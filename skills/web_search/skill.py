"""
Web Search Skill - Search the internet for latest information using Tavily API
"""
import os
from typing import Generator
from tavily import TavilyClient
from groq import Groq


class WebSearchSkill:
    """Search the web for real-time information"""
    
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        self.client = TavilyClient(api_key=api_key)
        
        # Initialize Groq for translation
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.groq_client = Groq(api_key=groq_key)
        else:
            self.groq_client = None
    
    def translate_to_chinese(self, text: str) -> str:
        """Translate English text to Simplified Chinese using Groq"""
        if not self.groq_client:
            return text
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "你是一个专业的翻译助手。将英文翻译成简体中文，保持原意，使用自然流畅的中文表达。只返回翻译结果，不要添加任何解释。"},
                    {"role": "user", "content": f"请将以下英文翻译成简体中文：\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content or text
        except:
            return text
    
    def execute(self, query: str) -> Generator[str, None, None]:
        """
        Execute web search and stream results
        
        Args:
            query: Search query string
            
        Yields:
            Formatted search results with sources
        """
        try:
            yield f"🔍 正在搜索: **{query}**\n\n"
            
            # Perform search with topic filter for news
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                topic="news"
            )
            
            if not response.get("results"):
                yield "❌ No results found.\n"
                return
            
            yield f"✅ 找到 {len(response['results'])} 条结果\n\n"
            yield "---\n\n"
            
            # Add answer summary if available (show first)
            if "answer" in response and response["answer"]:
                yield "## 📝 内容摘要\n\n"
                yield f"{response['answer']}\n\n"
                yield "---\n\n"
            
            # Format and yield results with better structure
            yield "## 📰 详细新闻\n\n"
            for idx, result in enumerate(response["results"], 1):
                title = result.get("title", "无标题")
                url = result.get("url", "")
                content = result.get("content", "暂无内容")
                
                # Translate title and content to Chinese
                title_cn = self.translate_to_chinese(title)
                content_cn = self.translate_to_chinese(content)
                
                yield f"### {idx}. {title_cn}\n\n"
                
                # Split content into paragraphs for better readability
                paragraphs = content_cn.split('。')
                for para in paragraphs:
                    if para.strip():
                        yield f"{para.strip()}。\n\n"
                
                yield f"🔗 **来源:** [{url}]({url})\n\n"
                yield "---\n\n"
            
        except Exception as e:
            yield f"❌ **Error during web search:** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    Entry point for the skill
    
    Args:
        params: Dictionary with 'query' key
        
    Yields:
        Search results
    """
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' parameter is required\n"
        return
    
    skill = WebSearchSkill()
    yield from skill.execute(query)


# For testing
if __name__ == "__main__":
    import sys
    
    test_query = "latest AI news 2024"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    
    print(f"Testing web_search skill with query: {test_query}\n")
    print("="*80)
    
    for chunk in run({"query": test_query}):
        print(chunk, end="", flush=True)

# Made with Bob
