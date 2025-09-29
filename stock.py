import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import re

# Cache data fetching
@st.cache_data
def fetch_stock_data(symbol, period):
    stock = yf.Ticker(symbol)
    return stock.history(period=period)

# Set page config
st.set_page_config(page_title="Stock Analysis Pro", page_icon="📊", layout="wide")

# Welcome page
st.title("📈 Stock Analysis Pro")
st.markdown("""
**Stock Analysis Pro**: Analyze stocks with interactive charts! View price trends, 20-day SMA, Bollinger Bands, and 14-day RSI. Spot oversold (RSI<30, buy) or overbought (RSI>70, sell) stocks like AMD, BA, NVDA. Get BUY/SELL signals (e.g., AAPL: SELL, GOOGL: BUY). Download CSV data. Powered by Yahoo Finance & Plotly.
**Note**: Recommendations prioritize RSI signals (Overbought > 70 = SELL, Oversold < 30 = BUY) over SMA.
""")

# Sidebar
st.sidebar.title("Stock Analysis Settings")
st.sidebar.markdown("- Select/enter tickers (e.g., AAPL, GOOGL, TSLA, NVDA).")
st.sidebar.markdown("- Choose period (1mo, 3mo, 6mo, 1y).")
st.sidebar.markdown("- RSI < 30 = Buy, RSI > 70 = Sell.")

# Ticker input
ticker_options = ["AAPL", "GOOGL", "TSLA", "AMD", "F", "BA", "GME", "NVDA"]
selected_tickers = st.sidebar.multiselect("Select stock tickers:", ticker_options, default=["AAPL", "GOOGL", "TSLA", "NVDA"])
tickers_input = st.sidebar.text_input("Enter custom tickers (comma-separated):", "")
# Validate and deduplicate tickers
valid_ticker = re.compile(r'^[A-Z0-9.-]+$')
if not tickers_input.strip():
    tickers = list(set(selected_tickers))  # Use only selected tickers if input is empty
else:
    tickers = list(set([ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip() and valid_ticker.match(ticker.strip())] + selected_tickers))

period = st.sidebar.selectbox("Select data period:", ["1mo", "3mo", "6mo", "1y"], index=3)

recommendations = []
oversold_stocks = []

for stock_symbol in tickers:
    st.header(f"{stock_symbol} Analysis")
    try:
        data = fetch_stock_data(stock_symbol, period)
        if data.empty or len(data) < 20:
            st.warning(f"Insufficient data for {stock_symbol}. Need at least 20 days for SMA/RSI.")
            recommendations.append(f"{stock_symbol}: No data")
            continue
    except Exception as e:
        st.error(f"Error fetching {stock_symbol}: {e}.")
        recommendations.append(f"{stock_symbol}: Error ({e})")
        continue

    try:
        # Calculate 20-day SMA and Bollinger Bands
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['STD20'] = data['Close'].rolling(window=20).std()
        data['UpperBB'] = data['SMA20'] + 2 * data['STD20']
        data['LowerBB'] = data['SMA20'] - 2 * data['STD20']

        # Calculate 14-day RSI
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
        data['RSI'] = 100 - (100 / (1 + rs))

        # Simplify dates
        data.index = data.index.strftime('%Y-%m-%d')

        # Display last 5 rows
        st.subheader(f"{stock_symbol} Data (Last 5 Days)")
        st.dataframe(data[['Close', 'SMA20', 'UpperBB', 'LowerBB', 'RSI']].tail().style.format("{:.2f}").background_gradient(cmap="RdYlGn", subset=["RSI"]))

        # Oversold days
        oversold_days = data[data['RSI'] < 30]
        st.subheader(f"Oversold Days (RSI < 30)")
        if not oversold_days.empty:
            st.dataframe(oversold_days[['Close', 'RSI']].style.format("{:.2f}").background_gradient(cmap="RdYlGn", subset=["RSI"]))
            oversold_stocks.append(stock_symbol)
        else:
            st.info("None")

        # Download data
        csv = data[['Close', 'SMA20', 'UpperBB', 'LowerBB', 'RSI']].to_csv()
        st.download_button(f"Download {stock_symbol} data", csv, f"{stock_symbol}_data.csv", "text/csv")

        # SMA analysis
        latest_close = data['Close'].iloc[-1]
        latest_sma = data['SMA20'].iloc[-1]
        sma_signal = "Bullish (buy or hold)" if latest_close > latest_sma else "Bearish (sell or avoid)"

        # RSI analysis
        latest_rsi = data['RSI'].iloc[-1]
        prev_rsi = data['RSI'].iloc[-2] if len(data) > 1 else latest_rsi
        if latest_rsi > 70:
            rsi_signal = "Overbought (sell)"
        elif latest_rsi < 30 and prev_rsi >= 30:
            rsi_signal = "Oversold (buy - just crossed below 30)"
        elif latest_rsi < 30:
            rsi_signal = "Oversold (buy)"
        else:
            rsi_signal = "Neutral (no action)"

        # Combined signal
        if rsi_signal.startswith("Oversold") or (sma_signal == "Bullish (buy or hold)" and 40 <= latest_rsi <= 60):
            recommendation = "BUY"
        elif rsi_signal == "Overbought (sell)":
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        recommendations.append(f"{stock_symbol}: {recommendation} (SMA: {sma_signal}, RSI: {latest_rsi:.2f} ({rsi_signal}))")

        # Downsample for charts
        plot_data = data.resample('W').last() if period == "1y" else data

        # Plotly SMA and Bollinger Bands chart
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['SMA20'], mode='lines', name='20-Day SMA', line=dict(color='orange')))
        fig1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['UpperBB'], mode='lines', name='Upper Bollinger Band', line=dict(color='green', dash='dash')))
        fig1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['LowerBB'], mode='lines', name='Lower Bollinger Band', line=dict(color='red', dash='dash')))
        fig1.add_trace(go.Bar(x=plot_data.index, y=plot_data['Volume'], name='Volume', yaxis='y2', opacity=0.3))
        fig1.add_trace(go.Scatter(x=[plot_data.index[-1]], y=[plot_data['Close'].iloc[-1]], mode='markers', name='Latest Price', marker=dict(color='blue', size=10)))
        fig1.add_trace(go.Scatter(x=[plot_data.index[-1]], y=[plot_data['SMA20'].iloc[-1]], mode='markers', name='Latest SMA', marker=dict(color='orange', size=10)))
        fig1.update_layout(
            title=f"{stock_symbol} Price, SMA, and Bollinger Bands",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            yaxis2=dict(title='Volume', overlaying='y', side='right'),
            showlegend=True,
            template="plotly_dark"
        )
        fig1.update_xaxes(tickangle=45)

        # Plotly RSI chart
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=plot_data.index, y=plot_data['RSI'], mode='lines', name='RSI', line=dict(color='purple')))
        fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig2.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        fig2.update_layout(title=f"{stock_symbol} 14-Day RSI", xaxis_title="Date", yaxis_title="RSI", showlegend=True, template="plotly_dark")
        fig2.update_xaxes(tickangle=45)

        # Display charts
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing {stock_symbol}: {e}")
        recommendations.append(f"{stock_symbol}: Error ({e})")

# Oversold stocks
if oversold_stocks:
    st.header("🚨 Oversold Stocks (RSI < 30)")
    st.markdown("Potential buy opportunities:")
    for stock in oversold_stocks:
        st.markdown(f"- {stock}")
else:
    st.header("🚨 Oversold Stocks (RSI < 30)")
    st.info("No stocks with RSI < 30. Try AMD, F, BA, NVDA.")

# Recommendations
st.header("Recommendations")
for rec in recommendations:
    st.markdown(f"- {rec}")

# Download recommendations
if recommendations:
    rec_df = pd.DataFrame([r.split(": ", 1) for r in recommendations], columns=["Ticker", "Recommendation"])
    csv = rec_df.to_csv(index=False)
    st.download_button("Download Recommendations", csv, "recommendations.csv", "text/csv")