"""
Report Agent - Generates comprehensive investment reports and theses.
"""

from utils.data_providers import (
    get_key_metrics,
    get_stock_info,
    get_news,
    format_large_number,
    format_percentage,
)
from utils.gemini_client import GeminiClient

SYSTEM_INSTRUCTION = """You are an expert investment report generator agent. Your role is to:
1. Generate professional, institutional-grade investment reports
2. Create comprehensive investment theses with bull/bear cases
3. Provide clear, actionable recommendations with price targets
4. Include quantitative analysis with qualitative insights
5. Structure reports in a professional format suitable for portfolio managers
6. Always include specific data points, metrics, and citations

Report Quality Standards:
- Use precise financial language
- Include specific numbers and percentages
- Present balanced bull/bear perspectives
- Provide clear rationale for recommendations
- Structure with executive summary, detailed analysis, and conclusion"""


class ReportAgent:
    """Agent that generates investment reports and theses."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()

    def generate_investment_thesis(self, ticker: str) -> str:
        """Generate a comprehensive investment thesis for a company."""
        metrics = get_key_metrics(ticker)
        news = get_news(ticker)

        company_name = metrics.get("longName") or metrics.get("shortName", ticker)

        news_headlines = "\n".join(
            [f"- {n.get('title', '')}" for n in news[:8]]
        ) if news else "No recent news available."

        data_context = f"""
COMPANY: {company_name} ({ticker.upper()})
Sector: {metrics.get('sector', 'N/A')} | Industry: {metrics.get('industry', 'N/A')}
Employees: {metrics.get('fullTimeEmployees', 'N/A'):,} 

CURRENT VALUATION:
- Stock Price: ${metrics.get('currentPrice', 'N/A')}
- Market Cap: {format_large_number(metrics.get('marketCap'))}
- Enterprise Value: {format_large_number(metrics.get('enterpriseValue'))}
- P/E (TTM): {metrics.get('trailingPE', 'N/A')}
- Forward P/E: {metrics.get('forwardPE', 'N/A')}
- PEG Ratio: {metrics.get('pegRatio', 'N/A')}
- Price/Book: {metrics.get('priceToBook', 'N/A')}
- EV/Revenue: {round(metrics.get('enterpriseValue', 0) / metrics.get('totalRevenue', 1), 2) if metrics.get('enterpriseValue') and metrics.get('totalRevenue') else 'N/A'}

FINANCIAL PERFORMANCE:
- Revenue: {format_large_number(metrics.get('totalRevenue'))}
- Revenue Growth: {format_percentage(metrics.get('revenueGrowth'))}
- Gross Margins: {format_percentage(metrics.get('grossMargins'))}
- Operating Margins: {format_percentage(metrics.get('operatingMargins'))}
- Net Margins: {format_percentage(metrics.get('profitMargins'))}
- EPS (TTM): ${metrics.get('trailingEps', 'N/A')}
- EPS (Forward): ${metrics.get('forwardEps', 'N/A')}
- ROE: {format_percentage(metrics.get('returnOnEquity'))}
- ROA: {format_percentage(metrics.get('returnOnAssets'))}

BALANCE SHEET:
- Total Cash: {format_large_number(metrics.get('totalCash'))}
- Total Debt: {format_large_number(metrics.get('totalDebt'))}
- Debt/Equity: {metrics.get('debtToEquity', 'N/A')}
- Current Ratio: {metrics.get('currentRatio', 'N/A')}
- Free Cash Flow: {format_large_number(metrics.get('freeCashflow'))}
- Operating Cash Flow: {format_large_number(metrics.get('operatingCashflow'))}

MARKET DATA:
- Beta: {metrics.get('beta', 'N/A')}
- 52-Week High: ${metrics.get('fiftyTwoWeekHigh', 'N/A')}
- 52-Week Low: ${metrics.get('fiftyTwoWeekLow', 'N/A')}
- 50-Day Average: ${metrics.get('fiftyDayAverage', 'N/A')}
- 200-Day Average: ${metrics.get('twoHundredDayAverage', 'N/A')}
- Dividend Yield: {format_percentage(metrics.get('dividendYield'))}

ANALYST CONSENSUS:
- Recommendation: {metrics.get('recommendationKey', 'N/A').upper()}
- Target High: ${metrics.get('targetHighPrice', 'N/A')}
- Target Low: ${metrics.get('targetLowPrice', 'N/A')}
- Target Mean: ${metrics.get('targetMeanPrice', 'N/A')}
- Number of Analysts: {metrics.get('numberOfAnalystOpinions', 'N/A')}

RECENT NEWS:
{news_headlines}
"""

        prompt = f"""Generate a comprehensive investment thesis report for {company_name} ({ticker.upper()}).

{data_context}

Create a professional investment report with the following structure:

# {company_name} ({ticker.upper()}) - Investment Thesis

## Executive Summary
- Rating (Strong Buy / Buy / Hold / Sell / Strong Sell)
- Target Price with upside/downside percentage
- 1-paragraph thesis summary

## Company Overview
- Business description and competitive position
- Key products/services and revenue drivers
- Market position and competitive moats

## Financial Analysis
- Revenue and earnings trends
- Profitability assessment
- Balance sheet strength
- Cash flow analysis

## Valuation Assessment
- Current valuation vs. historical averages
- Peer comparison context
- Is the stock overvalued, undervalued, or fairly valued?

## Bull Case (with target price)
- 3-5 key catalysts and positive scenarios
- Upside target price and rationale

## Bear Case (with target price)
- 3-5 key risks and negative scenarios
- Downside target price and rationale

## Key Catalysts & Timeline
- Upcoming events that could move the stock
- Expected timing of catalysts

## Risk Factors
- Top 5 risks with severity assessment

## Conclusion & Recommendation
- Final recommendation with confidence level
- Position sizing suggestion (e.g., core position vs. starter)
- Key metrics to monitor

Use specific numbers from the data provided. Be balanced and objective."""

        return self.gemini.generate(
            prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.4,
            max_tokens=8192,
        )

    def generate_earnings_analysis(self, ticker: str) -> str:
        """Generate an earnings analysis report for a company."""
        metrics = get_key_metrics(ticker)
        company_name = metrics.get("longName") or metrics.get("shortName", ticker)
        news = get_news(ticker)

        news_text = "\n".join([f"- {n.get('title', '')}" for n in news[:5]]) if news else "None available"

        prompt = f"""Generate an earnings analysis report for {company_name} ({ticker.upper()}).

Current Financial Metrics:
- Revenue: {format_large_number(metrics.get('totalRevenue'))}
- Revenue Growth: {format_percentage(metrics.get('revenueGrowth'))}
- EPS (TTM): ${metrics.get('trailingEps', 'N/A')}
- EPS (Forward): ${metrics.get('forwardEps', 'N/A')}
- Gross Margin: {format_percentage(metrics.get('grossMargins'))}
- Operating Margin: {format_percentage(metrics.get('operatingMargins'))}
- Net Margin: {format_percentage(metrics.get('profitMargins'))}
- Earnings Growth: {format_percentage(metrics.get('earningsGrowth'))}

Recent News: {news_text}

Generate a comprehensive earnings analysis including:
1. **Earnings Overview** - Key numbers and what they mean
2. **Revenue Analysis** - Growth drivers and headwinds
3. **Margin Analysis** - Profitability trends
4. **Key Takeaways** - Most important findings
5. **Forward Outlook** - What to expect going forward
6. **Market Reaction Context** - How the market may interpret these numbers"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def generate_comparison_report(self, tickers: list) -> str:
        """Generate a peer comparison report."""
        all_data = {}
        for ticker in tickers:
            ticker = ticker.strip().upper()
            all_data[ticker] = get_key_metrics(ticker)

        data_text = []
        for ticker, metrics in all_data.items():
            name = metrics.get("longName") or metrics.get("shortName", ticker)
            data_text.append(f"""
--- {name} ({ticker}) ---
Price: ${metrics.get('currentPrice', 'N/A')} | Market Cap: {format_large_number(metrics.get('marketCap'))}
P/E: {metrics.get('trailingPE', 'N/A')} | Fwd P/E: {metrics.get('forwardPE', 'N/A')} | PEG: {metrics.get('pegRatio', 'N/A')}
Revenue: {format_large_number(metrics.get('totalRevenue'))} | Rev Growth: {format_percentage(metrics.get('revenueGrowth'))}
Gross: {format_percentage(metrics.get('grossMargins'))} | Op: {format_percentage(metrics.get('operatingMargins'))} | Net: {format_percentage(metrics.get('profitMargins'))}
ROE: {format_percentage(metrics.get('returnOnEquity'))} | D/E: {metrics.get('debtToEquity', 'N/A')}
FCF: {format_large_number(metrics.get('freeCashflow'))} | Analyst: {metrics.get('recommendationKey', 'N/A')}
""")

        prompt = f"""Generate a peer comparison report for: {', '.join(tickers)}

Data:
{"".join(data_text)}

Create a professional comparison report with:
1. **Executive Summary** - Key takeaway about which companies stand out
2. **Comparison Table** - Side-by-side metrics comparison
3. **Valuation Comparison** - Which offers the best value
4. **Growth Comparison** - Which has the strongest growth profile
5. **Profitability Comparison** - Which is most profitable
6. **Financial Health** - Which has the strongest balance sheet
7. **Rankings** - Overall ranking with rationale
8. **Investment Implications** - Which to buy/hold/avoid and why"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
