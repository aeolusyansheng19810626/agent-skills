"""
Web Search Skill - Search the internet for latest information using Tavily API
"""
import os
import sys
from typing import Generator
from datetime import datetime, timedelta
from tavily import TavilyClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import groq_client


class WebSearchSkill:
    """Search the web for real-time information"""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        self.client = TavilyClient(api_key=api_key)

    def translate_to_chinese(self, text: str) -> str:
        """Translate English text to Simplified Chinese using Groq"""
        try:
            response, _ = groq_client.chat_completion(
                [
                    {"role": "system", "content": "你是一个专业的翻译助手。将英文翻译成简体中文，保持原意，使用自然流畅的中文表达。只返回翻译结果，不要添加任何解释。"},
                    {"role": "user", "content": f"请将以下英文翻译成简体中文：\n\n{text}"},
                ],
                temperature=0.3,
                max_tokens=2000,
                task_type="light",
            )
            return response.choices[0].message.content or text
        except Exception:
            return text
    
    def filter_and_format_results(self, query: str, results: list, max_results: int) -> str:
        """Use LLM to filter noise and format results uniformly"""
        try:
            # Prepare raw content for LLM, but truncate each result to avoid token limits
            # llama-3.1-8b-instant has ~6000 token limit, roughly 800 chars per result is safe
            MAX_CONTENT_PER_RESULT = 800  # Conservative limit per result
            raw_content = ""
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                content = result.get("content", "")[:MAX_CONTENT_PER_RESULT]  # Truncate content
                url = result.get("url", "")
                raw_content += f"\n[结果{idx}]\n标题: {title}\n内容: {content}\nURL: {url}\n"
            
            prompt = f"""你是一个信息过滤和翻译助手。用户搜索："{query}"

以下是搜索引擎返回的原始英文结果：
{raw_content}

请执行以下任务：
1. **严格过滤**：只保留与"{query}"直接相关的新闻内容，删除：
   - 导航栏、侧边栏、热门故事列表
   - 无关的其他新闻标题
   - 广告、推荐链接
   - 任何与"{query}"主题无关的内容
2. **翻译**：将所有内容翻译成简体中文
3. **限制数量**：只输出最相关的 {max_results} 条结果
4. **统一格式**：每条结果使用以下格式：

### 标题（中文）
正文段落（中文，连贯的段落文字，不含列表或子标题）

来源：URL

---

重要规则：
- 如果某条结果包含多个无关新闻的列表，只提取与"{query}"直接相关的那一条
- 正文必须是流畅的中文段落，不得包含英文或列表结构
- 每条结果之间用 --- 分隔
- 只输出过滤和翻译后的结果，不要添加任何解释"""

            response, _ = groq_client.chat_completion(
                [
                    {"role": "system", "content": "你是一个专业的信息过滤助手。严格按照要求格式输出，不添加任何额外内容。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
                task_type="light",
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # Fallback: return original results with basic formatting
            output = ""
            for idx, result in enumerate(results[:max_results], 1):
                title = result.get("title", "无标题")
                content = result.get("content", "暂无内容")
                url = result.get("url", "")
                output += f"### {title}\n\n{content}\n\n来源：{url}\n\n---\n\n"
            return output
    
    def execute(self, query: str, max_results: int = 3) -> Generator[str, None, None]:
        """
        Execute web search and stream results
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 3)
            
        Yields:
            Formatted search results with sources
        """
        try:
            yield f"🔍 正在搜索: **{query}**\n\n"
            
            # Inject current date into query to bias toward recent results
            today = datetime.now()
            dated_query = f"{query} {today.strftime('%Y年%m月')}"

            # Request more results from Tavily to have options for filtering
            tavily_max = max(max_results * 2, 8)
            response = self.client.search(
                query=dated_query,
                search_depth="advanced",
                max_results=tavily_max,
                topic="news",
            )

            if not response.get("results"):
                yield "❌ 未找到相关结果\n"
                return

            # Filter out results older than 30 days when published_date is available
            cutoff = today - timedelta(days=30)
            results = []
            for r in response["results"]:
                pub = r.get("published_date") or r.get("publishedDate") or ""
                if pub:
                    try:
                        pub_dt = datetime.fromisoformat(pub[:10])
                        if pub_dt >= cutoff:
                            results.append(r)
                    except ValueError:
                        results.append(r)  # keep if date unparseable
                else:
                    results.append(r)  # keep if no date field

            # Fall back to unfiltered list if filtering removed everything
            if not results:
                results = response["results"]

            yield f"✅ 找到 {len(results)} 条结果，正在过滤和格式化...\n\n"
            
            # Use LLM to filter noise and format results uniformly
            filtered_output = self.filter_and_format_results(query, results, max_results)
            
            yield "## 📰 搜索结果\n\n"
            yield filtered_output
            
        except Exception as e:
            yield f"❌ **搜索过程出错:** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    Entry point for the skill
    
    Args:
        params: Dictionary with 'query' and optional 'max_results' keys
        
    Yields:
        Search results
    """
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' parameter is required\n"
        return
    
    max_results = params.get("max_results", 3)  # Default to 3 results
    
    skill = WebSearchSkill()
    yield from skill.execute(query, max_results)


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
