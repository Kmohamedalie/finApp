import streamlit as st
import streamlit.components.v1 as components
import yaml
import tempfile
import pandas as pd
from pathlib import Path
from datetime import datetime

# Import your existing engine modules
from src.config import Config
from src.loader import load_prices
from src.cleaner import clean_and_normalize
from src.attribution import compute_attribution
from src.kpis import compute_kpis
from src.viz import generate_all_figures
from src.report import generate_reports
from src.messages import RunMessages

st.set_page_config(page_title="Financial Reporting Engine", layout="wide")

st.title("📈 Financial Data Automation & Reporting")
st.markdown("Generate comprehensive financial reports, KPIs, and visualizations interactively.")


# --- CACHING WRAPPER ---
@st.cache_data(show_spinner="Fetching market data...")
def fetch_cached_data(data_dict: dict, cleaning_dict: dict):
    """
    Wraps the load_prices function to cache downloaded data. 
    We reconstruct a temporary Config object just for loading so we don't 
    trigger cache misses when the temp_dir paths change.
    """
    temp_cfg = Config(
        path=Path("dummy.yaml"), 
        data={"data": data_dict, "cleaning": cleaning_dict}
    )
    return load_prices(temp_cfg)


# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("1. Data Configuration")
tickers_input = st.sidebar.text_input("Tickers (comma separated)", "AAPL, MSFT, GOOG")
start_date = st.sidebar.date_input("Start Date", value=datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime.today())
base_currency = st.sidebar.text_input("Base Currency", "USD")

st.sidebar.header("2. KPI Parameters")
ann_factor = st.sidebar.number_input("Annualization Factor", min_value=1, value=252)
risk_free_rate = st.sidebar.number_input("Risk-Free Rate (Annual)", min_value=0.0, value=0.02, step=0.01)

st.sidebar.header("3. Reporting Options")
report_title = st.sidebar.text_input("Report Title", "Interactive Financial Report")
include_rolling = st.sidebar.checkbox("Include Rolling Metrics", value=True)
include_drawdowns = st.sidebar.checkbox("Include Drawdowns", value=True)

# --- NEW: PREDICTIVE ANALYTICS SIDEBAR ---
st.sidebar.header("4. Predictive Analytics")
enable_forecast = st.sidebar.checkbox("Enable Price Forecast", value=False, help="Uses Prophet to forecast future prices.")
forecast_days = st.sidebar.slider("Forecast Horizon (Days)", min_value=7, max_value=90, value=30)

# --- CREDITS SECTION ---
st.sidebar.markdown("---")
st.sidebar.header("👨‍💻 About the Developers")
st.sidebar.markdown("""
**Core Engine & Financial Logic:** Created by [Mikel Lopez](https://www.linkedin.com/in/mikellopezfinance/) as part of his Bachelor's thesis work.

**Interactive Web Application:** Built by [Mohamed Alie Kamara](https://www.linkedin.com/in/mohamed-alie-kamara-8765941a4/) to bring this tool to non-technical users.
""")


# --- INITIALIZE SESSION STATE ---
if "report_generated" not in st.session_state:
    st.session_state.report_generated = False
if "forecasts" not in st.session_state:
    st.session_state.forecasts = None


# --- MAIN EXECUTION BLOCK ---
if st.button("🚀 Generate Report", type="primary"):
    temp_dir = Path(tempfile.mkdtemp())
    run_dir = temp_dir / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    input_tickers = [t.strip() for t in tickers_input.split(",")]
    
    # Build the configuration dictionary dynamically from UI inputs
    config_dict = {
        "data": {
            "source_type": "yfinance",
            "tickers": input_tickers,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "base_currency": base_currency,
            "fx": {"enabled": False} 
        },
        "cleaning": {
            "na_strategy": "ffill_then_bfill",
            "return_type": "log",
            "align_method": "outer",  # <--- FIXED: Changed from 'inner' to 'outer' to prevent 0-row errors
            "min_rows": 30
        },
        "kpis": {
            "annualization_factor": ann_factor,
            "risk_free_rate": risk_free_rate,
            "rolling_windows": [21, 63, 126, 252]
        },
        "report": {
            "title": report_title,
            "output_dir": str(run_dir),
            "output_pdf": str(run_dir / "report.pdf"),
            "output_html": str(run_dir / "report.html"),
            "include_rolling": include_rolling,
            "include_drawdowns": include_drawdowns,
            "include_histograms": True,
            "include_boxplots": True
        },
        "visuals": {
            "figure_format": "png",
            "dpi": 150
        }
    }
    
    cfg_path = temp_dir / "config.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(config_dict, f)

    try:
        with st.spinner("Processing data and generating reports..."):
            cfg = Config.from_file(cfg_path)
            msgs = RunMessages()

            # 1) Load (Using our cached wrapper)
            loaded = fetch_cached_data(config_dict["data"], config_dict["cleaning"])
            
            # Catch bad tickers before they crash the pipeline
            if loaded.prices.empty:
                st.error("No data could be downloaded for the provided tickers. Please check your spelling or date range.")
                st.stop()
                
            missing_tickers = [t for t in input_tickers if t not in loaded.prices.columns]
            if missing_tickers:
                st.warning(f"⚠️ Could not fetch data for: {', '.join(missing_tickers)}. They will be excluded from the report.")
            
            # 2) Clean + Returns + Attribution
            cleaned = clean_and_normalize(loaded.prices, cfg)
            attrib = compute_attribution(cleaned.returns, loaded.weights) if loaded.weights is not None else None
            
            # ---> NEW: FORECASTING LOGIC <---
            st.session_state.forecasts = None
            if enable_forecast:
                from prophet import Prophet
                forecasts_dict = {}
                
                # Iterate through each valid ticker in the cleaned prices
                for ticker in cleaned.prices.columns:
                    df_p = cleaned.prices[[ticker]].reset_index()
                    df_p.columns = ['ds', 'y']
                    
                    # Prophet requires timezone-naive datetimes
                    if df_p['ds'].dt.tz is not None:
                        df_p['ds'] = df_p['ds'].dt.tz_localize(None)
                    
                    # Fit model
                    m = Prophet(daily_seasonality=False, yearly_seasonality=True)
                    m.fit(df_p)
                    
                    # Predict future prices
                    future = m.make_future_dataframe(periods=forecast_days)
                    fcst = m.predict(future)
                    
                    # Save the relevant columns for the forecast horizon
                    forecasts_dict[ticker] = fcst[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_days)
                
                st.session_state.forecasts = forecasts_dict
            # ---> END FORECASTING LOGIC <---

            # 3) KPIs
            kpi = compute_kpis(cleaned.returns, cfg)
            
            # 4) Visuals
            figs = generate_all_figures(cleaned.prices, cleaned.returns, kpi, cfg)
            
            # 5) Reports
            outputs = generate_reports(cleaned.prices, cleaned.returns, kpi, figs, attrib, cfg, msgs=msgs)

            # Store results in session state to survive Streamlit reruns
            st.session_state.kpi_summary = kpi.summary
            st.session_state.warnings = msgs.warnings
            st.session_state.fig_prices = str(figs.prices) if figs.prices else None
            st.session_state.fig_drawdowns = str(figs.drawdowns) if figs.drawdowns else None
            st.session_state.fig_boxplot = str(figs.boxplot) if figs.boxplot else None
            
            with open(outputs.pdf, "rb") as f:
                st.session_state.pdf_bytes = f.read()
            with open(outputs.html, "rb") as f:
                st.session_state.html_bytes = f.read()

            st.session_state.report_generated = True

    except Exception as e:
        st.error(f"Pipeline Error: {e}")


# --- DISPLAY RESULTS IN APP ---
if st.session_state.report_generated:
    st.success("Report generated successfully!")

    # Dynamically define tab names based on whether a forecast was run
    tab_names = ["📊 KPIs & Analysis", "📈 Visualizations"]
    has_forecast = st.session_state.get("forecasts") is not None
    
    if has_forecast:
        tab_names.append("🔮 Predictions")
        
    tab_names.extend(["📄 View Report", "📥 Downloads"])

    # Create the dynamic tabs
    tabs = st.tabs(tab_names)

    # --- TAB 1: KPIs & Analysis ---
    with tabs[0]:
        st.subheader("Key Performance Indicators")
        st.dataframe(st.session_state.kpi_summary, use_container_width=True)

        if st.session_state.warnings:
            st.markdown("### ⚠️ Data Quality Notes")
            for warn in st.session_state.warnings:
                st.warning(warn)

    # --- TAB 2: Visualizations ---
    with tabs[1]:
        st.subheader("Market Visualizations")
        
        # Prices and Drawdowns side-by-side
        col1, col2 = st.columns(2)
        if st.session_state.fig_prices:
            col1.image(st.session_state.fig_prices, caption="Prices", use_container_width=True)
            
        if st.session_state.fig_drawdowns and include_drawdowns:
            col2.image(st.session_state.fig_drawdowns, caption="Drawdowns", use_container_width=True)
            
        # Boxplot spans the full width below
        if st.session_state.fig_boxplot:
            st.markdown("---")
            st.image(st.session_state.fig_boxplot, caption="Return Distributions (Boxplot)", use_container_width=True)

    # --- TAB 3 (OPTIONAL): Predictions ---
    current_tab_idx = 2
    if has_forecast:
        with tabs[current_tab_idx]:
            st.subheader(f"Price Forecast ({forecast_days} Days)")
            st.markdown("Powered by Facebook Prophet. **Note:** Predictions are based on historical trends and seasonality, not guarantees of future performance.")
            
            for ticker, forecast_df in st.session_state.forecasts.items():
                st.markdown(f"### {ticker}")
                
                # Format for Streamlit Line Chart
                plot_df = forecast_df.set_index('ds')
                plot_df.columns = ['Predicted Price', 'Lower Bound', 'Upper Bound']
                
                st.line_chart(plot_df)
                
                # Optional: Show the raw numbers inside an expander
                with st.expander(f"View Raw Forecast Data for {ticker}"):
                    st.dataframe(plot_df, use_container_width=True)
                    
        current_tab_idx += 1

    # --- NEXT TAB: View HTML Report ---
    with tabs[current_tab_idx]:
        st.subheader("Interactive Report Preview")
        st.info("Scroll through the full generated HTML report below.")
        
        # Decode the bytes to a standard string and render the HTML
        html_string = st.session_state.html_bytes.decode("utf-8")
        components.html(html_string, height=800, scrolling=True)

    # --- FINAL TAB: Downloads ---
    with tabs[current_tab_idx + 1]:
        st.subheader("Download Generated Reports")
        st.markdown("Grab the fully formatted PDF or interactive HTML reports below.")
        
        dl_col1, dl_col2 = st.columns(2)
        
        dl_col1.download_button(
            label="📄 Download PDF Report", 
            data=st.session_state.pdf_bytes, 
            file_name="Financial_Report.pdf", 
            mime="application/pdf",
            use_container_width=True
        )
        
        dl_col2.download_button(
            label="🌐 Download HTML Report", 
            data=st.session_state.html_bytes, 
            file_name="Financial_Report.html", 
            mime="text/html",
            use_container_width=True
        )
