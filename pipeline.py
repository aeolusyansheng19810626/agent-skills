"""
Pipeline executor — serial, parallel, nested, and dynamic plan execution.

Step types inside a plan:
  {"skill": "name", "params": {...}}              — serial single skill
  {"parallel": [{"skill": "name", "params": {...}}, ...]}  — concurrent group
  {"plan": [...]}                                 — nested sub-plan (recursive)

Context propagation:
  Each step's full text output is concatenated and passed as params["context"]
  to the next step (or parallel group), enabling downstream skills to build on
  prior results.

Dynamic extension:
  After the last step of a plan, the Evaluator LLM judges if output is sufficient.
  If it recommends an additional skill, that skill is appended and executed once.
  Capped at _MAX_DYNAMIC_EXTENSIONS per plan level to prevent infinite loops.

Nesting:
  Pipeline recursively calls itself for {"plan": [...]} steps.
  Depth is tracked and capped at max_depth (default 3).
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List

from skill_loader import SkillLoader

_MAX_DYNAMIC_EXTENSIONS = 1  # per plan level


# ── Public entry point ────────────────────────────────────────────────────────

def execute(
    router_result: Dict[str, Any],
    skill_loader: SkillLoader,
    user_query: str = "",
    max_depth: int = 3,
) -> Generator[str, None, None]:
    """
    Unified entry point. Handles single skill or plan (serial/parallel/nested/dynamic).

    Args:
        router_result: output of RouterAgent.route()
        skill_loader:  SkillLoader instance
        user_query:    original user text, used by Evaluator for dynamic extension
        max_depth:     maximum nesting depth for recursive sub-plans
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
            # Route through _execute_plan so Evaluator can run after the single step
            yield from _execute_plan(
                [{"skill": skill_name, "params": params}],
                skill_loader, user_query, max_depth, depth=0,
            )
        else:
            yield from _execute_single(router_result, skill_loader)


# ── Internal helpers ──────────────────────────────────────────────────────────

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

    # Mutable copy: evaluator may append one extra step at the end
    steps = list(plan)
    context = ""
    dynamic_extensions = 0
    idx = 0  # pointer into steps (len(steps) may grow by 1)
    
    # Track execution history: list of (skill_name, query) tuples
    execution_history = []

    while idx < len(steps):
        step = steps[idx]
        idx += 1
        total = len(steps)
        is_last = idx >= total

        # ── parallel group ────────────────────────────────────────
        if "parallel" in step:
            sub_steps = step["parallel"]
            yield f"### ⚡ 并行执行（共 {len(sub_steps)} 个技能）\n\n"

            results = _execute_parallel(sub_steps, context, skill_loader)
            merged = ""
            for skill_name, output in results.items():
                yield f"**[{skill_name}]**\n\n{output}\n\n"
                merged += f"[{skill_name}]\n{output}\n\n"
            context = merged

        # ── nested sub-plan ───────────────────────────────────────
        elif "plan" in step:
            yield f"### 🔄 子计划（嵌套深度 {depth + 1}）\n\n"
            sub_output = ""
            for chunk in _execute_plan(
                step["plan"], skill_loader, user_query, max_depth, depth + 1
            ):
                yield chunk
                sub_output += chunk
            context = sub_output

        # ── single serial skill ───────────────────────────────────
        elif "skill" in step:
            skill_name = step["skill"]
            params = dict(step.get("params", {}))
            # Use idx (1-based after increment) for display; recalculate total
            yield f"### 步骤 {idx}/{total}：{skill_name}\n\n"
            if context:
                params["context"] = context
            step_output = ""
            for chunk in _run_skill(skill_name, params, skill_loader):
                yield chunk
                step_output += chunk
            context = step_output
            
            # Record execution history (skill_name, query)
            query = params.get("query", "")
            execution_history.append((skill_name, query))

        # ── separator between steps ───────────────────────────────
        if not is_last:
            yield "\n---\n\n"

        # ── dynamic evaluation at the natural end of the plan ─────
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
                    # Record the dynamically added skill
                    query = next_params.get("query", "")
                    execution_history.append((next_skill, query))


def _execute_parallel(
    steps: List[Dict],
    context: str,
    skill_loader: SkillLoader,
) -> Dict[str, str]:
    """
    Run all steps concurrently via ThreadPoolExecutor.
    Returns {skill_name: full_output} dict; order follows completion time.
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
