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
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP", "RDSA.AS"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP", "PYPL"]
}

# --- 3. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 20: return None
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # Berekeningen
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / (-1 * close.diff().clip(upper=0).rolling(14).mean() + 0.000001)))).iloc[-1]
        hi, curr = float(close.max()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        score = (100 - float(rsi)) + (dist_top * 1.5)
        status = "💎 STRONG BUY" if score > 85 else "✅ Buy" if score > 70 else "⚖️ Hold" if rsi < 70 else "🔥 SELL"
        
        return {"Sector": sector, "Ticker": ticker, "Score": round(float(score), 1), "RSI": round(float(rsi), 1), "Korting": round(float(dist_top), 1), "Prijs": round(float(curr), 2), "Status": status}
    except: return None

# --- 4. DATA LADEN ---
st.title("🎯 Holy Grail: Sector Spread Dashboard")

with st.sidebar:
    st.header("⚙️ Systeem")
    watchlist_extra = st.text_input("Extra Tickers:", "AAPL, META")
    st.divider()
    st.write("De scanner verdeelt de top 15 over 5 cruciale sectoren voor optimale risicospreiding.")

all_results = []
ticker_list = [(t, s) for s, ts in SECTOREN.items() for t in ts]
if watchlist_extra:
    for t in watchlist_extra.split(","):
        ticker_list.append((t.strip().upper(), "Mijn Watchlist"))

progress = st.progress(0)
for i, (t, s) in enumerate(ticker_list):
    res = scan_aandeel(t, s)
    if res: all_results.append(res)
    progress.progress((i + 1) / len(ticker_list))
progress.empty()

# --- 5. WIDESCREEN LAYOUT ---
if all_results:
    df_all = pd.DataFrame(all_results).sort_values("Score", ascending=False)
    
    # Links: De Heatmap Tabel (40% breed) | Rechts: De Sector Kaarten (60% breed)
