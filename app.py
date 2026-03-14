import streamlit as st
import yaml
import tempfile
import shutil
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

# --- MAIN EXECUTION BLOCK ---
if st.button("🚀 Generate Report", type="primary"):
    # Create a temporary directory for this run's outputs and config
    temp_dir = Path(tempfile.mkdtemp())
    run_dir = temp_dir / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Build the configuration dictionary dynamically from UI inputs
    config_dict = {
        "data": {
            "source_type": "yfinance",
            "tickers": [t.strip() for t in tickers_input.split(",")],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "base_currency": base_currency,
            "fx": {"enabled": False} 
        },
        "cleaning": {
            "na_strategy": "ffill_then_bfill",
            "return_type": "log",
            "align_method": "inner",
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
    
    # Save to a temporary YAML file so your Config class can load it
    cfg_path = temp_dir / "config.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(config_dict, f)

    # --- PIPELINE EXECUTION ---
    try:
        with st.spinner("Processing data and generating reports..."):
            cfg = Config.from_file(cfg_path)
            msgs = RunMessages()

            # 1) Load
            loaded = load_prices(cfg, msgs=msgs)
            
            # 2) Clean + Returns + Attribution
            cleaned = clean_and_normalize(loaded.prices, cfg)
            attrib = compute_attribution(cleaned.returns, loaded.weights) if loaded.weights is not None else None
            
            # 3) KPIs
            kpi = compute_kpis(cleaned.returns, cfg)
            
            # 4) Visuals
            figs = generate_all_figures(cleaned.prices, cleaned.returns, kpi, cfg)
            
            # 5) Reports
            outputs = generate_reports(cleaned.prices, cleaned.returns, kpi, figs, attrib, cfg, msgs=msgs)

        st.success("Report generated successfully!")

        # --- DISPLAY RESULTS IN APP ---
        st.subheader("📊 Key Performance Indicators")
        st.dataframe(kpi.summary, use_container_width=True)

        if msgs.has_messages():
            for warn in msgs.warnings:
                st.warning(warn)

        st.subheader("📈 Visualizations")
        col1, col2 = st.columns(2)
        if figs.prices:
            col1.image(str(figs.prices), caption="Prices")
        if figs.drawdowns and include_drawdowns:
            col2.image(str(figs.drawdowns), caption="Drawdowns")
            
        if figs.boxplot:
            st.image(str(figs.boxplot), caption="Return Distributions (Boxplot)")

        # --- DOWNLOAD BUTTONS ---
        st.subheader("📥 Download Reports")
        dl_col1, dl_col2 = st.columns(2)
        
        if outputs.pdf and Path(outputs.pdf).exists():
            with open(outputs.pdf, "rb") as f:
                dl_col1.download_button("Download PDF Report", f, file_name="Financial_Report.pdf", mime="application/pdf")
                
        if outputs.html and Path(outputs.html).exists():
            with open(outputs.html, "rb") as f:
                dl_col2.download_button("Download HTML Report", f, file_name="Financial_Report.html", mime="text/html")

    except Exception as e:
        st.error(f"Pipeline Error: {e}")