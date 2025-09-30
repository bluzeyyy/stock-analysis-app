
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------
# Page Config
# ---------------------------------------------------
st.set_page_config(page_title="Stock Analysis Pro", page_icon="📊", layout="wide")

# ---------------------------------------------------
# Cache Functions
# ---------------------------------------------------
@st.cache_data
def fetch_stock_data(tickers, period="6mo"):
    """Download stock OHLCV data for multiple tickers."""
    return yf.download(tickers, period=period, group_by="ticker", threads=True)

@st.cache_data
def get_sp500_tickers():
    """Fetch latest S&P500 tickers from Wikipedia, with fallback."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}  # Fake browser header
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        sp500 = pd.read_html(response.text)[0]
        return sp500['Symbol'].tolist()
    except Exception as e:
        st.warning(f"⚠️ Could not fetch S&P 500 list (using fallback). Error: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]

# ---------------------------------------------------
# Helper: Calculate Indicators
# ---------------------------------------------------
def add_indicators(df):
    df['SMA20'] = df['Close'].rolling(window=20).mean()

    # RSI (14)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20, 2)
    df['BB_Mid'] = df['SMA20']
    df['BB_Upper'] = df['SMA20'] + 2 * df['Close'].rolling(window=20).std()
    df['BB_Lower'] = df['SMA20'] - 2 * df['Close'].rolling(window=20).std()

    return df

# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------
st.sidebar.title("⚙️ Stock Analysis Settings")
st.sidebar.markdown("Select up to 10 tickers or enter your own.")

# Load tickers
ticker_options = get_sp500_tickers()
selected_tickers = st.sidebar.multiselect("Select stock tickers:", ticker_options, default=["AAPL", "GOOGL"])
tickers_input = st.sidebar.text_input("Enter custom tickers (comma-separated):", "")
custom_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
tickers = list(dict.fromkeys(custom_tickers + selected_tickers))
if len(tickers) > 10:
    st.error("⚠️ Maximum 10 tickers allowed.")
    tickers = tickers[:10]

# Period selection
period = st.sidebar.selectbox("Data Period:", ["1mo", "3mo", "6mo", "1y"], index=2)
show_charts = st.sidebar.checkbox("Show detailed charts for each stock", value=True)

# ---------------------------------------------------
# Main App
# ---------------------------------------------------
st.title("📈 Stock Analysis Pro")
st.markdown("""
Analyze stocks using **RSI**, **SMA**, and **Bollinger Bands** to spot 
**bullish** or **bearish** signals.  
Download raw data, review signals, and compare multiple stocks at once.
""")

if not tickers:
    st.info("👈 Please select or enter at least one ticker.")
    st.stop()

with st.spinner("Fetching stock data..."):
    data = fetch_stock_data(tickers, period)

recommendations = []
signal_summary = []

# ---------------------------------------------------
# Tabs Layout
# ---------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Individual Analysis", "✅ Recommendations"])

# ---------------------------------------------------
# Tab 1: Overview (Heatmap)
# ---------------------------------------------------
with tab1:
    st.subheader("Market Heatmap (Last Close)")

    heatmap_data = []

    for stock in tickers:
        try:
            stock_data = data[stock] if len(tickers) > 1 else data
            stock_data = add_indicators(stock_data)

            latest = stock_data.iloc[-1]
            close, sma, rsi = latest['Close'], latest['SMA20'], latest['RSI']

            # Signal logic
            sma_signal = "Bullish" if close > sma else "Bearish"
            if rsi > 70:
                rsi_signal = "Overbought"
                rec = "SELL"
            elif rsi < 30:
                rsi_signal = "Oversold"
                rec = "BUY"
            else:
                rsi_signal = "Neutral"
                rec = "HOLD"

            recommendations.append(f"{stock}: {rec} (Close: {close:.2f}, SMA: {sma:.2f}, RSI: {rsi:.2f})")
            heatmap_data.append([stock, close, sma, rsi, sma_signal, rsi_signal, rec])
            signal_summary.append(rec)

        except Exception as e:
            st.error(f"{stock}: Error {e}")

    df_heatmap = pd.DataFrame(heatmap_data, columns=["Ticker", "Close", "SMA20", "RSI", "SMA Signal", "RSI Signal", "Recommendation"])
    st.dataframe(df_heatmap.style.background_gradient(cmap="RdYlGn", subset=["RSI"]))

# ---------------------------------------------------
# Tab 2: Individual Analysis
# ---------------------------------------------------
with tab2:
    for stock in tickers:
        st.subheader(f"{stock} Detailed Analysis")

        try:
            stock_data = data[stock] if len(tickers) > 1 else data
            stock_data = add_indicators(stock_data)

            # Last 5 days
            last5 = stock_data[['Close', 'SMA20', 'RSI']].tail()
            st.dataframe(last5.style.format("{:.2f}"))

            # Charts
            if show_charts:
                col1, col2 = st.columns(2)

                # Price + SMA + Bollinger Bands
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name="Close", line=dict(color="blue")))
                fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA20'], mode='lines', name="20-SMA", line=dict(color="orange")))
                fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BB_Upper'], mode='lines', name="BB Upper", line=dict(color="red", dash="dot")))
                fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BB_Lower'], mode='lines', name="BB Lower", line=dict(color="green", dash="dot")))
                fig1.update_layout(title=f"{stock} Price, SMA & Bollinger Bands", template="plotly_dark")

                # RSI Chart
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=stock_data.index, y=stock_data['RSI'], mode='lines', name="RSI", line=dict(color="purple")))
                fig2.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
                fig2.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
                fig2.update_layout(title=f"{stock} RSI (14)", template="plotly_dark")

                with col1: st.plotly_chart(fig1, use_container_width=True)
                with col2: st.plotly_chart(fig2, use_container_width=True)

            # Download CSV
            csv = stock_data[['Close', 'SMA20', 'RSI']].to_csv()
            st.download_button(f"Download {stock} Data", csv, f"{stock}_data.csv", "text/csv")

        except Exception as e:
            st.error(f"{stock}: Error {e}")

# ---------------------------------------------------
# Tab 3: Recommendations
# ---------------------------------------------------
with tab3:
    st.subheader("📌 Stock Recommendations")

    for rec in recommendations:
        if "BUY" in rec:
            st.success(rec)
        elif "SELL" in rec:
            st.error(rec)
        else:
            st.info(rec)

    # Summary counts
    st.markdown("### Signal Summary")
    st.metric("BUY signals", signal_summary.count("BUY"))
    st.metric("SELL signals", signal_summary.count("SELL"))
    st.metric("HOLD signals", signal_summary.count("HOLD"))