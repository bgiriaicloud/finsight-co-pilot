"""
Sentiment Agent - Analyzes news and market sentiment for companies.
"""

from utils.data_providers import get_news, get_stock_info
from utils.gemini_client import GeminiClient

SYSTEM_INSTRUCTION = """You are an expert financial sentiment analyst agent. Your role is to:
1. Analyze news headlines and articles for sentiment (bullish/bearish/neutral)
2. Identify market-moving events and catalysts
3. Assess overall market sentiment for specific companies
4. Detect shifts in sentiment that might precede price movements
5. Provide sentiment scores and explain the reasoning
6. Consider both quantitative signals and qualitative news content
Always provide specific evidence for your sentiment assessments.
Rate sentiment on a scale from -1.0 (very bearish) to +1.0 (very bullish)."""


class SentimentAgent:
    """Agent that analyzes news sentiment and market sentiment."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()

    def get_recent_news(self, ticker: str) -> list:
        """Get recent news for a company."""
        return get_news(ticker)

    def analyze_sentiment(self, ticker: str) -> str:
        """Analyze overall sentiment for a company using news and Gemini."""
        news = self.get_recent_news(ticker)
        info = get_stock_info(ticker)
        company_name = info.get("longName") or info.get("shortName", ticker)

        # Build news context
        news_text = ""
        if news:
            news_items = []
            for item in news:
                title = item.get("title", "")
                publisher = item.get("publisher", "")
                if title:
                    news_items.append(f"- [{publisher}] {title}")
            news_text = "\n".join(news_items)
        else:
            news_text = "No recent news articles available."

        # Additional context from stock info
        stock_context = ""
        if info and "error" not in info:
            rec = info.get("recommendationKey", "N/A")
            target = info.get("targetMeanPrice", "N/A")
            current = info.get("currentPrice", "N/A")
            stock_context = f"""
Current Stock Context:
- Current Price: ${current}
- Analyst Recommendation: {rec}
- Mean Target Price: ${target}
- 52-Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}
"""

        prompt = f"""Analyze the current sentiment for {company_name} ({ticker.upper()}).

Recent News Headlines:
{news_text}

{stock_context}

Provide:
1. **Overall Sentiment Score**: Rate from -1.0 (very bearish) to +1.0 (very bullish)
2. **Sentiment Summary**: 2-3 sentence overview of current sentiment
3. **Key Positive Factors**: Bullish signals from news and data
4. **Key Negative Factors**: Bearish signals from news and data
5. **Sentiment Drivers**: What's driving the current sentiment
6. **Outlook**: Short-term sentiment outlook (1-4 weeks)
7. **Risk Events**: Upcoming events that could shift sentiment

Format your response clearly with headers and bullet points."""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def analyze_news_batch(self, tickers: list) -> str:
        """Analyze sentiment across multiple tickers."""
        all_news = {}
        for ticker in tickers:
            ticker = ticker.strip().upper()
            news = self.get_recent_news(ticker)
            all_news[ticker] = news

        news_summary = []
        for ticker, news_list in all_news.items():
            news_summary.append(f"\n{ticker}:")
            if news_list:
                for item in news_list[:5]:
                    news_summary.append(f"  - {item.get('title', 'N/A')}")
            else:
                news_summary.append("  - No recent news")

        prompt = f"""Analyze the sentiment across these companies based on recent news:

{"".join(news_summary)}

For each company, provide:
1. Sentiment score (-1.0 to +1.0)
2. Key sentiment driver
3. Notable news items

Then provide a comparative sentiment ranking and any sector-wide themes."""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def analyze_custom_text(self, text: str, context: str = "") -> str:
        """Analyze sentiment of custom text (e.g., earnings call transcript)."""
        prompt = f"""Analyze the sentiment of the following financial text:

{f'Context: {context}' if context else ''}

Text to analyze:
---
{text[:5000]}
---

Provide:
1. **Overall Sentiment**: Score from -1.0 to +1.0 with label
2. **Tone Analysis**: Management confidence level, forward-looking optimism
3. **Key Positive Statements**: Quotes or paraphrases
4. **Key Negative Statements**: Quotes or paraphrases
5. **Hidden Signals**: Subtle language changes or hedging
6. **Comparison**: How this compares to typical earnings call language"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
