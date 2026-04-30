"""
Router Agent - Uses LLM to determine which skill to call based on user input
"""
import os
import json
from typing import Dict, Optional, Any
from groq import Groq
from skill_loader import get_skill_loader


class RouterAgent:
    """Routes user queries to appropriate skills using LLM"""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model
        self.skill_loader = get_skill_loader()
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with all skill descriptions"""
        skills_summary = self.skill_loader.get_skills_summary()
        
        prompt = f"""你是一个 Router Agent，根据用户输入判断应该调用哪个技能。

# 可用技能

{skills_summary}

# 你的任务

分析用户的查询并确定应该调用哪个技能。返回一个 JSON 对象，包含：
- "skill": 技能名称（例如："web_search"、"stock_analysis"、"document_qa"、"code_generation"）
- "params": 该技能所需的参数字典
- "reasoning": 简要说明为什么选择这个技能（必须使用简体中文）

如果没有匹配的技能，返回：
{{"skill": "none", "params": {{}}, "reasoning": "说明原因"}}

# 示例

用户："今天有什么AI相关的新闻？"
响应：{{"skill": "web_search", "params": {{"query": "AI相关新闻"}}, "reasoning": "用户询问最新新闻，需要网络搜索"}}

用户："分析 AAPL 股票"
响应：{{"skill": "stock_analysis", "params": {{"ticker": "AAPL"}}, "reasoning": "用户要求分析股票代码 AAPL"}}

用户："写一个 Python 函数对列表排序"
响应：{{"skill": "code_generation", "params": {{"requirement": "Python 函数对列表排序", "language": "Python"}}, "reasoning": "用户请求代码生成"}}

用户："文档中关于定价的内容是什么？"
响应：{{"skill": "document_qa", "params": {{"query": "定价信息"}}, "reasoning": "用户询问文档内容"}}

# 重要规则

1. 始终返回有效的 JSON
2. 精确匹配技能参数定义
3. 从用户查询中提取关键信息作为参数
4. 如果多个技能都适用，选择最具体的那个
5. 仔细考虑触发条件和不触发条件
6. 对于 code_generation，如果未指定语言则默认为 "Python"
7. reasoning 字段必须使用简体中文回答，不要使用繁体中文

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty response")
            result = json.loads(content)
            
            # Validate result structure
            if "skill" not in result:
                raise ValueError("Response missing 'skill' field")
            if "params" not in result:
                result["params"] = {}
            if "reasoning" not in result:
                result["reasoning"] = "No reasoning provided"
            
            # Validate skill exists
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
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Answer the user's question directly and concisely."},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
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
