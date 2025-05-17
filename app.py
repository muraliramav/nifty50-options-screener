import streamlit as st
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objs as go
import time

st.set_page_config(page_title="Live Nifty50 Options Picks", layout="wide")
st.title("📈 Live Nifty50 Options Trading Screener")

NIFTY50_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "KOTAKBANK", "LT", "ITC", "HINDUNILVR",
    "AXISBANK", "BAJFINANCE", "BHARTIARTL", "HCLTECH", "WIPRO"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_option_chain(symbol="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=HEADERS)
    time.sleep(1)
    response = session.get(url, headers=HEADERS)
    data = response.json()
    records = data['records']['data']
    ce_list = []
    pe_list = []
    for rec in records:
        strike_price = rec['strikePrice']
        if 'CE' in rec and rec['CE']:
            ce = rec['CE']
            ce_list.append({
                'Strike Price': strike_price,
                'Open Interest': ce['openInterest'],
                'CALLS/PUTS': 'CE'
            })
        if 'PE' in rec and rec['PE']:
            pe = rec['PE']
            pe_list.append({
                'Strike Price': strike_price,
                'Open Interest': pe['openInterest'],
                'CALLS/PUTS': 'PE'
            })
    df_ce = pd.DataFrame(ce_list)
    df_pe = pd.DataFrame(pe_list)
    df = pd.concat([df_ce, df_pe], ignore_index=True)
    return df

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_price_data(ticker, period="5d", interval="15m"):
    df = yf.download(ticker + ".NS", period=period, interval=interval, progress=False)
    if not df.empty:
        df['EMA_20'] = calculate_ema(df['Close'], 20)
        df['EMA_50'] = calculate_ema(df['Close'], 50)
        df['RSI_14'] = calculate_rsi(df['Close'], 14)
    return df

def analyze_stock(df):
    latest = df.iloc[-1]
    signal = ""
    if latest['EMA_20'] > latest['EMA_50'] and latest['RSI_14'] > 60:
        signal = "Bullish"
    elif latest['EMA_20'] < latest['EMA_50'] and latest['RSI_14'] < 40:
        signal = "Bearish"
    else:
        signal = "Neutral"
    return {
        "Price": round(latest['Close'], 2),
        "EMA20": round(latest['EMA_20'], 2),
        "EMA50": round(latest['EMA_50'], 2),
        "RSI": round(latest['RSI_14'], 2),
        "Signal": signal
    }

def analyze_option_chain(df):
    pe_data = df[df['CALLS/PUTS'] == 'PE']
    ce_data = df[df['CALLS/PUTS'] == 'CE']
    support_strike = pe_data.sort_values('Open Interest', ascending=False).iloc[0]['Strike Price'] if not pe_data.empty else None
    resistance_strike = ce_data.sort_values('Open Interest', ascending=False).iloc[0]['Strike Price'] if not ce_data.empty else None
    return support_strike, resistance_strike

def score_stock(stock_data, support, resistance):
    score = 0
    reasons = []
    if stock_data["Signal"] == "Bullish":
        score += 2
        reasons.append("Bullish Price Trend (+2)")
    elif stock_data["Signal"] == "Bearish":
        score -= 2
        reasons.append("Bearish Price Trend (-2)")

    price = stock_data["Price"]
    if support:
        dist_to_support = abs(price - support)
        if dist_to_support <= 20:
            score += 1
            reasons.append(f"Near Support {support} (+1)")
    if resistance:
        dist_to_resistance = abs(price - resistance)
        if dist_to_resistance <= 20:
            score -= 1
            reasons.append(f"Near Resistance {resistance} (-1)")
    return score, reasons

st.sidebar.header("Settings")
selected_symbol = st.sidebar.selectbox("Select Index for Option Chain", ["NIFTY", "BANKNIFTY"])
refresh_seconds = st.sidebar.slider("Refresh every (seconds)", 60, 600, 300)

if st.button("Fetch & Analyze Now") or 'last_fetch' not in st.session_state or (time.time() - st.session_state.last_fetch) > refresh_seconds:
    with st.spinner("Fetching live option chain data from NSE..."):
        try:
            option_chain_df = fetch_option_chain(selected_symbol)
            st.session_state.option_chain_df = option_chain_df
            st.session_state.last_fetch = time.time()
            st.success("Fetched option chain data.")
        except Exception as e:
            st.error(f"Failed to fetch NSE data: {e}")

if 'option_chain_df' in st.session_state:
    support, resistance = analyze_option_chain(st.session_state.option_chain_df)
    st.write(f"**Support (Max PE OI):** {support} | **Resistance (Max CE OI):** {resistance}")
else:
    st.info("Fetch option chain data to continue.")

results = []
if 'option_chain_df' in st.session_state:
    with st.spinner("Fetching price data and scoring stocks..."):
        for ticker in NIFTY50_STOCKS:
            df_price = fetch_price_data(ticker)
            if df_price.empty:
                continue
            analysis = analyze_stock(df_price)
            analysis["Ticker"] = ticker
            score, reasons = score_stock(analysis, support, resistance)
            analysis["Score"] = score
            analysis["Reasons"] = "; ".join(reasons)
            results.append(analysis)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="Score", ascending=False)
    st.subheader("Ranked Nifty50 Stocks for Options Trading")
    st.dataframe(df_results[["Ticker", "Price", "EMA20", "EMA50", "RSI", "Signal", "Score", "Reasons"]])

    st.subheader("Price Charts for Top 3 Stocks")
    for ticker in df_results.head(3)["Ticker"]:
        df_price = fetch_price_data(ticker)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_price.index,
                                     open=df_price['Open'], high=df_price['High'],
                                     low=df_price['Low'], close=df_price['Close'], name='Candles'))
        fig.add_trace(go.Scatter(x=df_price.index, y=df_price['EMA_20'], mode='lines', name='EMA20'))
        fig.add_trace(go.Scatter(x=df_price.index, y=df_price['EMA_50'], mode='lines', name='EMA50'))
        fig.update_layout(title=f"{ticker} Price Chart", template='plotly_dark', height=400)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Please fetch option chain data first.")
