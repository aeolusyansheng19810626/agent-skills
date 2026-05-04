"""
パイプライン実行エンジン - 直列、並列、ネスト、動的プラン実行

プラン内のステップタイプ:
  {"skill": "name", "params": {...}}              — 直列単一スキル
  {"parallel": [{"skill": "name", "params": {...}}, ...]}  — 並列グループ
  {"plan": [...]}                                 — ネストされたサブプラン（再帰）

コンテキストの伝播:
  各ステップの完全なテキスト出力が連結され、params["context"]として
  次のステップ（または並列グループ）に渡される。これにより下流のスキルが
  前の結果を基に処理を行える。

動的拡張:
  プランの最後のステップ後、評価エンジンのLLMが出力が十分かを判断。
  追加のスキルを推奨する場合、そのスキルが追加され一度だけ実行される。
  無限ループを防ぐため、プランレベルごとに_MAX_DYNAMIC_EXTENSIONSで制限。

ネスト:
  パイプラインは{"plan": [...]}ステップに対して自身を再帰的に呼び出す。
  深度は追跡され、max_depth（デフォルト3）で制限される。
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List

from skill_loader import SkillLoader

_MAX_DYNAMIC_EXTENSIONS = 1  # プランレベルごと


# ── パブリックエントリーポイント ──────────────────────────────────────────────

def execute(
    router_result: Dict[str, Any],
    skill_loader: SkillLoader,
    user_query: str = "",
    max_depth: int = 3,
) -> Generator[str, None, None]:
    """
    統一エントリーポイント。単一スキルまたはプラン（直列/並列/ネスト/動的）を処理

    Args:
        router_result: RouterAgent.route()の出力
        skill_loader:  SkillLoaderインスタンス
        user_query:    元のユーザーテキスト、動的拡張のために評価エンジンで使用
        max_depth:     再帰的サブプランの最大ネスト深度
    """
    if "plan" in router_result:
        yield from _execute_plan(
            router_result["plan"], skill_loader, user_query, max_depth, depth=0
        )
    else:
        skill_name = router_result.get("skill", "none")
        params = router_result.get("params", {})
        if not skill_name or skill_name == "none":
            return
        if user_query:
            # 単一ステップ後に評価エンジンが実行できるよう_execute_planを経由
            yield from _execute_plan(
                [{"skill": skill_name, "params": params}],
                skill_loader, user_query, max_depth, depth=0,
            )
        else:
            yield from _execute_single(router_result, skill_loader)


# ── 内部ヘルパー ──────────────────────────────────────────────────────────────

def _execute_single(
    router_result: Dict[str, Any], skill_loader: SkillLoader
) -> Generator[str, None, None]:
    skill_name = router_result.get("skill", "none")
    params = router_result.get("params", {})
    if not skill_name or skill_name == "none":
        return
    yield from _run_skill(skill_name, params, skill_loader)


def _execute_plan(
    plan: List[Dict],
    skill_loader: SkillLoader,
    user_query: str,
    max_depth: int,
    depth: int,
) -> Generator[str, None, None]:
    if depth >= max_depth:
        yield f"⚠️ 已达最大嵌套深度（{max_depth}），停止执行\n"
        return

    # 可変コピー：評価エンジンが最後に1つのステップを追加する可能性がある
    steps = list(plan)
    context = ""
    dynamic_extensions = 0
    idx = 0  # stepsへのポインタ（len(steps)は1増える可能性がある）
    
    # 実行履歴を追跡：(skill_name, query)タプルのリスト
    execution_history = []

    while idx < len(steps):
        step = steps[idx]
        idx += 1
        total = len(steps)
        is_last = idx >= total

        # ── 並列グループ ──────────────────────────────────────────
        if "parallel" in step:
            sub_steps = step["parallel"]
            yield f"### ⚡ 并行执行（共 {len(sub_steps)} 个技能）\n\n"

            results = _execute_parallel(sub_steps, context, skill_loader)
            merged = ""
            for skill_name, output in results.items():
                yield f"**[{skill_name}]**\n\n{output}\n\n"
                merged += f"[{skill_name}]\n{output}\n\n"
            context = merged

        # ── ネストされたサブプラン ────────────────────────────────
        elif "plan" in step:
            yield f"### 🔄 子计划（嵌套深度 {depth + 1}）\n\n"
            sub_output = ""
            for chunk in _execute_plan(
                step["plan"], skill_loader, user_query, max_depth, depth + 1
            ):
                yield chunk
                sub_output += chunk
            context = sub_output

        # ── 単一直列スキル ────────────────────────────────────────
        elif "skill" in step:
            skill_name = step["skill"]
            params = dict(step.get("params", {}))
            # 表示にはidx（インクリメント後の1ベース）を使用。totalを再計算
            yield f"### 步骤 {idx}/{total}：{skill_name}\n\n"
            if context:
                params["context"] = context
            step_output = ""
            for chunk in _run_skill(skill_name, params, skill_loader):
                yield chunk
                step_output += chunk
            context = step_output
            
            # 実行履歴を記録（skill_name, query）
            query = params.get("query", "")
            execution_history.append((skill_name, query))

        # ── ステップ間の区切り ────────────────────────────────────
        if not is_last:
            yield "\n---\n\n"

        # ── プランの自然な終了時の動的評価 ────────────────────────
        if is_last and user_query and dynamic_extensions < _MAX_DYNAMIC_EXTENSIONS:
            from evaluator import Evaluator
            eval_result = Evaluator().evaluate(
                user_query, context, skill_loader.get_skill_names(), execution_history
            )
            if eval_result.get("action") == "next":
                next_skill = eval_result.get("skill", "")
                next_params = eval_result.get("params", {})
                if next_skill and next_skill in skill_loader.get_skill_names():
                    dynamic_extensions += 1
                    yield "\n---\n\n"
                    yield f"\x00DYNAMIC_SKILL:{next_skill}\x00"
                    yield f"💡 *评估后追加技能: {next_skill}*\n\n"
                    steps.append({"skill": next_skill, "params": next_params})
                    # 動的に追加されたスキルを記録
                    query = next_params.get("query", "")
                    execution_history.append((next_skill, query))


def _execute_parallel(
    steps: List[Dict],
    context: str,
    skill_loader: SkillLoader,
) -> Dict[str, str]:
    """
    ThreadPoolExecutorを使用してすべてのステップを並行実行。
    {skill_name: full_output}辞書を返す。順序は完了時刻に従う。
    """
    results: Dict[str, str] = {}

    def run_one(step: Dict):
        skill_name = step["skill"]
        params = dict(step.get("params", {}))
        if context:
            params["context"] = context
        output = "".join(_run_skill(skill_name, params, skill_loader))
        return skill_name, output

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_one, step): step for step in steps}
        for future in as_completed(futures):
            try:
                skill_name, output = future.result()
                results[skill_name] = output
            except Exception as exc:
                fallback_name = futures[future].get("skill", "unknown")
                results[fallback_name] = f"❌ 并行执行出错: {exc}\n"

    return results


def _run_skill(
    skill_name: str, params: dict, skill_loader: SkillLoader
) -> Generator[str, None, None]:
    try:
        skill_module = skill_loader.import_skill_module(skill_name)
        if not hasattr(skill_module, "run"):
            yield f"❌ 错误: 技能 '{skill_name}' 没有 'run' 函数\n"
            return
        yield from skill_module.run(params)
    except Exception as exc:
        yield f"❌ 执行技能 '{skill_name}' 时出错: {exc}\n"
