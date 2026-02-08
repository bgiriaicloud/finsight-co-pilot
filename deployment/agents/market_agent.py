"""
Market Data Agent - Retrieves and analyzes market data using Yahoo Finance.
"""

import pandas as pd
from utils.data_providers import (
    get_stock_info,
    get_price_history,
    get_financials,
    get_key_metrics,
    get_analyst_recommendations,
    format_large_number,
    format_percentage,
)
from utils.gemini_client import GeminiClient

SYSTEM_INSTRUCTION = """You are an expert financial market analyst agent. Your role is to:
1. Analyze stock market data including prices, fundamentals, and ratios
2. Provide clear, concise insights based on quantitative data
3. Compare companies using standard financial metrics
4. Identify trends in price movement and financial performance
5. Always cite specific numbers and metrics in your analysis
6. Use professional financial terminology
Format your responses with clear headers and bullet points."""


class MarketDataAgent:
    """Agent that retrieves and analyzes market data."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()

    def get_company_overview(self, ticker: str) -> dict:
        """Get a comprehensive company overview with key metrics."""
        metrics = get_key_metrics(ticker)
        if "error" in metrics:
            return {"error": f"Could not fetch data for {ticker}: {metrics['error']}"}

        price_hist = get_price_history(ticker, period="1y")

        overview = {
            "ticker": ticker.upper(),
            "name": metrics.get("longName") or metrics.get("shortName", ticker),
            "sector": metrics.get("sector", "N/A"),
            "industry": metrics.get("industry", "N/A"),
            "current_price": metrics.get("currentPrice"),
            "market_cap": metrics.get("marketCap"),
            "market_cap_formatted": format_large_number(metrics.get("marketCap")),
            "pe_ratio": metrics.get("trailingPE"),
            "forward_pe": metrics.get("forwardPE"),
            "peg_ratio": metrics.get("pegRatio"),
            "price_to_book": metrics.get("priceToBook"),
            "dividend_yield": metrics.get("dividendYield"),
            "beta": metrics.get("beta"),
            "52w_high": metrics.get("fiftyTwoWeekHigh"),
            "52w_low": metrics.get("fiftyTwoWeekLow"),
            "revenue_growth": metrics.get("revenueGrowth"),
            "earnings_growth": metrics.get("earningsGrowth"),
            "gross_margins": metrics.get("grossMargins"),
            "operating_margins": metrics.get("operatingMargins"),
            "profit_margins": metrics.get("profitMargins"),
            "roe": metrics.get("returnOnEquity"),
            "roa": metrics.get("returnOnAssets"),
            "debt_to_equity": metrics.get("debtToEquity"),
            "current_ratio": metrics.get("currentRatio"),
            "total_revenue": metrics.get("totalRevenue"),
            "total_revenue_formatted": format_large_number(metrics.get("totalRevenue")),
            "free_cash_flow": metrics.get("freeCashflow"),
            "free_cash_flow_formatted": format_large_number(metrics.get("freeCashflow")),
            "analyst_target": metrics.get("targetMeanPrice"),
            "recommendation": metrics.get("recommendationKey"),
            "num_analysts": metrics.get("numberOfAnalystOpinions"),
            "employees": metrics.get("fullTimeEmployees"),
            "price_history": price_hist,
        }
        return overview

    def compare_companies(self, tickers: list) -> dict:
        """Compare multiple companies on key metrics."""
        comparison = {}
        for ticker in tickers:
            ticker = ticker.strip().upper()
            overview = self.get_company_overview(ticker)
            comparison[ticker] = overview
        return comparison

    def get_financial_statements(self, ticker: str) -> dict:
        """Get financial statements for a company."""
        return get_financials(ticker)

    def analyze_with_ai(self, ticker: str, query: str = None) -> str:
        """Use Gemini to analyze market data for a company."""
        overview = self.get_company_overview(ticker)
        if "error" in overview:
            return overview["error"]

        # Build context from real data
        data_summary = f"""
Company: {overview['name']} ({overview['ticker']})
Sector: {overview['sector']} | Industry: {overview['industry']}

PRICE DATA:
- Current Price: ${overview.get('current_price', 'N/A')}
- 52-Week High: ${overview.get('52w_high', 'N/A')}
- 52-Week Low: ${overview.get('52w_low', 'N/A')}
- Beta: {overview.get('beta', 'N/A')}

VALUATION:
- Market Cap: {overview['market_cap_formatted']}
- P/E (TTM): {overview.get('pe_ratio', 'N/A')}
- Forward P/E: {overview.get('forward_pe', 'N/A')}
- PEG Ratio: {overview.get('peg_ratio', 'N/A')}
- Price/Book: {overview.get('price_to_book', 'N/A')}

PROFITABILITY:
- Gross Margins: {format_percentage(overview.get('gross_margins'))}
- Operating Margins: {format_percentage(overview.get('operating_margins'))}
- Profit Margins: {format_percentage(overview.get('profit_margins'))}
- ROE: {format_percentage(overview.get('roe'))}
- ROA: {format_percentage(overview.get('roa'))}

GROWTH:
- Revenue Growth: {format_percentage(overview.get('revenue_growth'))}
- Earnings Growth: {format_percentage(overview.get('earnings_growth'))}
- Total Revenue: {overview['total_revenue_formatted']}
- Free Cash Flow: {overview['free_cash_flow_formatted']}

FINANCIAL HEALTH:
- Debt/Equity: {overview.get('debt_to_equity', 'N/A')}
- Current Ratio: {overview.get('current_ratio', 'N/A')}

ANALYST CONSENSUS:
- Recommendation: {overview.get('recommendation', 'N/A')}
- Target Price: ${overview.get('analyst_target', 'N/A')}
- Number of Analysts: {overview.get('num_analysts', 'N/A')}
"""

        if query:
            prompt = f"""Based on the following market data, answer this question: {query}

{data_summary}

Provide a detailed, data-driven analysis. Reference specific metrics in your answer."""
        else:
            prompt = f"""Provide a comprehensive market analysis for this company based on the data:

{data_summary}

Include:
1. Valuation assessment (overvalued/undervalued/fair)
2. Growth trajectory analysis
3. Profitability comparison to typical industry benchmarks
4. Financial health assessment
5. Key strengths and concerns
6. Brief investment outlook"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def compare_with_ai(self, tickers: list, query: str = None) -> str:
        """Use Gemini to generate AI comparison of multiple companies."""
        comparison = self.compare_companies(tickers)

        data_parts = []
        for ticker, overview in comparison.items():
            if "error" in overview:
                data_parts.append(f"\n{ticker}: Data unavailable")
                continue
            data_parts.append(f"""
--- {overview.get('name', ticker)} ({ticker}) ---
Price: ${overview.get('current_price', 'N/A')} | Market Cap: {overview.get('market_cap_formatted', 'N/A')}
P/E: {overview.get('pe_ratio', 'N/A')} | Fwd P/E: {overview.get('forward_pe', 'N/A')} | PEG: {overview.get('peg_ratio', 'N/A')}
Gross Margin: {format_percentage(overview.get('gross_margins'))} | Op Margin: {format_percentage(overview.get('operating_margins'))} | Net Margin: {format_percentage(overview.get('profit_margins'))}
Rev Growth: {format_percentage(overview.get('revenue_growth'))} | EPS Growth: {format_percentage(overview.get('earnings_growth'))}
ROE: {format_percentage(overview.get('roe'))} | D/E: {overview.get('debt_to_equity', 'N/A')}
Revenue: {overview.get('total_revenue_formatted', 'N/A')} | FCF: {overview.get('free_cash_flow_formatted', 'N/A')}
Analyst: {overview.get('recommendation', 'N/A')} | Target: ${overview.get('analyst_target', 'N/A')}
""")

        data_text = "\n".join(data_parts)

        if query:
            prompt = f"""{query}

Here is the current market data for comparison:
{data_text}

Provide a detailed comparative analysis based on this data."""
        else:
            prompt = f"""Compare these companies based on the following data:
{data_text}

Provide:
1. Valuation comparison table
2. Growth comparison
3. Profitability comparison
4. Financial health comparison
5. Which company appears most attractive and why
6. Key risks for each"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
