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
            print(f"[DEBUG filter] Starting filter with query='{query}', max_results={max_results}, num_results={len(results)}")
            # Prepare raw content for LLM
            raw_content = ""
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                raw_content += f"\n[结果{idx}]\n标题: {title}\n内容: {content}\nURL: {url}\n"
            print(f"[DEBUG filter] Raw content length: {len(raw_content)} chars")
            
            prompt = f"""你是一个信息过滤助手。用户搜索："{query}"

以下是搜索引擎返回的原始结果：
{raw_content}

请执行以下任务：
1. 只保留与查询"{query}"直接相关的内容
2. 删除导航栏、热门故事、侧边栏、无关新闻、广告等噪音
3. 输出不超过 {max_results} 条最相关的结果
4. 每条结果使用以下统一格式输出：

### 标题
正文段落（纯文字，不含嵌套列表或Markdown结构）

来源：URL

---

重要：
- 正文必须是连贯的段落文字，不得包含列表、子标题等嵌套结构
- 如果原始内容是列表，请改写为流畅的段落
- 每条结果之间用 --- 分隔
- 只输出过滤后的结果，不要添加任何解释"""

            print(f"[DEBUG filter] Calling LLM for filtering...")
            response, _ = groq_client.chat_completion(
                [
                    {"role": "system", "content": "你是一个专业的信息过滤助手。严格按照要求格式输出，不添加任何额外内容。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
                task_type="light",
            )
            filtered = response.choices[0].message.content or ""
            print(f"[DEBUG filter] LLM returned {len(filtered)} chars")
            print(f"[DEBUG filter] First 500 chars of filtered output:\n{filtered[:500]}")
            return filtered
        except Exception as e:
            print(f"[DEBUG filter] Exception during filtering: {e}")
            # Fallback: return original results with basic formatting
            output = ""
            for idx, result in enumerate(results[:max_results], 1):
                title = result.get("title", "无标题")
                content = result.get("content", "暂无内容")
                url = result.get("url", "")
                output += f"### {title}\n\n{content}\n\n来源：{url}\n\n---\n\n"
            print(f"[DEBUG filter] Using fallback formatting, output length: {len(output)} chars")
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
            # DEBUG: Log max_results parameter
            print(f"[DEBUG web_search] Received max_results={max_results}")
            yield f"🔍 正在搜索: **{query}** (max_results={max_results})\n\n"
            
            # Inject current date into query to bias toward recent results
            today = datetime.now()
            dated_query = f"{query} {today.strftime('%Y年%m月')}"

            # Request more results from Tavily to have options for filtering
            tavily_max = max(max_results * 2, 8)
            print(f"[DEBUG web_search] Calling Tavily with max_results={tavily_max}")
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

            print(f"[DEBUG web_search] Found {len(results)} results after date filtering")
            yield f"✅ 找到 {len(results)} 条原始结果，正在过滤和格式化（目标: {max_results} 条）...\n\n"
            
            # Use LLM to filter noise and format results uniformly
            print(f"[DEBUG web_search] Calling filter_and_format_results with max_results={max_results}")
            filtered_output = self.filter_and_format_results(query, results, max_results)
            print(f"[DEBUG web_search] Filter output length: {len(filtered_output)} chars")
            
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
    print(f"[DEBUG web_search.run] Received params: {params}")
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' parameter is required\n"
        return
    
    max_results = params.get("max_results", 3)  # Default to 3 results
    print(f"[DEBUG web_search.run] Extracted max_results={max_results} from params")
    
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
