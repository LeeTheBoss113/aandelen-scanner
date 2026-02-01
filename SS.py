import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Investment Hub 2026", layout="wide")

# --- 2. GEDEELDE FUNCTIE VOOR DATA ---
def scan_aandeel(ticker, sector_naam="Watchlist"):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 20: return None
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        delta = close.diff()
        up, down = delta.clip(lower=0).rolling(14).mean(), -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)))).iloc[-1]
        hi, curr = float(close.max()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        kans_score = (100 - float(rsi)) + (dist_top * 1.5)
        status = "💎 STRONG BUY" if kans_score > 85 else "✅ Buy" if kans_score > 70 else "⚖️ Hold" if rsi < 70 else "🔥 SELL"
        
        return {
            "Sector": sector_naam, "Ticker": ticker, "Score": round(float(kans_score), 1),
            "RSI": round(float(rsi), 1), "Korting": round(float(dist_top), 1),
            "Prijs": round(float(curr), 2), "Status": status
        }
    except: return None

# --- 3. SIDEBAR NAVIGATIE ---
with st.sidebar:
    st.title("🚀 Hub Navigatie")
    keuze = st.radio("Kies je overzicht:", ["🏠 Home & Sectoren", "📋 Mijn Watchlist", "💰 Tax Calculator"])
    st.divider()
    st.info("De Hub ververst live data van Yahoo Finance.")

# --- 4. PAGINA: HOME & SECTOREN ---
if keuze == "🏠 Home & Sectoren":
    st.title("🎯 Sector-Gespreide Heatmap")
    SECTOREN = {
        "💻 Big Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
        "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS"],
        "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
        "🛒 Consument": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
        "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
    }
    
    all_results = []
    progress = st.progress(0)
    ticker_flat_list = [t for sublist in SECTOREN.values() for t in sublist]
    
    for i, (sec, tickers) in enumerate(SECTOREN.items()):
        for t in tickers:
            res = scan_aandeel(t, sec)
            if res: all_results.append(res)
        progress.progress((i + 1) / len(SECTOREN))
    
    if all_results:
        df_all = pd.DataFrame(all_results)
        cols = st.columns(len(SECTOREN))
        for i, (sec_naam, col) in enumerate(zip(SECTOREN.keys(), cols)):
            with col:
                st.subheader(sec_naam)
                sec_df = df_all[df_all['Sector'] == sec_naam].sort_values('Score', ascending=False).head(3)
                for row in sec_df.itertuples():
                    with st.container(border=True):
                        st.metric(label=row.Ticker, value=f"{row.Score} Ptn", delta=f"-{row.Korting}%")
                        if "STRONG" in row.Status: st.success(row.Status)
                        elif "Buy" in row.Status: st.info(row.Status)
                        elif "SELL" in row.Status: st.error(row.Status)
                        else: st.warning(row.Status)

# --- 5. PAGINA: MIJN WATCHLIST ---
elif keuze == "📋 Mijn Watchlist":
    st.title("📋 Persoonlijke Scanner")
    user_input = st.text_input("Voeg tickers toe (gescheiden door komma):", "ASML.AS, KO, TSLA, AAPL")
    tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    results = []
    for t in tickers:
        res = scan_aandeel(t)
        if res: results.append(res)
    
    if results:
        df_w = pd.DataFrame(results).sort_values('Score', ascending=False)
        st.dataframe(df_w.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=40, vmax=100), use_container_width=True)

# --- 6. PAGINA: TAX ---
elif keuze == "💰 Tax Calculator":
    st.title("💰 Belastingdruk Box 3 (2026)")
    vermogen = st.number_input("Totaal Vermogen (€):", value=120000, step=1000)
    vrijstelling = 114000
    belastbaar = max(0, vermogen - vrijstelling)
    taks = belastbaar * 0.0212
    
    c1, c2 = st.columns(2)
    c1.metric("Te betalen belasting", f"€{taks:,.0f}")
    c2.metric("Heffingsvrij vermogen", f"€{vrijstelling:,.0f}")
    
    st.progress(min(1.0, vermogen / 200000))
    st.caption("Let op: Dit is een schatting op basis van de verwachte tarieven voor 2026.")
