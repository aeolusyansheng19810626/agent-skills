"""
Router Agent - Uses LLM to determine which skill to call based on user input
"""
import os
import json
import unicodedata
from typing import Dict, Optional, Any
from skill_loader import get_skill_loader
import groq_client


def _sanitize_reasoning(text: str, result: dict) -> str:
    """Return a readable Chinese reasoning string, falling back to an auto-generated one."""
    if not isinstance(text, str) or not text.strip():
        return _auto_reasoning(result)
    # Check ratio of CJK + ASCII printable chars; reject if too low (garbled text)
    total = len(text)
    readable = sum(
        1 for ch in text
        if unicodedata.category(ch) in ("Lo", "Nd", "Zs", "Po", "Ps", "Pe")
        or (0x20 <= ord(ch) <= 0x7E)
    )
    if total > 0 and readable / total < 0.6:
        return _auto_reasoning(result)
    return text


def _auto_reasoning(result: dict) -> str:
    if "plan" in result:
        parts = []
        for step in result["plan"]:
            if "parallel" in step:
                names = "、".join(s.get("skill", "?") for s in step["parallel"])
                parts.append(f"并行执行（{names}）")
            else:
                parts.append(step.get("skill", "?"))
        return "计划执行：" + " → ".join(parts)
    skill = result.get("skill", "none")
    return f"调用技能：{skill}" if skill != "none" else "无匹配技能"


class RouterAgent:
    """Routes user queries to appropriate skills using LLM"""
    
    def __init__(self, model: str = None):
        self.skill_loader = get_skill_loader()
        self.system_prompt = self._build_system_prompt()

    @property
    def model(self) -> str:
        try:
            return groq_client.get_model()
        except RuntimeError:
            return "（所有模型已耗尽）"
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with all skill descriptions"""
        skills_summary = self.skill_loader.get_skills_summary()
        
        prompt = f"""你是一个 Router Agent，根据用户输入判断应该调用哪个技能。

# 可用技能

{skills_summary}

# 你的任务

分析用户的查询，返回以下两种格式之一：

## 格式一：单技能（默认）
适用于只需调用一个技能的情况。
{{
  "skill": "技能名称",
  "params": {{}},
  "reasoning": "简体中文说明"
}}

## 格式二：Pipeline — 串行
适用于用户意图明确需要"先做A再做B"的情况，例如"搜索后分析"、"先查再总结"。
{{
  "plan": [
    {{"skill": "技能名称1", "params": {{}}}},
    {{"skill": "技能名称2", "params": {{}}}}
  ],
  "reasoning": "简体中文说明"
}}
注意：plan 中后续技能会自动接收前一技能的输出作为 context 参数，无需在 params 中手动填写 context。

## 格式三：Pipeline — 并行组
适用于用户需要"同时/并行"执行多个技能，各技能独立运行后汇总结果。
使用 "parallel" 字段代替 "skill"，值为技能对象数组。
{{
  "plan": [
    {{"parallel": [
      {{"skill": "技能名称A", "params": {{}}}},
      {{"skill": "技能名称B", "params": {{}}}}
    ]}},
    {{"skill": "技能名称C", "params": {{}}}}
  ],
  "reasoning": "简体中文说明"
}}
注意：parallel 组内所有技能同时启动，汇总后的结果作为 context 传给后续串行步骤。

如果没有匹配的技能，返回：
{{"skill": "none", "params": {{}}, "reasoning": "说明原因"}}

# 示例

用户："今天有什么AI相关的新闻？"
响应：{{"skill": "web_search", "params": {{"query": "AI相关新闻"}}, "reasoning": "用户询问最新新闻，需要网络搜索"}}

用户："详细搜索一下人工智能的最新进展"
响应：{{"skill": "web_search", "params": {{"query": "人工智能最新进展", "max_results": 5}}, "reasoning": "用户要求详细搜索，使用 max_results=5 返回更多结果"}}

用户："分析 AAPL 股票"
响应：{{"skill": "stock_analysis", "params": {{"ticker": "AAPL"}}, "reasoning": "用户要求分析股票代码 AAPL"}}

用户："写一个 Python 函数对列表排序"
响应：{{"skill": "code_generation", "params": {{"requirement": "Python 函数对列表排序", "language": "Python"}}, "reasoning": "用户请求代码生成"}}

用户："文档中关于定价的内容是什么？"
响应：{{"skill": "document_qa", "params": {{"query": "定价信息"}}, "reasoning": "用户询问文档内容"}}

用户："搜索英伟达最新消息后分析NVDA股票"
响应：{{"plan": [{{"skill": "web_search", "params": {{"query": "英伟达最新消息"}}}}, {{"skill": "stock_analysis", "params": {{"ticker": "NVDA"}}}}], "reasoning": "用户需要先搜索英伟达最新消息，再结合搜索结果进行股票分析"}}

用户："先搜一下特斯拉的新闻，再帮我分析TSLA"
响应：{{"plan": [{{"skill": "web_search", "params": {{"query": "特斯拉最新新闻"}}}}, {{"skill": "stock_analysis", "params": {{"ticker": "TSLA"}}}}], "reasoning": "用户明确要求先搜索新闻再分析股票，使用Pipeline"}}

用户："同时帮我搜索英伟达新闻和分析NVDA股票"
响应：{{"plan": [{{"parallel": [{{"skill": "web_search", "params": {{"query": "英伟达最新新闻"}}}}, {{"skill": "stock_analysis", "params": {{"ticker": "NVDA"}}}}]}}], "reasoning": "用户明确要求同时执行搜索和股票分析，使用并行组"}}

# 重要规则

1. 始终返回有效的 JSON
2. 精确匹配技能参数定义
3. 从用户查询中提取关键信息作为参数
4. 如果多个技能都适用，选择最具体的那个
5. 仔细考虑触发条件和不触发条件
6. 对于 code_generation，如果未指定语言则默认为 "Python"
7. 对于 web_search：
   - 当用户说"详细搜索"、"全面搜索"、"多找一些"等时，传 max_results=5
   - 其他情况不传 max_results（使用默认值3）
8. reasoning 字段必须是一句通顺的简体中文，简明说明为什么选择该技能或计划。例如："用户同时要求搜索苹果新闻和分析AAPL股票，使用并行组同时执行。" 禁止输出乱码、繁体中文或非中文内容
9. 仅当用户明确表达串行意图（"搜索后分析"、"先查再..."等）时才使用串行 plan；单一意图始终用单技能格式
10. 仅当用户明确表达并行意图（"同时"、"并行"、"一起"等）时才在 plan 中使用 parallel 组
11. 当用户使用条件句（"如果...就..."、"不足则..."、"必要时..."、"如有需要..."等）描述后续动作时，属于动态意图，只返回第一步技能（单技能格式），不要创建固定 plan。后续步骤由系统自动评估是否需要追加
12. plan 模式中 web_search 的 query 参数必须忠实还原用户的搜索意图原文，不得改写、翻译或替换为其他词语

现在分析用户的查询并返回适当的 JSON 响应。
"""
        return prompt
    
    def route(self, user_query: str) -> Dict[str, Any]:
        """
        Route user query to appropriate skill
        
        Args:
            user_query: User's input query
            
        Returns:
            Dictionary with skill, params, and reasoning
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_query},
            ]
            response, warning = groq_client.chat_completion(
                messages,
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            if warning:
                try:
                    import streamlit as st
                    st.toast(warning, icon="⚠️")
                except Exception:
                    pass

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty response")
            result = json.loads(content)
            
            # Validate result structure
            if "reasoning" not in result:
                result["reasoning"] = "No reasoning provided"
            else:
                result["reasoning"] = _sanitize_reasoning(result["reasoning"], result)

            if "plan" in result:
                # Pipeline format: validate each step (serial skill or parallel group)
                valid_names = self.skill_loader.get_skill_names()
                for step in result["plan"]:
                    if "parallel" in step:
                        for sub in step["parallel"]:
                            if "skill" not in sub:
                                raise ValueError("Parallel sub-step missing 'skill' field")
                            if sub["skill"] not in valid_names:
                                raise ValueError(f"Unknown skill in parallel: {sub['skill']}")
                            if "params" not in sub:
                                sub["params"] = {}
                    elif "skill" in step:
                        if step["skill"] not in valid_names:
                            raise ValueError(f"Unknown skill in plan: {step['skill']}")
                        if "params" not in step:
                            step["params"] = {}
                    else:
                        raise ValueError("Plan step must have 'skill' or 'parallel' field")
            else:
                # Single skill format
                if "skill" not in result:
                    raise ValueError("Response missing 'skill' field")
                if "params" not in result:
                    result["params"] = {}
                if result["skill"] != "none" and result["skill"] not in self.skill_loader.get_skill_names():
                    raise ValueError(f"Unknown skill: {result['skill']}")
            
            return result
            
        except json.JSONDecodeError as e:
            return {
                "skill": "none",
                "params": {},
                "reasoning": f"Failed to parse LLM response: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            return {
                "skill": "none",
                "params": {},
                "reasoning": f"Router error: {str(e)}",
                "error": str(e)
            }
    
    def route_with_fallback(self, user_query: str) -> Dict[str, Any]:
        """
        Route with fallback to direct response if no skill matches
        
        Args:
            user_query: User's input query
            
        Returns:
            Dictionary with skill, params, reasoning, and optional direct_response
        """
        result = self.route(user_query)
        
        # If no skill matches, generate a direct response
        if result["skill"] == "none":
            try:
                response, warning = groq_client.chat_completion(
                    [
                        {"role": "system", "content": "You are a helpful assistant. Answer the user's question directly and concisely."},
                        {"role": "user", "content": user_query},
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                )
                if warning:
                    try:
                        import streamlit as st
                        st.toast(warning, icon="⚠️")
                    except Exception:
                        pass
                result["direct_response"] = response.choices[0].message.content
            except Exception as e:
                result["direct_response"] = f"I couldn't process your request. Error: {str(e)}"
        
        return result


def test_router():
    """Test the router with sample queries"""
    router = RouterAgent()
    
    test_queries = [
        "What's the latest news about Tesla?",
        "Analyze AAPL stock performance",
        "Write a Python function to calculate fibonacci numbers",
        "What does the document say about refund policy?",
        "What is 2+2?",  # Should return none
    ]
    
    print("="*80)
    print("ROUTER AGENT TEST")
    print("="*80)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = router.route(query)
        print(f"🎯 Skill: {result['skill']}")
        print(f"📦 Params: {result['params']}")
        print(f"💭 Reasoning: {result['reasoning']}")
        if 'error' in result:
            print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    test_router()

# Made with Bob
