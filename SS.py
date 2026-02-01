import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Heatmap", layout="wide")

# --- 2. DE SCAN FUNCTIE ---
def scan_aandeel(ticker):
    try:
        # 1 jaar data voor de 52-wk stats
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 30: return None
        
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # RSI Berekening
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rs = up / (down + 0.000001)
        rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Prijs stats
        hi, curr = float(close.max()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        # KANS SCORE FORMULE (Zonder spaties in keys)
        # We belonen een lage RSI en een hoge korting
        kans_score = (100 - rsi_val) + (dist_top * 1.5)
        
        status = "💎 STRONG BUY" if kans_score > 85 else "✅ Buy" if kans_score > 70 else "⚖️ Hold" if rsi_val < 70 else "🔥 SELL"
        
        return {
            "Status": status,
            "Ticker": ticker,
            "Kans_Score": round(kans_score, 1),
            "Prijs": round(curr, 2),
            "RSI": round(rsi_val, 1),
            "Korting_Top": round(dist_top, 1),
        }
    except: return None

# --- 3. DASHBOARD ---
st.title("🎯 Markt Kansen Heatmap")
st.write("Visualisatie van de beste instapmomenten op basis van RSI en 52-weken herstelpotentieel.")

with st.sidebar:
    st.header("⚙️ Instellingen")
    tickers = st.text_area("Tickers:", "ASML.AS, KO, GOOGL, NVDA, TSLA, AMZN, NFLX, SHEL.AS, AD.AS, PYPL, DIS, AAPL")
    st.divider()
    st.info("De Kans Score stijgt naarmate een aandeel verder is 'uitgeput' (lage RSI) en verder van zijn top staat.")

ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
results = []

# Voortgangsbalk tonen tijdens scannen
if ticker_list:
    progress_bar = st.progress(0)
