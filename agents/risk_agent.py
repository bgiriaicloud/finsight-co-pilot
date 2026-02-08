"""
Risk Agent - Identifies and assesses risk factors for companies.
"""

from utils.data_providers import (
    get_key_metrics,
    get_company_filings,
    format_percentage,
    format_large_number,
)
from utils.gemini_client import GeminiClient

SYSTEM_INSTRUCTION = """You are an expert financial risk analyst agent. Your role is to:
1. Identify and categorize risk factors for companies
2. Assess the severity and likelihood of each risk
3. Compare risks across peer companies
4. Detect red flags in financial data
5. Evaluate financial health and stability metrics
6. Provide actionable risk mitigation insights

Risk categories to consider:
- Market Risk (competition, demand, pricing)
- Financial Risk (leverage, liquidity, currency)
- Operational Risk (supply chain, technology, talent)
- Regulatory Risk (compliance, litigation, policy changes)
- Strategic Risk (M&A, innovation, market shifts)
- ESG Risk (environmental, social, governance)

Always rate severity as: Critical / High / Medium / Low
Format responses with structured risk tables and clear explanations."""


class RiskAgent:
    """Agent that identifies and assesses risk factors."""

    def __init__(self):
        self.gemini = GeminiClient.get_instance()

    def assess_financial_risk(self, ticker: str) -> dict:
        """Assess financial risk based on key metrics."""
        metrics = get_key_metrics(ticker)
        if "error" in metrics:
            return {"error": metrics["error"]}

        risk_indicators = {
            "ticker": ticker.upper(),
            "company": metrics.get("longName") or metrics.get("shortName", ticker),
        }

        # Leverage risk
        de = metrics.get("debtToEquity")
        if de is not None:
            if de > 200:
                risk_indicators["leverage_risk"] = {"level": "Critical", "value": de, "note": "Very high leverage"}
            elif de > 100:
                risk_indicators["leverage_risk"] = {"level": "High", "value": de, "note": "High leverage"}
            elif de > 50:
                risk_indicators["leverage_risk"] = {"level": "Medium", "value": de, "note": "Moderate leverage"}
            else:
                risk_indicators["leverage_risk"] = {"level": "Low", "value": de, "note": "Conservative leverage"}

        # Liquidity risk
        cr = metrics.get("currentRatio")
        if cr is not None:
            if cr < 0.5:
                risk_indicators["liquidity_risk"] = {"level": "Critical", "value": cr, "note": "Severe liquidity concern"}
            elif cr < 1.0:
                risk_indicators["liquidity_risk"] = {"level": "High", "value": cr, "note": "Below 1x current ratio"}
            elif cr < 1.5:
                risk_indicators["liquidity_risk"] = {"level": "Medium", "value": cr, "note": "Adequate liquidity"}
            else:
                risk_indicators["liquidity_risk"] = {"level": "Low", "value": cr, "note": "Strong liquidity"}

        # Valuation risk
        pe = metrics.get("trailingPE")
        if pe is not None:
            if pe > 60:
                risk_indicators["valuation_risk"] = {"level": "High", "value": pe, "note": "Very high P/E, elevated expectations"}
            elif pe > 30:
                risk_indicators["valuation_risk"] = {"level": "Medium", "value": pe, "note": "Above-average valuation"}
            elif pe > 0:
                risk_indicators["valuation_risk"] = {"level": "Low", "value": pe, "note": "Reasonable valuation"}
            else:
                risk_indicators["valuation_risk"] = {"level": "High", "value": pe, "note": "Negative earnings"}

        # Profitability risk
        margins = metrics.get("profitMargins")
        if margins is not None:
            if margins < 0:
                risk_indicators["profitability_risk"] = {"level": "High", "value": margins, "note": "Unprofitable"}
            elif margins < 0.05:
                risk_indicators["profitability_risk"] = {"level": "Medium", "value": margins, "note": "Thin margins"}
            else:
                risk_indicators["profitability_risk"] = {"level": "Low", "value": margins, "note": "Healthy margins"}

        # Growth risk
        rev_growth = metrics.get("revenueGrowth")
        if rev_growth is not None:
            if rev_growth < -0.1:
                risk_indicators["growth_risk"] = {"level": "High", "value": rev_growth, "note": "Revenue declining"}
            elif rev_growth < 0:
                risk_indicators["growth_risk"] = {"level": "Medium", "value": rev_growth, "note": "Slight revenue decline"}
            else:
                risk_indicators["growth_risk"] = {"level": "Low", "value": rev_growth, "note": "Positive growth"}

        # Volatility risk
        beta = metrics.get("beta")
        if beta is not None:
            if beta > 2.0:
                risk_indicators["volatility_risk"] = {"level": "High", "value": beta, "note": "Very high beta"}
            elif beta > 1.2:
                risk_indicators["volatility_risk"] = {"level": "Medium", "value": beta, "note": "Above-market volatility"}
            else:
                risk_indicators["volatility_risk"] = {"level": "Low", "value": beta, "note": "Low to moderate volatility"}

        return risk_indicators

    def comprehensive_risk_analysis(self, ticker: str) -> str:
        """Generate a comprehensive AI-powered risk analysis."""
        metrics = get_key_metrics(ticker)
        risk_data = self.assess_financial_risk(ticker)
        filings = get_company_filings(ticker, "10-K", 1)

        data_context = f"""
Company: {risk_data.get('company', ticker)} ({ticker.upper()})

FINANCIAL METRICS:
- Market Cap: {format_large_number(metrics.get('marketCap'))}
- Revenue: {format_large_number(metrics.get('totalRevenue'))}
- Revenue Growth: {format_percentage(metrics.get('revenueGrowth'))}
- Gross Margins: {format_percentage(metrics.get('grossMargins'))}
- Operating Margins: {format_percentage(metrics.get('operatingMargins'))}
- Net Margins: {format_percentage(metrics.get('profitMargins'))}
- Debt/Equity: {metrics.get('debtToEquity', 'N/A')}
- Current Ratio: {metrics.get('currentRatio', 'N/A')}
- P/E Ratio: {metrics.get('trailingPE', 'N/A')}
- Beta: {metrics.get('beta', 'N/A')}
- ROE: {format_percentage(metrics.get('returnOnEquity'))}
- Free Cash Flow: {format_large_number(metrics.get('freeCashflow'))}

QUANTITATIVE RISK ASSESSMENT:
"""
        for key, val in risk_data.items():
            if isinstance(val, dict) and "level" in val:
                data_context += f"- {key.replace('_', ' ').title()}: {val['level']} ({val['note']})\n"

        prompt = f"""Provide a comprehensive risk assessment for {ticker.upper()} based on the data below:

{data_context}

Generate a professional risk report with:

1. **Executive Risk Summary** (2-3 sentences)

2. **Risk Scorecard** (rate each 1-10):
   - Financial Risk
   - Market/Competitive Risk
   - Operational Risk
   - Regulatory/Legal Risk
   - Strategic Risk
   - Overall Risk Score

3. **Key Risk Factors** (top 5, with severity rating):
   For each: Description, Severity (Critical/High/Medium/Low), Likelihood, Potential Impact

4. **Red Flags** - Any warning signs in the data

5. **Risk Mitigation Factors** - Positive indicators that offset risks

6. **Peer Context** - How these risks compare to typical industry peers

7. **Monitoring Recommendations** - Key metrics to watch"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    def compare_risks(self, tickers: list) -> str:
        """Compare risk profiles across multiple companies."""
        risk_profiles = {}
        for ticker in tickers:
            ticker = ticker.strip().upper()
            risk_profiles[ticker] = self.assess_financial_risk(ticker)

        profile_text = []
        for ticker, profile in risk_profiles.items():
            profile_text.append(f"\n--- {profile.get('company', ticker)} ({ticker}) ---")
            for key, val in profile.items():
                if isinstance(val, dict) and "level" in val:
                    profile_text.append(f"  {key.replace('_', ' ').title()}: {val['level']} - {val['note']}")

        prompt = f"""Compare the risk profiles of these companies:

{"".join(profile_text)}

Provide:
1. **Comparative Risk Matrix** (table format)
2. **Company-by-Company Risk Summary**
3. **Shared Risks** - Common risks across all companies
4. **Unique Risks** - Risks specific to individual companies
5. **Risk-Adjusted Ranking** - Which company has the best risk profile and why
6. **Key Takeaways** for investors"""

        return self.gemini.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
