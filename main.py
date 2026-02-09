"""
Financial Analyst Co-Pilot
AI-powered institutional-grade financial analysis.
Run: streamlit run main.py
"""

import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
import time
from utils.gcp_client import gcp_client

# Load environment variables
load_dotenv()

# ── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Analyst Co-Pilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global styles */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    /* Main header */
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #6B7280;
        margin-top: 0;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card h3 { margin: 0; font-size: 0.85rem; opacity: 0.9; }
    .metric-card h1 { margin: 0.3rem 0; font-size: 1.6rem; }
    .metric-card p { margin: 0; font-size: 0.8rem; opacity: 0.85; }

    /* Agent status */
    .agent-status {
        padding: 8px 12px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 0.85rem;
        background: #F3F4F6;
    }
    .agent-active { border-left: 4px solid #10B981; background: #ECFDF5; }
    .agent-working { border-left: 4px solid #F59E0B; background: #FFFBEB; }
    .agent-pending { border-left: 4px solid #9CA3AF; background: #F9FAFB; }

    /* Stock card */
    .stock-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stock-up { color: #10B981; font-weight: 600; }
    .stock-down { color: #EF4444; font-weight: 600; }

    /* Sidebar customization — light theme for readability */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F0F4FA 0%, #E2E8F0 100%);
        border-right: 1px solid #CBD5E1;
    }
    [data-testid="stSidebar"] * {
        color: #1E293B !important;
    }
    [data-testid="stSidebar"] h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h2 {
        color: #1E3A5F !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #CBD5E1 !important;
    }
    [data-testid="stSidebar"] button {
        color: #1E293B !important;
    }

    /* Info box */
    .info-box {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* Report section */
    .report-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialization ────────────────────────────────────────────
def init_session_state():
    defaults = {
        "messages": [],
        "watchlist": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
        "orchestrator": None,
        "agent_statuses": {},
        "analysis_cache": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ── Lazy-load Orchestrator ──────────────────────────────────────────────────
@st.cache_resource
def get_orchestrator():
    from agents.orchestrator import Orchestrator
    return Orchestrator()


# ── Helper Functions ────────────────────────────────────────────────────────

def update_agent_status(agent: str, status: str):
    """Callback for updating agent status in the UI."""
    st.session_state.agent_statuses[agent] = status


def render_agent_status():
    """Render the agent activity panel."""
    if not st.session_state.agent_statuses:
        return
    st.markdown("#### Agent Activity")
    agent_icons = {
        "orchestrator": "🎯",
        "market": "📈",
        "document": "📄",
        "sentiment": "💬",
        "risk": "⚠️",
        "report": "📝",
    }
    for agent, status in st.session_state.agent_statuses.items():
        icon = agent_icons.get(agent, "🤖")
        css_class = "agent-working"
        st.markdown(
            f'<div class="agent-status {css_class}">{icon} <strong>{agent.title()}</strong>: {status}</div>',
            unsafe_allow_html=True,
        )


def create_price_chart(ticker: str, period: str = "1y"):
    """Create a stock price chart using plotly."""
    from utils.data_providers import get_price_history
    hist = get_price_history(ticker, period)
    if hist.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"],
        high=hist["High"],
        low=hist["Low"],
        close=hist["Close"],
        name=ticker,
    ))
    fig.update_layout(
        title=f"{ticker} Price Chart ({period})",
        yaxis_title="Price ($)",
        xaxis_title="Date",
        template="plotly_white",
        height=400,
        margin=dict(l=50, r=20, t=50, b=40),
        xaxis_rangeslider_visible=False,
    )
    return fig


def create_comparison_chart(tickers: list, metric_name: str, values: list, title: str):
    """Create a bar chart comparing metrics across companies."""
    fig = go.Figure(data=[
        go.Bar(
            x=tickers,
            y=values,
            marker_color=px.colors.qualitative.Set2[:len(tickers)],
            text=[f"{v:.2f}" if isinstance(v, (int, float)) else str(v) for v in values],
            textposition="auto",
        )
    ])
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=350,
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig


# ── Sidebar ─────────────────────────────────────────────────────────────────
PAGE_OPTIONS = [
    "🏠 Dashboard",
    "💬 Chat",
    "🔍 Company Analysis",
    "⚖️ Peer Comparison",
    "📝 Investment Thesis",
    "📄 Document Analysis",
    "⚠️ Risk Assessment",
    "💡 Sentiment Analysis",
]

# Apply any pending navigation BEFORE the radio widget is created
if "_target_page" in st.session_state:
    st.session_state.nav_radio = st.session_state._target_page
    del st.session_state._target_page

with st.sidebar:
    st.markdown("# 📊 Financial Co-Pilot")
    st.markdown("*AI-Powered Analysis*")
    st.markdown("---")

    st.radio("Navigate", PAGE_OPTIONS, key="nav_radio")

    st.markdown("---")
    st.markdown("### Watchlist")
    wl_input = st.text_input(
        "Add ticker",
        placeholder="e.g., TSLA",
        key="wl_add",
        label_visibility="collapsed",
    )
    if wl_input and wl_input.strip().upper() not in st.session_state.watchlist:
        st.session_state.watchlist.append(wl_input.strip().upper())
        st.rerun()

    for i, t in enumerate(st.session_state.watchlist):
        cols = st.columns([3, 1])
        cols[0].markdown(f"**{t}**")
        if cols[1].button("✕", key=f"rm_{t}_{i}"):
            st.session_state.watchlist.remove(t)
            st.rerun()

    st.markdown("---")
    st.markdown("### ☁️ Cloud Infrastructure")
    
    # Status indicators for GCP Services
    services = {
        "Firestore": gcp_client.db is not None,
        "BigQuery": gcp_client.bq is not None,
        "Cloud Storage": gcp_client.storage is not None,
        "Pub/Sub": gcp_client.publisher is not None
    }
    
    for svc, status in services.items():
        color = "#10B981" if status else "#EF4444"
        icon = "●" if status else "○"
        st.markdown(
            f"<div style='font-size: 0.8rem; display: flex; justify-content: space-between;'>"
            f"<span>{svc}</span>"
            f"<span style='color: {color}; font-weight: bold;'>{icon}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown(
        "<p style='color:#64748B;font-size:0.75rem;text-align:center;'>"
        "Powered by Gemini &amp; Google Cloud</p>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
def render_dashboard():
    # Hero Image
    hero_img_path = os.path.join("assets", "hero.png")
    if os.path.exists(hero_img_path):
        st.image(hero_img_path, width='stretch')
    else:
        st.markdown('<p class="main-header">📊 Financial Analyst Co-Pilot</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">AI-powered institutional-grade financial analysis</p>', unsafe_allow_html=True)
    
    st.markdown("---")

    # Quick actions
    st.markdown("### Quick Actions")
    cols = st.columns(4)
    quick_ticker = cols[0].text_input("Ticker", value="AAPL", key="dash_ticker")

    if cols[1].button("📈 Analyze", width="stretch", key="dash_analyze"):
        st.session_state._target_page = "🔍 Company Analysis"
        st.session_state.analysis_ticker = quick_ticker
        st.rerun()

    if cols[2].button("📝 Thesis", width="stretch", key="dash_thesis"):
        st.session_state._target_page = "📝 Investment Thesis"
        st.session_state.thesis_ticker = quick_ticker
        st.rerun()

    if cols[3].button("⚠️ Risk", width="stretch", key="dash_risk"):
        st.session_state._target_page = "⚠️ Risk Assessment"
        st.session_state.risk_ticker = quick_ticker
        st.rerun()

    st.markdown("---")

    # Watchlist overview
    st.markdown("### Watchlist Overview")
    if st.session_state.watchlist:
        with st.spinner("Loading market data..."):
            from utils.data_providers import get_multiple_stock_data, format_large_number
            data = get_multiple_stock_data(st.session_state.watchlist[:8])

        cols = st.columns(min(len(data), 4))
        for i, (ticker, info) in enumerate(data.items()):
            col = cols[i % 4]
            metrics = info.get("metrics", {})
            price = metrics.get("currentPrice", "N/A")
            change = info.get("daily_change_pct")
            name = metrics.get("shortName", ticker)
            mktcap = format_large_number(metrics.get("marketCap"))

            change_str = f"{change:+.2f}%" if change is not None else "N/A"
            change_class = "stock-up" if change and change >= 0 else "stock-down"

            col.markdown(f"""
<div class="stock-card">
    <strong>{ticker}</strong><br>
    <span style="font-size:0.8rem;color:#6B7280;">{name}</span><br>
    <span style="font-size:1.3rem;font-weight:600;">${price}</span><br>
    <span class="{change_class}">{change_str}</span>
    <span style="font-size:0.75rem;color:#9CA3AF;"> | {mktcap}</span>
</div>
""", unsafe_allow_html=True)

        # Price charts for first 2 watchlist items
        st.markdown("---")
        st.markdown("### Price Charts")
        chart_cols = st.columns(2)
        for i, ticker in enumerate(st.session_state.watchlist[:2]):
            fig = create_price_chart(ticker, "6mo")
            if fig:
                chart_cols[i].plotly_chart(fig, width="stretch")

    # Cloud Connectivity Check (For local testing)
    st.markdown("---")
    with st.expander("🛠️ System Connectivity Check (GCP)"):
        st.info("Ensure you have run `gcloud auth application-default login` for local testing.")
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("🔥 Test Firestore"):
            import uuid
            session_id = str(uuid.uuid4())[:8]
            gcp_client.save_chat_message(session_id, "system", "Connectivity check")
            st.success(f"Test message sent to Firestore (DB: finsightcopilot)!")
            
        if col2.button("📊 Test BigQuery"):
            gcp_client.log_activity("TEST", "Diagnostic", "SUCCESS")
            st.success("Log entry sent to BigQuery (Dataset: financial_copilot)!")
            
        if col3.button("📦 Test Storage"):
            # Create a simple test file
            content = b"Connection Test"
            import io
            test_file = io.BytesIO(content)
            url = gcp_client.upload_document(test_file, "system/connection_test.txt")
            if url:
                st.success(f"File uploaded to GCS bucket!")
            else:
                st.error("Upload failed (Check if bucket exists)")
            
        if col4.button("📢 Test Pub/Sub"):
            gcp_client.publish_analysis_complete("TEST", "diagnostic", "Diagnostic summary")
            st.success("Analysis notification sent to analyst-events topic!")

    # Sample queries section
    st.markdown("---")
    st.markdown("### Try These Queries")
    sample_queries = [
        "Compare NVIDIA and AMD valuations - is NVDA overvalued?",
        "Generate an investment thesis for Microsoft",
        "What are the main risk factors for Tesla?",
        "Analyze Apple's latest financial performance",
        "Compare the gross margins of AAPL, MSFT, GOOGL",
    ]
    for q in sample_queries:
        if st.button(f"💡 {q}", key=f"sample_{q[:30]}", width="stretch"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.session_state._target_page = "💬 Chat"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: CHAT
# ═══════════════════════════════════════════════════════════════════════════
def render_chat():
    st.markdown('<p class="main-header">💬 Financial Analysis Chat</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask anything about companies, markets, filings, or investments</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new chat input
    prompt = st.chat_input("Ask about any company, filing, or financial topic...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Note: No rerun needed here, we'll process it below
    
    # Process the latest message if it's from user
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_query = st.session_state.messages[-1]["content"]
        
        with st.chat_message("assistant"):
            st.session_state.agent_statuses = {}
            status_container = st.empty()

            with st.spinner("Agents analyzing your query..."):
                orchestrator = get_orchestrator()
                # Use st.session_state.messages[-1]["content"] to be safe
                response = orchestrator.process_query(user_query, status_callback=update_agent_status)

            status_container.empty()
            st.markdown(response)

        # Save to Firestore and Session State
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.agent_statuses = {}
        
        # Persist to GCP
        import uuid
        if "chat_session_id" not in st.session_state:
            st.session_state.chat_session_id = str(uuid.uuid4())
        
        gcp_client.save_chat_message(st.session_state.chat_session_id, "user", user_query)
        gcp_client.save_chat_message(st.session_state.chat_session_id, "assistant", response)
        
        # Log to BigQuery
        gcp_client.log_activity("CHAT", "Orchestrator", "COMPLETED")
        st.rerun()

    # Suggested queries if no history
    if not st.session_state.messages:
        st.markdown("### Suggested Queries")
        suggestions = [
            ("📈 Market Analysis", "Analyze NVDA's current valuation and growth prospects"),
            ("📄 Filing Analysis", "What are the key takeaways from Apple's latest 10-K filing?"),
            ("⚖️ Comparison", "Compare MSFT, GOOGL, and AMZN on profitability and growth"),
            ("📝 Thesis", "Generate an investment thesis for Tesla with bull and bear cases"),
            ("⚠️ Risk", "What are the main risk factors for investing in Meta?"),
            ("💬 Sentiment", "What's the current market sentiment for AAPL?"),
        ]
        cols = st.columns(2)
        for i, (label, query) in enumerate(suggestions):
            col = cols[i % 2]
            if col.button(f"{label}: {query[:50]}...", key=f"sug_{i}", width="stretch"):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: COMPANY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_company_analysis():
    st.markdown('<p class="main-header">🔍 Company Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Deep-dive financial analysis for any public company</p>', unsafe_allow_html=True)
    st.markdown("---")

    default_ticker = st.session_state.get("analysis_ticker", "AAPL")
    col1, col2, col3 = st.columns([2, 1, 1])
    ticker = col1.text_input("Enter Ticker Symbol", value=default_ticker, key="company_ticker")
    period = col2.selectbox("Chart Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    analyze_btn = col3.button("🔍 Analyze", width="stretch", key="analyze_company_btn")

    # Fetch data on button click and persist in session state
    if analyze_btn and ticker:
        _ticker = ticker.strip().upper()
        with st.spinner(f"Analyzing {_ticker}..."):
            from utils.data_providers import get_key_metrics
            metrics = get_key_metrics(_ticker)
        if "error" in metrics:
            st.error(f"Could not fetch data for {_ticker}. Please check the ticker symbol.")
            st.session_state.pop("ca_metrics", None)
            st.session_state.pop("ca_ticker", None)
            return
        st.session_state["ca_metrics"] = metrics
        st.session_state["ca_ticker"] = _ticker
        st.session_state.pop("ca_ai_result", None)  # clear stale AI result

    # Show persisted analysis if available
    if "ca_metrics" not in st.session_state:
        st.info("Enter a ticker symbol above and click **Analyze** to start.")
        return

    metrics = st.session_state["ca_metrics"]
    active_ticker = st.session_state["ca_ticker"]
    from utils.data_providers import format_large_number, format_percentage

    company_name = metrics.get("longName") or metrics.get("shortName", active_ticker)

    # Company header
    st.markdown(f"## {company_name} ({active_ticker})")
    emp = metrics.get("fullTimeEmployees")
    emp_str = f"{emp:,}" if isinstance(emp, (int, float)) else "N/A"
    st.markdown(f"**{metrics.get('sector', '')}** | {metrics.get('industry', '')} | Employees: {emp_str}")

    # Key metrics cards
    st.markdown("### Key Metrics")
    m_cols = st.columns(5)
    metric_items = [
        ("Price", f"${metrics.get('currentPrice', 'N/A')}", f"Target: ${metrics.get('targetMeanPrice', 'N/A')}"),
        ("Market Cap", format_large_number(metrics.get("marketCap")), f"P/E: {metrics.get('trailingPE', 'N/A')}"),
        ("Revenue", format_large_number(metrics.get("totalRevenue")), f"Growth: {format_percentage(metrics.get('revenueGrowth'))}"),
        ("Margins", format_percentage(metrics.get("grossMargins")), f"Net: {format_percentage(metrics.get('profitMargins'))}"),
        ("FCF", format_large_number(metrics.get("freeCashflow")), f"D/E: {metrics.get('debtToEquity', 'N/A')}"),
    ]
    for i, (label, value, subtitle) in enumerate(metric_items):
        m_cols[i].markdown(f"""
<div class="metric-card">
    <h3>{label}</h3>
    <h1>{value}</h1>
    <p>{subtitle}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("")

    # Charts section
    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        fig = create_price_chart(active_ticker, period)
        if fig:
            st.plotly_chart(fig, width="stretch")

    with col_info:
        st.markdown("### Valuation & Returns")
        val_data = {
            "Metric": ["P/E (TTM)", "Forward P/E", "PEG Ratio", "P/B Ratio", "EV/Revenue", "Dividend Yield"],
            "Value": [
                str(metrics.get("trailingPE", "N/A")),
                str(metrics.get("forwardPE", "N/A")),
                str(metrics.get("pegRatio", "N/A")),
                str(metrics.get("priceToBook", "N/A")),
                str(round(metrics.get("enterpriseValue", 0) / metrics.get("totalRevenue", 1), 2))
                if metrics.get("enterpriseValue") and metrics.get("totalRevenue") else "N/A",
                format_percentage(metrics.get("dividendYield")),
            ],
        }
        st.dataframe(pd.DataFrame(val_data).astype(str), width="stretch", hide_index=True)

        st.markdown("### Returns & Efficiency")
        ret_data = {
            "Metric": ["ROE", "ROA", "Gross Margin", "Op Margin", "Net Margin", "Beta"],
            "Value": [
                format_percentage(metrics.get("returnOnEquity")),
                format_percentage(metrics.get("returnOnAssets")),
                format_percentage(metrics.get("grossMargins")),
                format_percentage(metrics.get("operatingMargins")),
                format_percentage(metrics.get("profitMargins")),
                str(metrics.get("beta", "N/A")),
            ],
        }
        st.dataframe(pd.DataFrame(ret_data).astype(str), width="stretch", hide_index=True)

    # AI Analysis
    st.markdown("---")
    st.markdown("### AI Analysis")
    custom_query = st.text_input(
        "Ask a specific question (optional)",
        placeholder=f"e.g., Is {active_ticker} overvalued compared to its peers?",
        key="company_custom_query",
    )

    if st.button("🤖 Generate AI Analysis", key="gen_ai_analysis", width="stretch"):
        with st.spinner("Generating AI analysis..."):
            orchestrator = get_orchestrator()
            query = custom_query if custom_query else None
            result = orchestrator.market_agent.analyze_with_ai(active_ticker, query)
        st.session_state["ca_ai_result"] = result

    if "ca_ai_result" in st.session_state:
        st.markdown(st.session_state["ca_ai_result"])

    # SEC Filings section
    st.markdown("---")
    st.markdown("### Recent SEC Filings")
    with st.spinner("Fetching SEC filings..."):
        from utils.data_providers import get_company_filings
        filings_10k = get_company_filings(active_ticker, "10-K", 3)
        filings_10q = get_company_filings(active_ticker, "10-Q", 3)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.markdown("**10-K Annual Reports**")
        for f in filings_10k:
            if "error" not in f:
                st.markdown(f"- 📄 Filed: {f.get('filing_date', 'N/A')} | {f.get('description', 'Annual Report')}")
    with f_col2:
        st.markdown("**10-Q Quarterly Reports**")
        for f in filings_10q:
            if "error" not in f:
                st.markdown(f"- 📄 Filed: {f.get('filing_date', 'N/A')} | {f.get('description', 'Quarterly Report')}")


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: PEER COMPARISON
# ═══════════════════════════════════════════════════════════════════════════
def render_peer_comparison():
    st.markdown('<p class="main-header">⚖️ Peer Comparison</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Compare multiple companies side by side</p>', unsafe_allow_html=True)
    st.markdown("---")

    tickers_input = st.text_input(
        "Enter tickers (comma-separated)",
        value="AAPL, MSFT, GOOGL",
        key="peer_tickers",
    )
    custom_question = st.text_input(
        "Specific comparison question (optional)",
        placeholder="e.g., Which company has the best growth-to-valuation ratio?",
        key="peer_question",
    )

    if st.button("⚖️ Compare Companies", key="compare_btn", width="stretch"):
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        if len(tickers) < 2:
            st.warning("Please enter at least 2 tickers to compare.")
            return

        with st.spinner(f"Comparing {', '.join(tickers)}..."):
            from utils.data_providers import get_key_metrics, format_large_number, format_percentage

            all_metrics = {}
            for t in tickers:
                all_metrics[t] = get_key_metrics(t)

        # Comparison table
        st.markdown("### Side-by-Side Comparison")

        table_rows = [
            ("Price", "currentPrice", "$"),
            ("Market Cap", "marketCap", "cap"),
            ("P/E (TTM)", "trailingPE", ""),
            ("Forward P/E", "forwardPE", ""),
            ("PEG Ratio", "pegRatio", ""),
            ("Revenue", "totalRevenue", "cap"),
            ("Rev Growth", "revenueGrowth", "%"),
            ("Gross Margin", "grossMargins", "%"),
            ("Op Margin", "operatingMargins", "%"),
            ("Net Margin", "profitMargins", "%"),
            ("ROE", "returnOnEquity", "%"),
            ("Debt/Equity", "debtToEquity", ""),
            ("FCF", "freeCashflow", "cap"),
            ("Beta", "beta", ""),
            ("Analyst", "recommendationKey", ""),
            ("Target Price", "targetMeanPrice", "$"),
        ]

        comp_data = {"Metric": [r[0] for r in table_rows]}
        for t in tickers:
            m = all_metrics.get(t, {})
            vals = []
            for _, key, fmt in table_rows:
                v = m.get(key)
                if v is None:
                    vals.append("N/A")
                elif fmt == "$":
                    vals.append(f"${v:,.2f}" if isinstance(v, (int, float)) else str(v))
                elif fmt == "%":
                    vals.append(format_percentage(v))
                elif fmt == "cap":
                    vals.append(format_large_number(v))
                else:
                    vals.append(f"{v:,.2f}" if isinstance(v, float) else str(v))
            comp_data[t] = vals

        st.dataframe(pd.DataFrame(comp_data).astype(str), width="stretch", hide_index=True)

        # Comparison charts
        st.markdown("### Visual Comparisons")
        chart_configs = [
            ("P/E Ratio", "trailingPE", "P/E Ratio Comparison"),
            ("Gross Margin", "grossMargins", "Gross Margin Comparison (%)"),
            ("Revenue Growth", "revenueGrowth", "Revenue Growth Comparison (%)"),
            ("ROE", "returnOnEquity", "Return on Equity Comparison (%)"),
        ]

        chart_cols = st.columns(2)
        for i, (label, key, title) in enumerate(chart_configs):
            values = []
            valid_tickers = []
            for t in tickers:
                v = all_metrics.get(t, {}).get(key)
                if v is not None:
                    if key in ("grossMargins", "revenueGrowth", "returnOnEquity", "operatingMargins", "profitMargins"):
                        v = v * 100 if abs(v) < 1 else v
                    values.append(v)
                    valid_tickers.append(t)
            if values:
                fig = create_comparison_chart(valid_tickers, label, values, title)
                chart_cols[i % 2].plotly_chart(fig, width="stretch")

        # AI Comparison
        st.markdown("---")
        st.markdown("### AI-Powered Comparison")
        with st.spinner("Generating AI comparison..."):
            orchestrator = get_orchestrator()
            if custom_question:
                ai_result = orchestrator.market_agent.compare_with_ai(tickers, custom_question)
            else:
                ai_result = orchestrator.report_agent.generate_comparison_report(tickers)
        st.markdown(ai_result)


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: INVESTMENT THESIS
# ═══════════════════════════════════════════════════════════════════════════
def render_investment_thesis():
    st.markdown('<p class="main-header">📝 Investment Thesis Generator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate comprehensive investment analysis with bull/bear cases</p>', unsafe_allow_html=True)
    st.markdown("---")

    default_ticker = st.session_state.get("thesis_ticker", "MSFT")
    col1, col2 = st.columns([3, 1])
    ticker = col1.text_input("Enter Ticker Symbol", value=default_ticker, key="thesis_input_ticker")
    generate_btn = col2.button("📝 Generate Thesis", width="stretch", key="gen_thesis_btn")

    if generate_btn and ticker:
        ticker = ticker.strip().upper()

        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()

        stages = [
            (10, "Fetching company data..."),
            (25, "Analyzing financial metrics..."),
            (40, "Reviewing SEC filings..."),
            (55, "Analyzing market sentiment..."),
            (70, "Assessing risk factors..."),
            (85, "Generating investment thesis..."),
            (95, "Finalizing report..."),
        ]

        # Show progress
        for pct, msg in stages[:2]:
            progress_bar.progress(pct)
            status_text.markdown(f"**{msg}**")
            time.sleep(0.3)

        with st.spinner("Generating comprehensive investment thesis..."):
            orchestrator = get_orchestrator()

            # Update progress as we work
            for pct, msg in stages[2:]:
                progress_bar.progress(pct)
                status_text.markdown(f"**{msg}**")
                time.sleep(0.2)

            thesis = orchestrator.report_agent.generate_investment_thesis(ticker)

        progress_bar.progress(100)
        status_text.markdown("**Complete!**")
        time.sleep(0.3)
        progress_bar.empty()
        status_text.empty()

        # Display the thesis
        st.markdown("---")
        st.markdown(thesis)

        # Download button
        st.markdown("---")
        st.download_button(
            label="📥 Download Report as Text",
            data=thesis,
            file_name=f"{ticker}_investment_thesis.md",
            mime="text/markdown",
        )


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: DOCUMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_document_analysis():
    st.markdown('<p class="main-header">📄 Document Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload and analyze SEC filings, earnings reports, and financial documents</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab1, tab2 = st.tabs(["📤 Upload Document", "🔎 Analyze SEC Filing"])

    with tab1:
        uploaded_file = st.file_uploader(
            "Upload a financial document (PDF)",
            type=["pdf"],
            key="doc_upload",
        )

        if uploaded_file:
            st.success(f"Uploaded: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

            query = st.text_area(
                "What would you like to know about this document?",
                value="Provide a comprehensive analysis including key financial metrics, risk factors, management discussion highlights, and notable changes.",
                key="doc_query",
                height=100,
            )

            if st.button("🔍 Analyze Document", key="analyze_doc_btn", width="stretch"):
                with st.spinner("Analyzing document with Gemini... This may take a moment."):
                    orchestrator = get_orchestrator()
                    file_bytes = uploaded_file.read()
                    
                    # Upload to GCS first
                    import io
                    gcs_file = io.BytesIO(file_bytes)
                    gcs_url = gcp_client.upload_document(gcs_file, f"uploads/{uploaded_file.name}")
                    if gcs_url:
                        st.info(f"📄 Document archived in GCS: {uploaded_file.name}")
                    
                    result = orchestrator.document_agent.analyze_uploaded_document(
                        file_bytes, uploaded_file.name, query
                    )
                st.markdown("### Analysis Results")
                st.markdown(result)

    with tab2:
        col1, col2, col3 = st.columns([2, 1, 1])
        sec_ticker = col1.text_input("Ticker Symbol", value="AAPL", key="sec_ticker")
        filing_type = col2.selectbox("Filing Type", ["10-K", "10-Q", "8-K"], key="sec_filing_type")
        sec_query = st.text_input(
            "Analysis question (optional)",
            placeholder="e.g., What are the main risk factors?",
            key="sec_query",
        )

        if st.button("📄 Analyze Filing", key="analyze_filing_btn", width="stretch"):
            sec_ticker = sec_ticker.strip().upper()

            with st.spinner(f"Fetching and analyzing {sec_ticker} {filing_type}..."):
                orchestrator = get_orchestrator()

                # Show filing list
                filings = orchestrator.document_agent.get_filings_list(sec_ticker, filing_type, 5)
                if filings:
                    st.markdown(f"### Recent {filing_type} Filings for {sec_ticker}")
                    for f in filings:
                        if "error" not in f:
                            st.markdown(
                                f"- 📄 {f.get('filing_date', 'N/A')} | "
                                f"{f.get('description', filing_type)} | "
                                f"Accession: {f.get('accession_number', 'N/A')}"
                            )

                # AI Analysis
                query = sec_query if sec_query else None
                analysis = orchestrator.document_agent.analyze_filing_with_ai(sec_ticker, query)

            st.markdown("### AI Analysis")
            st.markdown(analysis)


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: RISK ASSESSMENT
# ═══════════════════════════════════════════════════════════════════════════
def render_risk_assessment():
    st.markdown('<p class="main-header">⚠️ Risk Assessment</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Identify and assess risk factors with AI-powered analysis</p>', unsafe_allow_html=True)
    st.markdown("---")

    default_ticker = st.session_state.get("risk_ticker", "TSLA")
    tab1, tab2 = st.tabs(["📊 Single Company", "⚖️ Compare Risks"])

    with tab1:
        ticker = st.text_input("Enter Ticker Symbol", value=default_ticker, key="risk_ticker_input")

        if st.button("⚠️ Assess Risks", key="assess_risk_btn", width="stretch"):
            ticker = ticker.strip().upper()

            with st.spinner(f"Assessing risks for {ticker}..."):
                orchestrator = get_orchestrator()
                risk_data = orchestrator.risk_agent.assess_financial_risk(ticker)

            if "error" in risk_data:
                st.error(risk_data["error"])
                return

            # Risk scorecard visualization
            st.markdown(f"### Risk Scorecard: {risk_data.get('company', ticker)}")

            risk_items = {k: v for k, v in risk_data.items() if isinstance(v, dict) and "level" in v}
            if risk_items:
                risk_cols = st.columns(len(risk_items))
                colors = {"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#10B981"}
                for i, (key, val) in enumerate(risk_items.items()):
                    level = val["level"]
                    color = colors.get(level, "#6B7280")
                    risk_cols[i].markdown(f"""
<div style="text-align:center;padding:1rem;border-radius:10px;border:2px solid {color};background:{color}10;">
    <p style="margin:0;font-size:0.8rem;color:#6B7280;">{key.replace('_', ' ').title()}</p>
    <p style="margin:0.3rem 0;font-size:1.3rem;font-weight:700;color:{color};">{level}</p>
    <p style="margin:0;font-size:0.75rem;color:#9CA3AF;">{val['note']}</p>
</div>
""", unsafe_allow_html=True)

            # Comprehensive AI Risk Analysis
            st.markdown("---")
            st.markdown("### Comprehensive Risk Analysis")
            with st.spinner("Generating AI risk analysis..."):
                ai_analysis = orchestrator.risk_agent.comprehensive_risk_analysis(ticker)
            st.markdown(ai_analysis)

    with tab2:
        tickers_input = st.text_input(
            "Enter tickers to compare (comma-separated)",
            value="AAPL, MSFT, GOOGL",
            key="risk_compare_tickers",
        )
        if st.button("⚖️ Compare Risks", key="compare_risks_btn", width="stretch"):
            tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
            if len(tickers) < 2:
                st.warning("Enter at least 2 tickers.")
                return

            with st.spinner(f"Comparing risks: {', '.join(tickers)}..."):
                orchestrator = get_orchestrator()
                comparison = orchestrator.risk_agent.compare_risks(tickers)
            st.markdown(comparison)


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE: SENTIMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_sentiment_analysis():
    st.markdown('<p class="main-header">💡 Sentiment Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Analyze news and market sentiment for any company</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab1, tab2 = st.tabs(["📰 Company Sentiment", "📝 Custom Text Analysis"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        ticker = col1.text_input("Enter Ticker Symbol", value="NVDA", key="sentiment_ticker")
        analyze_btn = col2.button("💡 Analyze Sentiment", width="stretch", key="analyze_sentiment_btn")

        if analyze_btn and ticker:
            ticker = ticker.strip().upper()

            # Show recent news
            with st.spinner(f"Fetching news and analyzing sentiment for {ticker}..."):
                from utils.data_providers import get_news
                news = get_news(ticker)

                orchestrator = get_orchestrator()
                sentiment = orchestrator.sentiment_agent.analyze_sentiment(ticker)

            if news:
                st.markdown("### Recent News")
                for item in news[:6]:
                    title = item.get("title", "")
                    publisher = item.get("publisher", "")
                    link = item.get("link", "")
                    if title:
                        st.markdown(f"- **[{publisher}]** {title}")

            st.markdown("---")
            st.markdown("### AI Sentiment Analysis")
            st.markdown(sentiment)

    with tab2:
        st.markdown("Paste an earnings call transcript, press release, or any financial text for sentiment analysis.")
        text_input = st.text_area(
            "Enter text to analyze",
            height=200,
            key="custom_text_sentiment",
            placeholder="Paste earnings call transcript, press release, or financial news here...",
        )
        context = st.text_input(
            "Context (optional)",
            placeholder="e.g., AAPL Q4 2024 Earnings Call",
            key="sentiment_context",
        )

        if st.button("🔍 Analyze Text Sentiment", key="analyze_text_btn", width="stretch"):
            if text_input:
                with st.spinner("Analyzing text sentiment..."):
                    orchestrator = get_orchestrator()
                    result = orchestrator.sentiment_agent.analyze_custom_text(text_input, context)
                st.markdown("### Sentiment Analysis Results")
                st.markdown(result)
            else:
                st.warning("Please enter some text to analyze.")


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE ROUTING
# ═══════════════════════════════════════════════════════════════════════════
current_page = st.session_state.get("nav_radio", "🏠 Dashboard")

if current_page == "🏠 Dashboard":
    render_dashboard()
elif current_page == "💬 Chat":
    render_chat()
elif current_page == "🔍 Company Analysis":
    render_company_analysis()
elif current_page == "⚖️ Peer Comparison":
    render_peer_comparison()
elif current_page == "📝 Investment Thesis":
    render_investment_thesis()
elif current_page == "📄 Document Analysis":
    render_document_analysis()
elif current_page == "⚠️ Risk Assessment":
    render_risk_assessment()
elif current_page == "💡 Sentiment Analysis":
    render_sentiment_analysis()
else:
    render_dashboard()
