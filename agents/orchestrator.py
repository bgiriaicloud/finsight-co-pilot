"""
Orchestrator Agent - Coordinates all specialist agents and manages workflow.
"""

from utils.gemini_client import GeminiClient
from agents.market_agent import MarketDataAgent
from agents.document_agent import DocumentAgent
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskAgent
from agents.report_agent import ReportAgent
from utils.gcp_client import gcp_client

SYSTEM_INSTRUCTION = """You are the Orchestrator of a multi-agent financial analysis system.
Your role is to understand user queries and provide comprehensive financial analysis.
You have access to data from multiple specialized agents:
- Market Data Agent: Real-time prices, fundamentals, ratios
- Document Agent: SEC filings (10-K, 10-Q) and XBRL data
- Sentiment Agent: News and market sentiment analysis
- Risk Agent: Risk assessment and red flag detection
- Report Agent: Investment thesis and report generation

When answering user queries:
1. Synthesize information from all relevant data sources
2. Provide specific numbers and metrics
3. Be balanced and objective in your analysis
4. Use professional financial language
5. Format responses clearly with headers and bullet points
6. Always cite data sources when possible"""


class Orchestrator:
    """Central coordinator for all financial analysis agents."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()
        self.market_agent = MarketDataAgent()
        self.document_agent = DocumentAgent()
        self.sentiment_agent = SentimentAgent()
        self.risk_agent = RiskAgent()
        self.report_agent = ReportAgent()

    def _extract_tickers(self, query: str) -> list:
        """Use Gemini to extract stock tickers from a user query."""
        prompt = f"""Extract all stock ticker symbols mentioned in this query.
Return ONLY a comma-separated list of tickers (e.g., AAPL, MSFT, GOOGL).
If no specific tickers are mentioned, return NONE.

Query: {query}

Tickers:"""
        result = self.gemini.generate(prompt, temperature=0.0, max_tokens=100)
        result = result.strip().upper()
        if result == "NONE" or not result:
            return []
        tickers = [t.strip() for t in result.split(",") if t.strip().isalpha()]
        return tickers

    def _classify_intent(self, query: str) -> str:
        """Classify the user's intent to route to the right agent(s)."""
        prompt = f"""Classify this financial query into ONE of the following categories:
- MARKET_ANALYSIS: Questions about stock prices, valuation, financials, metrics
- DOCUMENT_ANALYSIS: Questions about SEC filings, 10-K, 10-Q, financial statements
- SENTIMENT: Questions about news, market sentiment, analyst opinions
- RISK_ASSESSMENT: Questions about risks, red flags, financial health concerns
- INVESTMENT_THESIS: Requests for buy/sell recommendations, investment analysis
- PEER_COMPARISON: Comparing multiple companies
- EARNINGS: Questions about earnings, revenue, profits
- GENERAL: General financial questions or education

Query: {query}

Category:"""
        result = self.gemini.generate(prompt, temperature=0.0, max_tokens=50)
        return result.strip().upper().replace(" ", "_")

    def process_query(self, query: str, status_callback=None) -> str:
        """Process a user query by routing to appropriate agents."""
        # Step 1: Extract tickers
        if status_callback:
            status_callback("orchestrator", "Analyzing your query...")

        tickers = self._extract_tickers(query)
        intent = self._classify_intent(query)
        
        # Log start of analysis to BigQuery
        gcp_client.log_activity(", ".join(tickers) if tickers else "GEN", intent, "STARTED")

        # Step 2: Route to appropriate agent(s) based on intent
        response = ""
        if "INVESTMENT_THESIS" in intent and tickers:
            if status_callback:
                status_callback("market", f"Fetching market data for {', '.join(tickers)}...")
                status_callback("document", "Analyzing SEC filings...")
                status_callback("sentiment", "Analyzing news sentiment...")
                status_callback("risk", "Assessing risk factors...")
                status_callback("report", "Generating investment thesis...")
            response = self.report_agent.generate_investment_thesis(tickers[0])

        elif "PEER_COMPARISON" in intent and len(tickers) >= 2:
            if status_callback:
                status_callback("market", f"Comparing: {', '.join(tickers)}...")
                status_callback("report", "Generating comparison report...")
            response = self.report_agent.generate_comparison_report(tickers)

        elif "RISK" in intent and tickers:
            if status_callback:
                status_callback("risk", f"Analyzing risks for {', '.join(tickers)}...")
            if len(tickers) > 1:
                response = self.risk_agent.compare_risks(tickers)
            else:
                response = self.risk_agent.comprehensive_risk_analysis(tickers[0])

        elif "SENTIMENT" in intent and tickers:
            if status_callback:
                status_callback("sentiment", f"Analyzing sentiment for {', '.join(tickers)}...")
            if len(tickers) > 1:
                response = self.sentiment_agent.analyze_news_batch(tickers)
            else:
                response = self.sentiment_agent.analyze_sentiment(tickers[0])

        elif "EARNINGS" in intent and tickers:
            if status_callback:
                status_callback("market", "Pulling earnings data...")
                status_callback("report", "Generating earnings analysis...")
            response = self.report_agent.generate_earnings_analysis(tickers[0])

        elif "DOCUMENT" in intent and tickers:
            if status_callback:
                status_callback("document", f"Analyzing filings for {tickers[0]}...")
            response = self.document_agent.analyze_filing_with_ai(tickers[0], query)

        elif "MARKET" in intent and tickers:
            if status_callback:
                status_callback("market", f"Analyzing market data for {', '.join(tickers)}...")
            if len(tickers) > 1:
                response = self.market_agent.compare_with_ai(tickers, query)
            else:
                response = self.market_agent.analyze_with_ai(tickers[0], query)

        elif tickers:
            # Default: comprehensive analysis with multiple agents
            if status_callback:
                status_callback("orchestrator", "Running comprehensive analysis...")
                status_callback("market", f"Fetching data for {', '.join(tickers)}...")

            if len(tickers) > 1:
                response = self.market_agent.compare_with_ai(tickers, query)
            else:
                response = self._comprehensive_single_stock(tickers[0], query, status_callback)

        else:
            # General question - use Gemini directly with financial context
            if status_callback:
                status_callback("orchestrator", "Processing general query...")
            response = self.gemini.generate(query, system_instruction=SYSTEM_INSTRUCTION)
            
        # Log completion to BigQuery and notify Pub/Sub
        gcp_client.log_activity(", ".join(tickers) if tickers else "GEN", intent, "COMPLETED")
        if tickers:
            gcp_client.publish_analysis_complete(tickers[0], intent, response)
            
        return response

    def _comprehensive_single_stock(self, ticker: str, query: str, status_callback=None) -> str:
        """Provide comprehensive analysis for a single stock."""
        if status_callback:
            status_callback("market", "Analyzing market data...")

        market_data = self.market_agent.get_company_overview(ticker)

        if status_callback:
            status_callback("document", "Checking SEC filings...")

        filings = self.document_agent.get_filings_list(ticker, "10-K", 2)

        if status_callback:
            status_callback("risk", "Assessing risks...")

        risk_data = self.risk_agent.assess_financial_risk(ticker)

        # Build comprehensive context
        context = f"""
Company: {market_data.get('name', ticker)} ({ticker.upper()})
Sector: {market_data.get('sector', 'N/A')} | Industry: {market_data.get('industry', 'N/A')}

Price: ${market_data.get('current_price', 'N/A')} | Market Cap: {market_data.get('market_cap_formatted', 'N/A')}
P/E: {market_data.get('pe_ratio', 'N/A')} | Forward P/E: {market_data.get('forward_pe', 'N/A')}
Revenue Growth: {market_data.get('revenue_growth', 'N/A')} | Earnings Growth: {market_data.get('earnings_growth', 'N/A')}
Gross Margin: {market_data.get('gross_margins', 'N/A')} | Op Margin: {market_data.get('operating_margins', 'N/A')}
Analyst Recommendation: {market_data.get('recommendation', 'N/A')} | Target: ${market_data.get('analyst_target', 'N/A')}

Recent 10-K Filings: {len(filings)} found
Risk Indicators:
"""
        for key, val in risk_data.items():
            if isinstance(val, dict) and "level" in val:
                context += f"  - {key.replace('_', ' ').title()}: {val['level']}\n"

        prompt = f"""Using this comprehensive data about {ticker.upper()}, answer the user's question:

User Question: {query}

{context}

Provide a thorough, data-driven response. Reference specific metrics and data points."""

        if status_callback:
            status_callback("orchestrator", "Generating final response...")

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
