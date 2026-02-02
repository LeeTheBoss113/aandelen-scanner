import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import date

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 2. SCAN LOGICA ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or len(df) < 252: return None
        
        # Kolomnamen opschonen
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        sma63 = close.rolling(63).mean().iloc[-1]
        sma252 = close.rolling(252).mean().iloc[-1]
        
        # RSI
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)).iloc[-1]))
        
        # Korting & Score
        hi = float(close.tail(252).max())
        dist_top = ((hi - curr) / hi) * 100
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma252: score += 10
        if curr > sma63: score += 5
        
        status = "⚖️ Hold"
        if score > 100 and curr > sma252: status = "💎 STRONG BUY"
        elif score > 80: status = "✅ Buy"
        elif rsi > 75: status = "🔥 SELL"
            
        # Maak een schone tijdreeks voor de grafiek
        hist_data = close.tail(126).copy()
        
        return {
            "Sector": sector, 
            "Ticker": ticker, 
            "Score": round(score, 1),
            "Status": status,
            "Trend3M": "✅" if curr > sma63 else "❌",
            "Trend1J": "✅" if curr > sma252
