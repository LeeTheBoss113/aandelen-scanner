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
        
        # RSI 14
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        score = (100 - rsi) + (div * 5)
        
        return {
            "Ticker": ticker, "RSI": round(rsi, 2), "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), "Score": round(score, 2)
        }
    except: return None

# --- 2. HET DASHBOARD (4 KOLOMMEN) ---
st.title("🚀 Ultimate Financial Dashboard 2026")

col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

# --- KOLOM 1: SCANNER MET GEKLEURDE TABEL ---
with col1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, TSLA, SHEL.AS", key="c1")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data: results.append(data)
    
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        # FUNCTIE VOOR KLEUREN IN DE TABEL
        def color_rsi(val):
            if val <= 35: color = '#90ee90' # Lichtgroen (Koop)
            elif val >= 70: color = '#ffcccb' # Lichtrood (Verkoop)
            else: color = 'white'
            return f'background-color: {color}'

        # Toepassen van de styling
        styled_df = df_all[['Ticker', 'RSI', 'Score']].style.applymap(color_rsi, subset=['RSI'])
        
        st.dataframe(styled_df, use_container_width=True)

# --- KOLOM 2: BESTE KANSEN ---
with col2:
    st.header("💎 Kansen")
    kansen = [r for r in results if r['RSI'] <= 40]
    if kansen:
        for k in kansen:
            st.success(f"**KOOP: {k['Ticker']}**\nRSI: {k['RSI']}")
    else:
        st.info("Geen RSI < 40")

# --- KOLOM 3: PORTFOLIO ---
with col3:
    st.header("⚖️ Monitor")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="c3")
    mijn_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_results = [scan_aandeel(t) for t in mijn_tickers if scan_aandeel(t)]
    if p_results:
        for r in p_results:
            status = "⚠️ SELL" if r['RSI'] >= 70 else "✅ HOLD"
            st.write(f"{status} **{r['Ticker']}** ({r['RSI']})")
        st.bar_chart(pd.DataFrame(p_results)['Sector'].value_counts())

# --- KOLOM 4: TAX-SAVER ---
with col4:
    st.header("💰 Belasting")
    vermogen = st.number_input("Vermogen (€):", value=100000, step=10000)
    
    # Box 3 berekening 2026 (Forfaitair)
    vrijstelling = 57000
    belastbaar = max(0, vermogen - vrijstelling)
    heffing_nl = belastbaar * 0.021  # Effectieve druk NL
    
    st.error(f"Heffing jij: €{heffing_nl:,.0f}/j")
    st.success(f"Heffing zij: €0 /j")
    st.metric("Jaarlijkse Besparing", f"€{heffing_nl:,.0f}")
    st.caption("Status Partner: Buitenlands Belastingplichtig")


