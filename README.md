# 📈 Financial Data Automation & Reporting Engine

An interactive, Python-based application for financial data analysis, KPI computation, and automated reporting. This tool fetches market data, cleans and normalizes it, calculates standard risk and performance metrics, and generates comprehensive, fully-formatted PDF and HTML reports.

## 🤝 Credits & Acknowledgments

This project is a collaborative effort bridging rigorous financial research and accessible software engineering:
* **Core Engine & Financial Logic:** Created by [Mikel Lopez](https://www.linkedin.com/in/mikellopezfinance/) as part of his Bachelor's thesis work. The backend handles the robust data processing, KPI mathematics, and report generation engines.
* **Interactive Web Application:** Built by [Mohamed Alie Kamara](https://www.linkedin.com/in/mohamed-alie-kamara-8765941a4/) using Streamlit, providing a sleek, intuitive graphical interface to make this powerful financial tool accessible to non-technical users.

## ✨ Features

* **Automated Data Loading:** Fetch price data dynamically via `yfinance`, or load custom data via CSV and Excel.
* **Data Cleaning:** Handles missing values with configurable strategies, ensures monotonic DatetimeIndexes, and calculates simple or log returns.
* **Comprehensive KPIs:** Computes Compound Annual Growth Rate (CAGR), Annualized Volatility, Sharpe Ratio, Sortino Ratio, Max Drawdown, and rolling metrics.
* **Portfolio Attribution:** Calculates period contributions and identifies top contributors and bottom detractors based on asset weights.
* **Rich Visualizations:** Automatically generates aesthetic price charts, drawdown charts, rolling returns/volatility plots, return histograms, and boxplots.
* **Exportable Reports:** Generates polished PDF and self-contained HTML reports featuring an automated executive summary, headline metrics, and embedded visualizations.
* **Configuration-Driven:** The underlying engine is highly modular, governed by structured YAML configurations.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME
2. Install the required dependencies:
It is recommended to use a virtual environment.
   ```bash
     Bash
     pip install -r requirements.txt
(Ensure your requirements.txt includes streamlit, pandas, numpy, PyYAML, yfinance, matplotlib, reportlab, and openpyxl).

🚀 Usage
The application provides an interactive web interface so you don't have to touch any code or configuration files.

To launch the app locally:
   
     Bash
     streamlit run app.py

Navigating the App:
1.Sidebar Configuration: Enter your desired ticker symbols (e.g., AAPL, MSFT), select your date ranges, and adjust KPI parameters like the annualization factor and risk-free rate.

2.Generate Report: Click the "🚀 Generate Report" button. The app will fetch the data and process the metrics.

3.Review Results: Use the tabs (📊 KPIs & Analysis, 📈 Visualizations, 📥 Downloads) to explore the data interactively on the screen.

4.Download: Grab your finalized PDF or HTML report directly from the interface!

## 📂 Project Structure
- app.py: The interactive Streamlit user interface.

- generate_report.py: The original CLI entrypoint.

- src/: Core engine modules.

   - config.py: Configuration management.

   - loader.py: Data ingestion (yfinance, CSV, Excel).

   - cleaner.py: Data cleaning and return conversion.

   - kpis.py: Performance and risk metric calculations.

   - attribution.py: Asset contribution analysis.

   - viz.py: Matplotlib visualization generation.

   - report.py: PDF (ReportLab) and HTML report builders.

   - messages.py: Warning and info message handling.

Built with Python & Streamlit.
