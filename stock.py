import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Set page config
st.set_page_config(page_title="Stock Analysis Pro", page_icon="📊", layout="wide")

# Cache data fetching
@st.cache_data
def fetch_stock_data(tickers, period):
    return yf.download(tickers, period=period, group_by='ticker', threads=True)

# Welcome page
st.title("📈 Stock Analysis Pro")
st.markdown("""
**Stock Analysis Pro**: Analyze stocks with interactive charts! View price trends, 20-day SMA, and 14-day RSI. Spot oversold (RSI<30, buy) or overbought (RSI>70, sell) stocks. Download CSV data.
""")

# Sidebar
st.sidebar.title("Stock Analysis Settings")
st.sidebar.markdown("- Select/enter up to 10 tickers (e.g., AAPL,GOOGL).")
st.sidebar.markdown("- Choose period (1mo, 3mo, 6mo, 1y).")
st.sidebar.markdown("- RSI < 30 = Buy, RSI > 70 = Sell.")

# Ticker input
ticker_options = ["AAPL", "GOOGL", "TSLA", "AMD", "F", "BA", "GME"]
selected_tickers = st.sidebar.multiselect("Select stock tickers:", ticker_options, default=["AAPL", "GOOGL"])
tickers_input = st.sidebar.text_input("Enter custom tickers (comma-separated):", "")
custom_tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
tickers = list(dict.fromkeys(custom_tickers + selected_tickers))  # Remove duplicates
if len(tickers) > 10:
    st.error("Maximum 10 tickers allowed.")
    tickers = tickers[:10]
period = st.sidebar.selectbox("Select data period:", ["1mo", "3mo", "6mo", "1y"], index=3)
show_charts = st.sidebar.checkbox("Show charts for all stocks", value=False)

recommendations = []
oversold_stocks = []

# Fetch data for all tickers at once
with st.spinner("Fetching stock data..."):
    data = fetch_stock_data(tickers, period)

for stock_symbol in tickers:
    st.header(f"{stock_symbol} Analysis")
    try:
        # Extract stock data
        stock_data = data[stock_symbol] if len(tickers) > 1 else data
        if stock_data.empty or stock_data['Close'].isna().all():
            st.warning(f"No data for {stock_symbol}. Try a valid ticker.")
            recommendations.append(f"{stock_symbol}: No data")
            continue
    except Exception as e:
        st.error(f"Error fetching {stock_symbol}: {e}.")
        recommendations.append(f"{stock_symbol}: Error ({e})")
        continue

    try:
        # Calculate indicators
        stock_data['SMA20'] = stock_data['Close'].rolling(window=20).mean()
        delta = stock_data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        stock_data['RSI'] = 100 - (100 / (1 + rs))

        # Display data
        display_data = stock_data[['Close', 'SMA20', 'RSI']].tail().copy()
        display_data.index = display_data.index.strftime('%Y-%m-%d')
        st.subheader(f"{stock_symbol} Data (Last 5 Days)")
        st.dataframe(display_data.style.format("{:.2f}").background_gradient(cmap="RdYlGn", subset=["RSI"]))

        # Oversold days
        oversold_days = stock_data[stock_data['RSI'] < 30][['Close', 'RSI']].copy()
        oversold_days.index = oversold_days.index.strftime('%Y-%m-%d')
        st.subheader(f"Oversold Days (RSI < 30)")
        if not oversold_days.empty:
            st.dataframe(oversold_days.style.format("{:.2f}").background_gradient(cmap="RdYlGn", subset=["RSI"]))
            oversold_stocks.append(stock_symbol)
        else:
            st.info("None")

        # Download data
        csv = stock_data[['Close', 'SMA20', 'RSI']].to_csv()
        st.download_button(f"Download {stock_symbol} data", csv, f"{stock_symbol}_data.csv", "text/csv")

        # Signals
        latest_close = stock_data['Close'].iloc[-1]
        latest_sma = stock_data['SMA20'].iloc[-1]
        sma_signal = "Bullish (buy or hold)" if latest_close > latest_sma else "Bearish (sell or avoid)"
        latest_rsi = stock_data['RSI'].iloc[-1]
        prev_rsi = stock_data['RSI'].iloc[-2] if len(stock_data) > 1 else latest_rsi
        if latest_rsi > 70:
            rsi_signal = "Overbought (sell)"
        elif latest_rsi < 30 and prev_rsi >= 30:
            rsi_signal = "Oversold (buy - just crossed above 30)"
        elif latest_rsi < 30:
            rsi_signal = "Oversold (buy)"
        else:
            rsi_signal = "Neutral (no action)"

        recommendation = "BUY" if rsi_signal.startswith("Oversold") or (sma_signal == "Bullish (buy or hold)" and 40 <= latest_rsi <= 60) else "SELL" if rsi_signal == "Overbought (sell)" else "HOLD"
        recommendations.append(f"{stock_symbol}: {recommendation} (SMA: {sma_signal}, RSI: {latest_rsi:.2f} ({rsi_signal}))")

        # Charts (optional)
        if show_charts:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
            fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA20'], mode='lines', name='20-Day SMA', line=dict(color='orange')))
            fig1.update_layout(title=f"{stock_symbol} Price and 20-Day SMA", xaxis_title="Date", yaxis_title="Price (USD)", showlegend=True, template="plotly_dark")
            fig1.update_xaxes(tickangle=45)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=stock_data.index, y=stock_data['RSI'], mode='lines', name='RSI', line=dict(color='purple')))
            fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            fig2.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            fig2.update_layout(title=f"{stock_symbol} 14-Day RSI", xaxis_title="Date", yaxis_title="RSI", showlegend=True, template="plotly_dark")
            fig2.update_xaxes(tickangle=45)

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing {stock_symbol}: {e}")
        recommendations.append(f"{stock_symbol}: Error ({e})")

# Summary
if oversold_stocks:
    st.header("🚨 Oversold Stocks (RSI < 30)")
    st.markdown("Potential buy opportunities:")
    for stock in oversold_stocks:
        st.markdown(f"- {stock}")
else:
    st.header("🚨 Oversold Stocks (RSI < 30)")
    st.info("No stocks with RSI < 30.")

st.header("Recommendations")
for rec in recommendations:
    st.markdown(f"- {rec}")