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

# --- 3. ROBUUSTE DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        # Haal data op met extra veiligheidsmarge
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        
        if df is None or df.empty or len(df) < 15:
            return None
        
        # FIX: Forceer data naar een platte structuur (verwijdert MultiIndex issues)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        
        # RSI berekening
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        # Prijs stats
        hi = float(close.max())
        curr = float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        # Score & Status
        score = (100 - float(rsi)) + (dist_top * 1.5)
        
        if score > 85: status = "💎 STRONG BUY"
        elif score > 70: status = "✅ Buy"
        elif rsi > 70: status = "🔥 SELL"
        else: status = "⚖️ Hold"
        
        return {
            "Sector": sector,
            "Ticker": ticker,
            "Score": round(float(score), 1),
            "RSI": round(float(rsi), 1),
            "Korting": round(float(dist_top), 1),
            "Prijs": round(float(curr), 2),
            "Status": status
        }
    except Exception as e:
        return None

# --- 4. DATA LADEN ---
st.title("🎯 Holy Grail: Sector Spread Dashboard")

all_results = []
ticker_items = []
for s, ts in SECTOREN.items():
    for t in
