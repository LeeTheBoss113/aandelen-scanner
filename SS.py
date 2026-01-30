import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText


# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Ultimate Score Scanner 2026", layout="wide")

def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = (info.get('dividendYield', 0) or 0) * 100
        # De Mix Score: Lage RSI + Hoog Dividend = Hoge Score
        score = (100 - rsi) + (div * 5)
        
        return {
            "Ticker": ticker, "RSI": round(rsi, 2), "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), "Score": round(score, 2)
        }
    except: return None

# --- 2. STYLING FUNCTIES ---
def style_results(df):
    def color_rsi(val):
        if val <= 35: return 'background-color: #90ee90; color: black;' # Groen
        if val >= 70: return 'background-color: #ffcccb; color: black;' # Rood
        return ''

    def color_score(val):
        # Hoe hoger de score, hoe intenser groen
        opacity = min(val / 150, 1.0) # We normaliseren rond een score van 150
        return f'background-color: rgba(0, 128, 0, {opacity}); color: white if {opacity} > 0.5 else black'

    return df.style.applymap(color_rsi, subset=['RSI'])\
                   .background_gradient(cmap='Greens', subset=['Score'])

# --- 3. HET DASHBOARD (4 KOLOMMEN) ---
st.title("🚀 Ultimate Financial Dashboard 2026")

col1, col2, col3, col4 = st.columns([1.2, 0.8, 1, 1])

# --- KOLOM 1: SCANNER (DE GEKLEURDE MIX) ---
with col1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, TSLA, SHEL.AS, O, ABBV", key="c1")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    results = [scan_aandeel(t) for t in tickers if scan_aandeel(t)]
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(style_results(df_all[['Ticker', 'RSI', 'Div %', 'Score']]), use_container_width=True)

# --- KOLOM 2: BESTE KANSEN (DE FILTERS) ---
with col2:
    st.header("💎 Top Kansen")
    kansen = [r for r in results if r['RSI'] <= 40 or r['Score'] >= 80]
    if kansen:
        for k in sorted(kansen, key=lambda x: x['Score'], reverse=True):
            st.success(f"**{k['Ticker']}**\nScore: {k['Score']} (RSI: {k['RSI']})")
    else:
        st.info("Geen uitschieters gevonden.")

# --- KOLOM 3: MONITOR & SPREIDING ---
with col3:
    st.header("⚖️ Portfolio")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="c3")
    mijn_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_results = [scan_aandeel(t) for t in mijn_tickers if scan_aandeel(t)]
    if p_results:
        df_p = pd.DataFrame(p_results)
        for r in p_results:
            icon = "🔴" if r['RSI'] >= 70 else "🟢"
            st.write(f"{icon} **{r['Ticker']}** - RSI: {r['RSI']}")
        st.bar_chart(df_p['Sector'].value_counts())

# --- KOLOM 4: TAX-SAVER (DE BELASTING) ---
with col4:
    st.header("💰 Tax-Hedge")
    vermogen = st.number_input("Vermogen (€):", value=100000, step=5000)
    vrijstelling = 57000
    belastbaar = max(0, vermogen - vrijstelling)
    heffing_nl = belastbaar * 0.021 
    
    st.metric("Jaarlijkse Heffing (NL)", f"€{heffing_nl:,.0f}", delta="-100%", delta_color="inverse")
    st.write(f"**Effectieve druk:** 2,1% boven de vrijstelling.")
    st.success(f"**Route Partner:**\nGeen Box 3 heffing verschuldigd.")
    st.caption("Gebaseerd op Filipijnse residentie/nationaliteit status.")
