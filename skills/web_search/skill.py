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

    def translate_to_ui_lang(self, text: str, ui_lang: str = "zh") -> str:
        """Groqを使用してテキストをターゲット言語に翻訳"""
        if ui_lang == "en": return text
        
        lang_names = {"zh": "简体中文", "ja": "日本語", "en": "English"}
        target_lang = lang_names.get(ui_lang, "简体中文")
        
        try:
            response, _ = groq_client.chat_completion(
                [
                    {"role": "system", "content": f"你是一个专业的翻译助手。将文本翻译成{target_lang}，保持原意，使用自然流畅的表达。只返回翻译结果，不要添加任何解释。"},
                    {"role": "user", "content": f"请将以下内容翻译成{target_lang}：\n\n{text}"},
                ],
                temperature=0.3,
                max_tokens=2000,
                task_type="light",
            )
            return response.choices[0].message.content or text
        except Exception:
            return text
    
    def filter_and_format_results(self, query: str, results: list, max_results: int, ui_lang: str = "zh") -> str:
        """LLMを使用してノイズをフィルタリングし、結果を統一的にフォーマット"""
        try:
            lang_names = {"zh": "简体中文", "ja": "日本語", "en": "English"}
            target_lang = lang_names.get(ui_lang, "简体中文")
            
            # LLM用に生コンテンツを準備
            MAX_CONTENT_PER_RESULT = 800
            raw_content = ""
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                content = result.get("content", "")[:MAX_CONTENT_PER_RESULT]
                url = result.get("url", "")
                raw_content += f"\n[结果{idx}]\n标题: {title}\n内容: {content}\nURL: {url}\n"
            
            prompt = f"""你是一个信息过滤和翻译助手。用户搜索："{query}"

以下是搜索引擎返回的原始结果：
{raw_content}

请执行以下任务：
1. **严格过滤**：只保留与"{query}"直接相关的内容。
2. **去重**：如果多条结果报道同一事件，只保留一条。
3. **翻译**：将所有标题和正文翻译成 {target_lang}。
4. **限制数量**：只输出最相关且不重复的 {max_results} 条结果。
5. **统一格式**：每条结果使用以下格式：

### 标题（{target_lang}）
正文段落（{target_lang}，连贯的段落文字，不含列表或子标题）

来源：URL

---

重要规则：
- 正文必须是流畅的 {target_lang} 段落。
- **严格去重：相同或高度相似的新闻只保留一条**。
- 每条结果之间用 --- 分隔。
- 只输出过滤和翻译后的结果，不要添加任何解释。"""

            response, _ = groq_client.chat_completion(
                [
                    {"role": "system", "content": f"你是一个专业的信息过滤助手。使用 {target_lang} 按照要求格式输出。"},
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
                title = result.get("title", "No Title")
                content = result.get("content", "No Content")
                url = result.get("url", "")
                source_label = "来源" if ui_lang == "zh" else ("Source" if ui_lang == "en" else "出典")
                output += f"### {title}\n\n{content}\n\n{source_label}：{url}\n\n---\n\n"
            return output
    
    def execute(self, query: str, max_results: int = 3, ui_lang: str = "zh") -> Generator[str, None, None]:
        """
        Web検索を実行して結果をストリーム
        """
        try:
            status_map = {
                "zh": f"🔍 正在搜索: **{query}**",
                "ja": f"🔍 検索中: **{query}**",
                "en": f"🔍 Searching for: **{query}**"
            }
            yield status_map.get(ui_lang, status_map["zh"]) + "\n\n"
            
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
                yield "❌ No results found\n"
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
                        results.append(r)
                else:
                    results.append(r)

            if not results:
                results = response["results"]

            found_map = {
                "zh": f"✅ 找到 {len(results)} 条新闻，显示前 {max_results} 条",
                "ja": f"✅ {len(results)} 件のﾆｭｰｽが見つかりました。上位 {max_results} 件を表示します",
                "en": f"✅ Found {len(results)} news, showing top {max_results}"
            }
            yield found_map.get(ui_lang, found_map["zh"]) + "\n\n"
            
            # LLMを使用してノイズをフィルタリングし、結果を統一的にフォーマット
            filtered_output = self.filter_and_format_results(query, results, max_results, ui_lang)
            
            res_hdr = {"zh": "## 📰 搜索结果", "ja": "## 📰 検索結果", "en": "## 📰 Search Results"}
            yield res_hdr.get(ui_lang, res_hdr["zh"]) + "\n\n"
            yield filtered_output
            
        except Exception as e:
            yield f"❌ Error: {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    スキルのエントリーポイント
    """
    query = params.get("query")
    if not query:
        yield "❌ Error: 'query' parameter is required\n"
        return
    
    max_results = params.get("max_results", 3)
    ui_lang = params.get("ui_lang", "zh")
    
    skill = WebSearchSkill()
    yield from skill.execute(query, max_results, ui_lang)


if __name__ == "__main__":
    import sys
    test_query = "latest AI news"
    for chunk in run({"query": test_query}):
        print(chunk, end="", flush=True)
