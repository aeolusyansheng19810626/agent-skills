"""
評価エンジン - パイプラインを拡張するかを判断する軽量LLMジャッジ

プランの自然な終了時に呼び出される。戻り値:
  {"action": "continue"}                                  — 出力は十分
  {"action": "next", "skill": "...", "params": {...}}     — さらに1つのスキルを追加
"""
import os
import json
from typing import List, Tuple, Optional
from groq import Groq


class Evaluator:
    # この軽量な判断タスクには高速で安価なモデルを使用
    MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=api_key)

    def evaluate(
        self,
        user_query: str,
        accumulated_output: str,
        available_skills: List[str],
        execution_history: Optional[List[Tuple[str, str]]] = None,
    ) -> dict:
        """
        accumulated_outputがuser_queryに十分に答えているかを判断

        Args:
            user_query: 元のユーザーリクエスト
            accumulated_output: 現在の累積出力
            available_skills: 利用可能なスキル名のリスト
            execution_history: すでに実行された(skill_name, query)タプルのリスト

        フェイルセーフ: 例外が発生した場合は{"action": "continue"}を返すため、
        評価エンジンのエラーによってパイプラインが停止することはない。
        """
        if not user_query:
            return {"action": "continue"}

        snippet = accumulated_output[-600:] if accumulated_output else "（无内容）"
        skills_str = ", ".join(available_skills)
        
        # 実行履歴をフォーマット
        if execution_history:
            history_str = "\n已执行的技能历史：\n"
            for skill_name, query in execution_history:
                history_str += f"- {skill_name}"
                if query:
                    history_str += f"（查询: {query}）"
                history_str += "\n"
        else:
            history_str = ""

        prompt = f"""用户的原始需求：
{user_query}

当前已收集结果（最后600字）：
{snippet}

可用技能：{skills_str}
{history_str}
请客观判断当前结果是否已充分满足用户的核心需求：
- 若已充分 → 返回：{{"action": "continue"}}
- 若确实存在关键信息缺失 → 返回：{{"action": "next", "skill": "<技能名>", "params": {{<参数字典>}}}}

重要判断原则：
1. 仅当结果中缺少回答用户核心需求所必需的关键信息时，才返回 next
2. 如果用户需求包含条件句（如"如果不足就搜索"），请先客观评估当前结果是否真的不足，不要仅因为用户提到了某个条件动作就推荐该动作
3. 股票分析结果包含价格、市值、30天涨跌、AI分析段落时，通常已经充分
4. **防止重复执行**：若相同技能（特别是 web_search）已在历史中执行过，且查询语义相似，则必须返回 continue，不得重复追加

只返回 JSON，不要任何解释。"""

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "你是一个判断助手，只输出JSON，禁止任何解释文字。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            result = json.loads(raw)
            if result.get("action") not in ("continue", "next"):
                return {"action": "continue"}
            return result
        except Exception:
            return {"action": "continue"}
