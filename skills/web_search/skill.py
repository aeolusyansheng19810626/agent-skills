"""
Web検索スキル - Tavily APIを使用してインターネットから最新情報を検索
"""
import os
import sys
from typing import Generator
from datetime import datetime, timedelta
from tavily import TavilyClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import groq_client


class WebSearchSkill:
    """リアルタイム情報をWeb検索"""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        self.client = TavilyClient(api_key=api_key)

    def translate_to_chinese(self, text: str) -> str:
        """Groqを使用して英語テキストを簡体字中国語に翻訳"""
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
        """LLMを使用してノイズをフィルタリングし、結果を統一的にフォーマット"""
        try:
            # LLM用に生コンテンツを準備するが、トークン制限を避けるため各結果を切り詰める
            # llama-3.1-8b-instantは約6000トークン制限、結果あたり約800文字が安全
            MAX_CONTENT_PER_RESULT = 800  # 結果あたりの保守的な制限
            raw_content = ""
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                content = result.get("content", "")[:MAX_CONTENT_PER_RESULT]  # コンテンツを切り詰め
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
2. **去重**：如果多条结果报道同一新闻事件，只保留一条最完整的
3. **翻译**：将所有内容翻译成简体中文
4. **限制数量**：只输出最相关且不重复的 {max_results} 条结果
5. **统一格式**：每条结果使用以下格式：

### 标题（中文）
正文段落（中文，连贯的段落文字，不含列表或子标题）

来源：URL

---

重要规则：
- 如果某条结果包含多个无关新闻的列表，只提取与"{query}"直接相关的那一条
- 正文必须是流畅的中文段落，不得包含英文或列表结构
- **摘要正文中不得包含任何 Markdown 链接格式（如 [文字](URL)），来源统一在最后一行用"来源：URL"输出**
- **严格去重：相同或高度相似的新闻只保留一条**
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
            # フォールバック: 基本的なフォーマットで元の結果を返す
            output = ""
            for idx, result in enumerate(results[:max_results], 1):
                title = result.get("title", "无标题")
                content = result.get("content", "暂无内容")
                url = result.get("url", "")
                output += f"### {title}\n\n{content}\n\n来源：{url}\n\n---\n\n"
            return output
    
    def execute(self, query: str, max_results: int = 3) -> Generator[str, None, None]:
        """
        Web検索を実行して結果をストリーム
        
        Args:
            query: 検索クエリ文字列
            max_results: 返す結果の最大数（デフォルト: 3）
            
        Yields:
            ソース付きのフォーマットされた検索結果
        """
        try:
            yield f"🔍 正在搜索: **{query}**\n\n"
            
            # 最近の結果に偏らせるため、現在の日付をクエリに注入
            today = datetime.now()
            dated_query = f"{query} {today.strftime('%Y年%m月')}"

            # フィルタリングのオプションを持つため、Tavilyからより多くの結果をリクエスト
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

            # published_dateが利用可能な場合、30日より古い結果を除外
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
                        results.append(r)  # 日付が解析不可の場合は保持
                else:
                    results.append(r)  # 日付フィールドがない場合は保持

            # フィルタリングですべて削除された場合は、フィルタリングされていないリストにフォールバック
            if not results:
                results = response["results"]

            yield f"✅ 找到 {len(results)} 条新闻，显示前 {max_results} 条\n\n"
            
            # LLMを使用してノイズをフィルタリングし、結果を統一的にフォーマット
            filtered_output = self.filter_and_format_results(query, results, max_results)
            
            yield "## 📰 搜索结果\n\n"
            yield filtered_output
            
        except Exception as e:
            yield f"❌ **搜索过程出错:** {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    スキルのエントリーポイント
    
    Args:
        params: 'query'とオプションの'max_results'キーを含む辞書
        
    Yields:
        検索結果
    """
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' parameter is required\n"
        return
    
    max_results = params.get("max_results", 3)  # デフォルトは3件の結果
    
    skill = WebSearchSkill()
    yield from skill.execute(query, max_results)


# テスト用
if __name__ == "__main__":
    import sys
    
    test_query = "latest AI news 2024"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    
    print(f"Testing web_search skill with query: {test_query}\n")
    print("="*80)
    
    for chunk in run({"query": test_query}):
        print(chunk, end="", flush=True)

