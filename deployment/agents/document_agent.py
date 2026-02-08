"""
Document Agent - Processes SEC filings and uploaded documents using Gemini.
"""

from utils.data_providers import (
    get_company_filings,
    get_company_facts,
    get_company_info_sec,
)
from utils.gemini_client import GeminiClient

SYSTEM_INSTRUCTION = """You are an expert SEC filing and financial document analyst agent.
Your role is to:
1. Parse and analyze SEC filings (10-K, 10-Q, 8-K)
2. Extract key financial data, metrics, and risk factors
3. Identify important changes between reporting periods
4. Provide analysis with specific citations to filing sections
5. Understand document structure (Item 1, 1A, 7, 8, etc.)
Always reference specific sections, page numbers, or items when citing information.
Format responses with clear headers and structured data."""


class DocumentAgent:
    """Agent that processes and analyzes financial documents and SEC filings."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()

    def get_filings_list(self, ticker: str, filing_type: str = "10-K", count: int = 5) -> list:
        """Get list of recent filings for a company."""
        return get_company_filings(ticker, filing_type, count)

    def get_xbrl_facts(self, ticker: str) -> dict:
        """Get structured XBRL data from SEC for a company."""
        return get_company_facts(ticker)

    def extract_key_metrics_from_xbrl(self, ticker: str) -> dict:
        """Extract key financial metrics from XBRL data."""
        facts = get_company_facts(ticker)
        if "error" in facts:
            return facts

        metrics = {}
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        key_items = {
            "Revenues": "revenue",
            "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
            "NetIncomeLoss": "net_income",
            "EarningsPerShareBasic": "eps_basic",
            "EarningsPerShareDiluted": "eps_diluted",
            "Assets": "total_assets",
            "Liabilities": "total_liabilities",
            "StockholdersEquity": "stockholders_equity",
            "OperatingIncomeLoss": "operating_income",
            "GrossProfit": "gross_profit",
            "CashAndCashEquivalentsAtCarryingValue": "cash",
            "LongTermDebt": "long_term_debt",
            "CommonStockSharesOutstanding": "shares_outstanding",
        }

        for xbrl_key, label in key_items.items():
            if xbrl_key in us_gaap:
                units = us_gaap[xbrl_key].get("units", {})
                # Get USD values (or shares for share counts)
                for unit_type in ["USD", "USD/shares", "shares"]:
                    if unit_type in units:
                        values = units[unit_type]
                        # Get the most recent annual values
                        annual_values = [
                            v for v in values
                            if v.get("form") in ("10-K", "10-K/A")
                            and "frame" not in v  # Exclude frame aggregated data
                        ]
                        if annual_values:
                            # Sort by end date and get the last few
                            annual_values.sort(key=lambda x: x.get("end", ""))
                            recent = annual_values[-3:]  # Last 3 years
                            metrics[label] = [
                                {
                                    "value": v.get("val"),
                                    "period_end": v.get("end"),
                                    "period_start": v.get("start", ""),
                                    "filed": v.get("filed", ""),
                                }
                                for v in recent
                            ]
                        break
        return metrics

    def analyze_filing_with_ai(self, ticker: str, query: str = None) -> str:
        """Analyze a company's SEC filings using XBRL data and Gemini."""
        sec_info = get_company_info_sec(ticker)
        xbrl_metrics = self.extract_key_metrics_from_xbrl(ticker)
        filings = self.get_filings_list(ticker, "10-K", 3)

        # Build context
        context_parts = [
            f"Company: {sec_info.get('name', ticker)} ({ticker.upper()})",
            f"SIC: {sec_info.get('sic_description', 'N/A')}",
            f"Fiscal Year End: {sec_info.get('fiscal_year_end', 'N/A')}",
            f"\nRecent 10-K Filings:",
        ]
        for f in filings:
            if "error" not in f:
                context_parts.append(f"  - Filed: {f.get('filing_date', 'N/A')} | {f.get('description', '')}")

        context_parts.append("\nKey Financial Metrics (from XBRL filings):")
        for metric_name, values in xbrl_metrics.items():
            if isinstance(values, list):
                context_parts.append(f"\n  {metric_name.replace('_', ' ').title()}:")
                for v in values:
                    val = v.get("value")
                    if val is not None:
                        if isinstance(val, (int, float)) and abs(val) > 1e6:
                            val_str = f"${val / 1e6:,.1f}M" if abs(val) < 1e9 else f"${val / 1e9:,.2f}B"
                        else:
                            val_str = f"{val:,.2f}" if isinstance(val, float) else str(val)
                        context_parts.append(
                            f"    Period ending {v.get('period_end', 'N/A')}: {val_str}"
                        )

        context = "\n".join(context_parts)

        if query:
            prompt = f"""Based on the following SEC filing data for {ticker.upper()}, answer this question:
{query}

{context}

Provide a thorough analysis citing specific metrics and trends. If the data is insufficient to fully answer,
note what additional information would be needed."""
        else:
            prompt = f"""Provide a comprehensive analysis of {ticker.upper()}'s SEC filings based on this data:

{context}

Include:
1. Revenue and earnings trends (year-over-year changes)
2. Profitability analysis
3. Balance sheet strength
4. Key changes or trends observed
5. Notable items that warrant further investigation"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def analyze_uploaded_document(self, file_bytes: bytes, filename: str, query: str) -> str:
        """Analyze an uploaded document (PDF) using Gemini's multimodal capabilities."""
        if not query:
            query = """Analyze this financial document comprehensively. Extract:
1. Key financial metrics and data points
2. Important risk factors
3. Management's discussion highlights
4. Any notable changes from prior periods
5. Summary of key findings
Format with clear sections and bullet points."""

        return self.gemini.analyze_document(file_bytes, query, filename)
