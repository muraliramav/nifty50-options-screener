import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import pandas_ta as ta
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

def fetch_price_data(ticker, period="5d", interval="15m"):
    df = yf.download(ticker + ".NS", period=period, interval=interval, progress=False)
    if not df.empty:
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
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
    return
