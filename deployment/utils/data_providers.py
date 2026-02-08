"""
Data providers for SEC EDGAR, Yahoo Finance, and news sources.
"""

import requests
import yfinance as yf
import pandas as pd
from typing import Optional
import time
import json


# ---------------------------------------------------------------------------
# SEC EDGAR
# ---------------------------------------------------------------------------

SEC_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": "FinancialAnalystCoPilot/1.0 (copilot@example.com)",
    "Accept-Encoding": "gzip, deflate",
}

# Cache CIK lookups
_cik_cache: dict = {}


def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """Convert a stock ticker to its SEC CIK number."""
    ticker = ticker.upper().strip()
    if ticker in _cik_cache:
        return _cik_cache[ticker]
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for entry in data.values():
            if entry["ticker"].upper() == ticker:
                cik = str(entry["cik_str"]).zfill(10)
                _cik_cache[ticker] = cik
                return cik
    except Exception:
        pass
    return None


def get_company_filings(ticker: str, filing_type: str = "10-K", count: int = 5) -> list:
    """Get recent SEC filings for a company."""
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return []
    try:
        resp = requests.get(
            f"{SEC_BASE_URL}/submissions/CIK{cik}.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        filings = []
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        for i, form in enumerate(forms):
            if form == filing_type and len(filings) < count:
                filings.append({
                    "accession_number": recent["accessionNumber"][i],
                    "filing_date": recent["filingDate"][i],
                    "form": form,
                    "primary_document": recent.get("primaryDocument", [""])[i]
                    if i < len(recent.get("primaryDocument", []))
                    else "",
                    "description": recent.get("primaryDocDescription", [""])[i]
                    if i < len(recent.get("primaryDocDescription", []))
                    else "",
                })
        return filings
    except Exception as e:
        return [{"error": str(e)}]


def get_company_facts(ticker: str) -> dict:
    """Get structured XBRL financial facts from SEC."""
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return {"error": "CIK not found"}
    try:
        resp = requests.get(
            f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def get_company_info_sec(ticker: str) -> dict:
    """Get basic company info from SEC submissions."""
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return {"error": "CIK not found"}
    try:
        resp = requests.get(
            f"{SEC_BASE_URL}/submissions/CIK{cik}.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "name": data.get("name", ""),
            "cik": cik,
            "ticker": ticker.upper(),
            "sic": data.get("sic", ""),
            "sic_description": data.get("sicDescription", ""),
            "fiscal_year_end": data.get("fiscalYearEnd", ""),
            "state": data.get("stateOfIncorporation", ""),
            "exchange": data.get("exchanges", []),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

def get_stock_info(ticker: str) -> dict:
    """Get comprehensive stock info from Yahoo Finance with retry."""
    for attempt in range(3):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info:
                time.sleep(0.5)
                continue
            # yfinance may return a dict with only an "error" key on transient
            # failures.  If meaningful financial keys are present, the data is
            # usable regardless of an extra "error" key.
            meaningful_keys = {"currentPrice", "marketCap", "shortName", "longName", "sector"}
            if meaningful_keys & set(info.keys()):
                info.pop("error", None)  # drop stale error flag if present
                return info
            # Dict came back but has no useful data – retry
            time.sleep(0.5)
        except Exception:
            time.sleep(0.5)
    # All retries exhausted – one final attempt and return whatever we get
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        if info and len(info) > 3:
            info.pop("error", None)
            return info
        return {"error": f"No data returned for {ticker}"}
    except Exception as e:
        return {"error": str(e)}


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Get historical price data."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        return pd.DataFrame()


def get_financials(ticker: str) -> dict:
    """Get income statement, balance sheet, and cash flow."""
    try:
        stock = yf.Ticker(ticker)
        result = {}
        try:
            inc = stock.financials
            result["income_statement"] = inc if inc is not None and not inc.empty else pd.DataFrame()
        except Exception:
            result["income_statement"] = pd.DataFrame()
        try:
            bs = stock.balance_sheet
            result["balance_sheet"] = bs if bs is not None and not bs.empty else pd.DataFrame()
        except Exception:
            result["balance_sheet"] = pd.DataFrame()
        try:
            cf = stock.cashflow
            result["cash_flow"] = cf if cf is not None and not cf.empty else pd.DataFrame()
        except Exception:
            result["cash_flow"] = pd.DataFrame()
        return result
    except Exception as e:
        return {"error": str(e)}


def get_key_metrics(ticker: str) -> dict:
    """Extract key financial metrics from Yahoo Finance info."""
    info = get_stock_info(ticker)
    # Only treat as a hard error if there's *nothing* useful in the response
    if "error" in info and len(info) <= 1:
        return info

    metrics = {}
    keys = [
        "marketCap", "enterpriseValue", "trailingPE", "forwardPE",
        "pegRatio", "priceToBook", "trailingEps", "forwardEps",
        "dividendYield", "payoutRatio", "beta", "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
        "revenueGrowth", "earningsGrowth", "grossMargins",
        "operatingMargins", "profitMargins", "returnOnEquity",
        "returnOnAssets", "debtToEquity", "currentRatio",
        "quickRatio", "freeCashflow", "operatingCashflow",
        "totalRevenue", "totalDebt", "totalCash",
        "shortName", "longName", "sector", "industry",
        "fullTimeEmployees", "website", "currentPrice",
        "targetHighPrice", "targetLowPrice", "targetMeanPrice",
        "recommendationKey", "numberOfAnalystOpinions",
    ]
    for key in keys:
        if key in info:
            metrics[key] = info[key]

    return metrics


def get_analyst_recommendations(ticker: str) -> pd.DataFrame:
    """Get analyst recommendations."""
    try:
        stock = yf.Ticker(ticker)
        recs = stock.recommendations
        return recs if recs is not None and not recs.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_news(ticker: str) -> list:
    """Get recent news for a ticker from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if news:
            return [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": item.get("providerPublishTime", ""),
                    "type": item.get("type", ""),
                }
                for item in news[:10]
            ]
        return []
    except Exception:
        return []


def get_multiple_stock_data(tickers: list) -> dict:
    """Get price and key metrics for multiple tickers at once."""
    result = {}
    for ticker in tickers:
        ticker = ticker.strip().upper()
        info = get_key_metrics(ticker)
        hist = get_price_history(ticker, period="5d")
        price_change = None
        if not hist.empty and len(hist) >= 2:
            price_change = (
                (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
                / hist["Close"].iloc[-2]
                * 100
            )
        result[ticker] = {
            "metrics": info,
            "daily_change_pct": round(price_change, 2) if price_change is not None else None,
        }
    return result


def format_large_number(num) -> str:
    """Format large numbers for display (e.g. 1.5T, 300B, 50M)."""
    if num is None:
        return "N/A"
    try:
        num = float(num)
    except (ValueError, TypeError):
        return str(num)
    if abs(num) >= 1e12:
        return f"${num / 1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"${num / 1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"${num / 1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"${num / 1e3:.1f}K"
    else:
        return f"${num:.2f}"


def format_percentage(val) -> str:
    """Format a decimal or percentage value for display."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) < 1:
            return f"{val * 100:.2f}%"
        return f"{val:.2f}%"
    except (ValueError, TypeError):
        return str(val)
