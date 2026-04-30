"""
Stock Analysis Skill - Analyze stock data using yfinance and Groq
"""
import os
from typing import Generator
import yfinance as yf
from datetime import datetime, timedelta
from groq import Groq


class StockAnalysisSkill:
    """Analyze stock performance with technical and news analysis"""
    
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def execute(self, ticker: str) -> Generator[str, None, None]:
        """
        Execute stock analysis and stream results
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL, TSLA)
            
        Yields:
            Formatted analysis results
        """
        try:
            yield f"📊 正在分析股票: **{ticker.upper()}**\n\n"
            
            # Fetch stock data
            stock = yf.Ticker(ticker)
            
            # Get basic info
            info = stock.info
            yield "## 📈 基本信息\n\n"
            
            company_name = info.get('longName', ticker.upper())
            yield f"**公司:** {company_name}\n\n"
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price:
                yield f"**当前价格:** ${current_price:.2f}\n\n"
            
            market_cap = info.get('marketCap')
            if market_cap:
                # Format market cap
                if market_cap >= 1_000_000_000_000:  # >= 1T
                    formatted_cap = f"${market_cap / 1_000_000_000_000:.3f} T"
                elif market_cap >= 1_000_000_000:  # >= 1B
                    formatted_cap = f"${market_cap / 1_000_000_000:.2f} B"
                else:
                    formatted_cap = f"${market_cap:,.0f}"
                yield f"**市值:** {formatted_cap}\n\n"
            
            pe_ratio = info.get('trailingPE')
            if pe_ratio:
                yield f"**市盈率:** {pe_ratio:.2f}\n\n"
            
            # Get historical data (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            hist = stock.history(start=start_date, end=end_date)
            
            change = 0.0  # Initialize change variable
            if not hist.empty:
                yield "## 📉 近期表现（30天）\n\n"
                
                first_price = hist['Close'].iloc[0]
                last_price = hist['Close'].iloc[-1]
                change = ((last_price - first_price) / first_price) * 100
                
                yield f"**30天涨跌:** {change:+.2f}%\n\n"
                yield f"**最高:** ${hist['High'].max():.2f}\n\n"
                yield f"**最低:** ${hist['Low'].min():.2f}\n\n"
                yield f"**平均成交量:** {hist['Volume'].mean():,.0f}\n\n"
            
            # Get news - skip if data is incomplete
            try:
                news = stock.news
                if news and len(news) > 0:
                    # Filter out news with missing data
                    valid_news = []
                    for article in news[:5]:
                        title = article.get('title') or article.get('headline')
                        if title and title not in ['No title', '']:
                            valid_news.append(article)
                    
                    if valid_news:
                        yield "## 📰 最新新闻\n\n"
                        for idx, article in enumerate(valid_news[:3], 1):
                            title = article.get('title') or article.get('headline')
                            link = article.get('link') or article.get('url') or ''
                            publisher = article.get('publisher') or article.get('source') or '未知来源'
                            
                            yield f"{idx}. **{title}**\n"
                            yield f"   *来源: {publisher}*\n"
                            if link:
                                yield f"   [阅读更多]({link})\n\n"
            except:
                # Skip news if there's an error
                pass
            
            # Generate AI analysis
            yield "## 🤖 AI 分析\n\n"
            yield "正在生成分析...\n\n"
            
            # Format values safely
            price_str = f"${current_price:.2f}" if current_price else "N/A"
            cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
            pe_str = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
            high_str = f"${hist['High'].max():.2f}" if not hist.empty else "N/A"
            low_str = f"${hist['Low'].min():.2f}" if not hist.empty else "N/A"
            
            analysis_prompt = f"""分析以下 {company_name} ({ticker}) 的股票数据：

当前价格: {price_str}
市值: {cap_str}
市盈率: {pe_str}
30天涨跌: {change:+.2f}%
30天最高: {high_str}
30天最低: {low_str}

请提供简要的技术分析，包括：
1. 价格趋势和动量
2. 关键支撑/阻力位
3. 整体展望（看涨/看跌/中性）

保持分析简洁（3-4段）且可操作。请用简体中文回答。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位金融分析师，提供股票分析。请客观、数据驱动，使用简体中文回答。请避免重复内容，每个观点只陈述一次。"},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            yield "\n\n"
            yield "---\n\n"
            yield "*⚠️ 免责声明: 此分析仅供参考，不构成投资建议。*\n"
            
        except Exception as e:
            yield f"❌ **股票分析出错:** {str(e)}\n"
            yield "\n请验证股票代码是否正确。\n"


def run(params: dict) -> Generator[str, None, None]:
    """
    Entry point for the skill
    
    Args:
        params: Dictionary with 'ticker' key
        
    Yields:
        Stock analysis results
    """
    ticker = params.get("ticker")
    if not ticker:
        yield "❌ Error: 'ticker' parameter is required\n"
        return
    
    skill = StockAnalysisSkill()
    yield from skill.execute(ticker)


# For testing
if __name__ == "__main__":
    import sys
    
    test_ticker = "AAPL"
    if len(sys.argv) > 1:
        test_ticker = sys.argv[1]
    
    print(f"Testing stock_analysis skill with ticker: {test_ticker}\n")
    print("="*80)
    
    for chunk in run({"ticker": test_ticker}):
        print(chunk, end="", flush=True)

# Made with Bob
