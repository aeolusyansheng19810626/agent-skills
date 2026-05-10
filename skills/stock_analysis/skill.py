"""
株式分析スキル - yfinanceとGroqを使用して株式データを分析
"""
import os
import sys
import importlib
from typing import Generator
import yfinance as yf
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import groq_client


class StockAnalysisSkill:
    """テクニカル分析とニュース分析で株式パフォーマンスを分析"""

    def __init__(self):
        pass
    
    def execute(self, ticker: str, context: str = "", ui_lang: str = "zh") -> Generator[str, None, None]:
        """
        株式分析を実行して結果をストリーム
        """
        try:
            lang_names = {"zh": "简体中文", "ja": "日本語", "en": "English"}
            target_lang = lang_names.get(ui_lang, "简体中文")
            
            status_map = {
                "zh": f"📊 正在分析股票: **{ticker.upper()}**",
                "ja": f"📊 株式を分析しています: **{ticker.upper()}**",
                "en": f"📊 Analyzing stock: **{ticker.upper()}**"
            }
            yield status_map.get(ui_lang, status_map["zh"]) + "\n\n"
            
            # 株式データを取得
            stock = yf.Ticker(ticker)
            info = stock.info
            
            hdr_info = {"zh": "## 📈 基本信息", "ja": "## 📈 基本情報", "en": "## 📈 Basic Info"}
            yield hdr_info.get(ui_lang, hdr_info["zh"]) + "\n\n"
            
            labels = {
                "zh": {"company": "公司", "price": "当前价格", "mkt_cap": "市值", "pe": "市盈率"},
                "ja": {"company": "企業名", "price": "現在値", "mkt_cap": "時価総額", "pe": "PER"},
                "en": {"company": "Company", "price": "Price", "mkt_cap": "Mkt Cap", "pe": "P/E Ratio"}
            }
            L = labels.get(ui_lang, labels["zh"])
            
            company_name = info.get('longName', ticker.upper())
            yield f"**{L['company']}:** {company_name}\n\n"
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price:
                yield f"**{L['price']}:** ${current_price:.2f}\n\n"
            
            market_cap = info.get('marketCap')
            if market_cap:
                if market_cap >= 1_000_000_000_000:
                    formatted_cap = f"${market_cap / 1_000_000_000_000:.3f} T"
                elif market_cap >= 1_000_000_000:
                    formatted_cap = f"${market_cap / 1_000_000_000:.2f} B"
                else:
                    formatted_cap = f"${market_cap:,.0f}"
                yield f"**{L['mkt_cap']}:** {formatted_cap}\n\n"
            
            pe_ratio = info.get('trailingPE')
            if pe_ratio:
                yield f"**{L['pe']}:** {pe_ratio:.2f}\n\n"
            
            # 過去データを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            hist = stock.history(start=start_date, end=end_date)
            
            change = 0.0
            if not hist.empty:
                hdr_perf = {"zh": "## 📉 近期表现（30天）", "ja": "## 📉 最近のﾊﾟﾌｫｰﾏﾝｽ（30日）", "en": "## 📉 Recent Performance (30d)"}
                yield hdr_perf.get(ui_lang, hdr_perf["zh"]) + "\n\n"
                
                perf_labels = {
                    "zh": {"change": "30天涨跌", "high": "最高", "low": "最低", "vol": "平均成交量"},
                    "ja": {"change": "30日騰落率", "high": "高値", "low": "安値", "vol": "平均出来高"},
                    "en": {"change": "30d Change", "high": "High", "low": "Low", "vol": "Avg Volume"}
                }
                PL = perf_labels.get(ui_lang, perf_labels["zh"])
                
                first_price = hist['Close'].iloc[0]
                last_price = hist['Close'].iloc[-1]
                change = ((last_price - first_price) / first_price) * 100
                
                yield f"**{PL['change']}:** {change:+.2f}%\n\n"
                yield f"**{PL['high']}:** ${hist['High'].max():.2f}\n\n"
                yield f"**{PL['low']}:** ${hist['Low'].min():.2f}\n\n"
                yield f"**{PL['vol']}:** {hist['Volume'].mean():,.0f}\n\n"
            
            # ニュース
            if context:
                hdr_ctx = {"zh": "## 📰 背景资讯", "ja": "## 📰 背景情報", "en": "## 📰 Background Info"}
                yield hdr_ctx.get(ui_lang, hdr_ctx["zh"]) + "\n\n"
                msg_ctx = {"zh": "*（已从上一步骤获取）*", "ja": "*（前のｽﾃｯﾌﾟから取得済み）*", "en": "*（Fetched from previous step）*"}
                yield msg_ctx.get(ui_lang, msg_ctx["zh"]) + "\n\n"
            else:
                try:
                    news = stock.news
                    if news and len(news) > 0:
                        hdr_news = {"zh": "## 📰 最新新闻", "ja": "## 📰 最新ﾆｭｰｽ", "en": "## 📰 Latest News"}
                        yield hdr_news.get(ui_lang, hdr_news["zh"]) + "\n\n"
                        for idx, article in enumerate(news[:3], 1):
                            title = article.get('title') or article.get('headline')
                            link = article.get('link') or article.get('url') or ''
                            yield f"{idx}. **{title}**\n"
                            if link: yield f"   [Link]({link})\n"
                        yield "\n"
                except: pass
            
            # AI分析
            hdr_ai = {"zh": "## 🤖 AI 分析", "ja": "## 🤖 AI 分析", "en": "## 🤖 AI Analysis"}
            yield hdr_ai.get(ui_lang, hdr_ai["zh"]) + "\n\n"
            
            price_str = f"${current_price:.2f}" if current_price else "N/A"
            context_section = f"\n\n## 背景资讯\n{context[:3000]}\n" if context else ""

            analysis_prompt = f"""分析以下 {company_name} ({ticker}) 的股票数据：
当前价格: {price_str}
30天涨跌: {change:+.2f}%
{context_section}
请提供简要的技术分析（趋势、支撑、展望）。**请使用 {target_lang} 回答。**"""

            messages = [
                {"role": "system", "content": f"你是一位金融分析师。请客观并使用 **{target_lang}** 回答。"},
                {"role": "user", "content": analysis_prompt},
            ]
            response, warning = groq_client.chat_completion(
                messages, stream=True, temperature=0.3, max_tokens=800, task_type="heavy"
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n---\n\n"
            disclaimer = {
                "zh": "*⚠️ 免责声明: 此分析仅供参考，不构成投资建议。*",
                "ja": "*⚠️ 免責事項: この分析は参考用であり、投資勧誘を目的としたものではありません。*",
                "en": "*⚠️ Disclaimer: This analysis is for reference only and does not constitute investment advice.*"
            }
            yield disclaimer.get(ui_lang, disclaimer["zh"]) + "\n"
            
        except Exception as e:
            yield f"❌ Error: {str(e)}\n"


def run(params: dict) -> Generator[str, None, None]:
    """スキルのエントリーポイント"""
    ticker = params.get("ticker")
    if not ticker:
        yield "❌ Error: 'ticker' is required\n"
        return

    context = params.get("context", "")
    ui_lang = params.get("ui_lang", "zh")
    skill = StockAnalysisSkill()
    yield from skill.execute(ticker, context, ui_lang)
