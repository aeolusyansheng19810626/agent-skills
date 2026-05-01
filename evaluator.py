"""
Evaluator - lightweight LLM judge that decides whether to extend the pipeline.

Called at the natural end of a plan. Returns:
  {"action": "continue"}                                  — output is sufficient
  {"action": "next", "skill": "...", "params": {...}}     — append one more skill
"""
import os
import json
from typing import List
from groq import Groq


class Evaluator:
    # Use a fast/cheap model for this lightweight judgment task
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
    ) -> dict:
        """
        Judge if accumulated_output sufficiently answers user_query.

        Fails safe: any exception returns {"action": "continue"} so the
        pipeline never stalls due to evaluator errors.
        """
        if not user_query:
            return {"action": "continue"}

        snippet = accumulated_output[-600:] if accumulated_output else "（无内容）"
        skills_str = ", ".join(available_skills)

        prompt = f"""用户的原始需求：
{user_query}

当前已收集结果（最后600字）：
{snippet}

可用技能：{skills_str}

请客观判断当前结果是否已充分满足用户的核心需求：
- 若已充分 → 返回：{{"action": "continue"}}
- 若确实存在关键信息缺失 → 返回：{{"action": "next", "skill": "<技能名>", "params": {{<参数字典>}}}}

重要判断原则：
1. 仅当结果中缺少回答用户核心需求所必需的关键信息时，才返回 next
2. 如果用户需求包含条件句（如"如果不足就搜索"），请先客观评估当前结果是否真的不足，不要仅因为用户提到了某个条件动作就推荐该动作
3. 股票分析结果包含价格、市值、30天涨跌、AI分析段落时，通常已经充分

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
