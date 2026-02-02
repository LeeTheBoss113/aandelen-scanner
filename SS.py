import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        # We halen 2 jaar data op voor de SMA 252 (Jaarlijks gemiddelde)
        df = yf.download(ticker, period="2y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 252:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])

        # --- GEMIDDELDEN (TRENDS) ---
        sma_63 = close.rolling(window=63).mean().iloc[-1]  # 3 Maanden
        sma_252 = close.rolling(window=252).mean().iloc[-1] # 1 Jaar
        
        is_above_3m = curr > sma_63
        is_above_1y = curr > sma_252
        
        # --- RSI & KORTING ---
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        hi = float(close.tail(252).max()) 
        dist_top = ((hi - curr) / hi) * 100
        
        # --- SCORE BEREKENING ---
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if is_above_1y: score += 10
        if is_above_3m: score += 5
        
        if score > 100 and is_above_1y: status = "💎 STRONG BUY"
        elif score > 80: status = "✅ Buy"
        elif rsi > 75 or (curr < sma_252 and dist_top < 2): status = "🔥 SELL"
        else: status = "⚖️ Hold"
        
        return {
            "Sector": sector, "Ticker": ticker, "Score": round(float(score), 1),
            "RSI": round(
