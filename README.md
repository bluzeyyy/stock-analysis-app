# Stock Analysis Pro

**Stock Analysis Pro**: Analyze stocks with interactive charts! View price trends, 20-day SMA, and 14-day RSI. Spot oversold (RSI<30, buy) or overbought (RSI>70, sell) stocks like AMD, BA. Get BUY/SELL signals (e.g., AAPL: SELL, GOOGL: BUY). Download CSV data. Powered by Yahoo Finance & Plotly.

## Features
- **Price Trends**: Interactive charts showing stock prices and 20-day SMA.
- **RSI Signals**: 14-day RSI to spot oversold (RSI < 30, buy) or overbought (RSI > 70, sell) conditions.
- **Oversold Alerts**: Highlights stocks with RSI < 30 for buy opportunities.
- **Recommendations**: Clear BUY, SELL, or HOLD signals.
- **Data Download**: Export stock data as CSV.

## How to Run Locally
1. Clone the repo: `git clone https://github.com/bluzeyyy/stock-analysis-app.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `streamlit run stock.py`
4. Open http://localhost:8501

## Deployment
Deployed on Streamlit Cloud: [stock-vision-pro.streamlit.app](https://stock-vision-pro.streamlit.app)

## Tech Stack
- Python, Streamlit, yfinance, pandas, plotly, matplotlib

Built by [bluzeyyy](https://github.com/bluzeyyy).