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
        
        # RSI Berekening
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        
        return {
            "Ticker": ticker,
            "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2),
            "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'),
            "Score": round((100 - rsi) + (div * 5), 2)
        }
    except: return None

# --- 2. HET DASHBOARD (3 KOLOMMEN) ---
st.title("🚀 Ultimate Score Scanner 2026")

col_scan, col_actie, col_port = st.columns([1, 1, 1])

# KOLOM 1: VOLLEDIGE SCANNER
with col_scan:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, TSLA, SHEL.AS, AAPL", key="scan_in")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data: results.append(data)
    
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(df_all[['Ticker', 'RSI', 'Score']], use_container_width=True)

# KOLOM 2: ACTIE-CENTRUM (DE KLEURTJES)
with col_actie:
    st.header("💎 Beste Kansen")
    
    if results:
        # Filter voor Koopkansen (RSI onder de 40)
        kansen = [r for r in results if r['RSI'] <= 40]
        
        if kansen:
            for k in kansen:
                st.success(f"### 💎 KOOP: {k['Ticker']}\n**RSI:** {k['RSI']} | **Score:** {k['Score']}\n\n*Dit aandeel is momenteel goedkoop.*")
        else:
            st.info("Geen directe koopkansen (RSI < 40) gevonden. Geduld is een schone zaak!")

# KOLOM 3: PORTFOLIO & RISICO
with col_port:
    st.header("⚖️ Monitor")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="port_in")
    mijn_tickers = [t.strip().upper() for t in port_input.split(",")]
    
    p_results = []
    for t in mijn_tickers:
        d = scan_aandeel(t)
        if d: p_results.append(d)
    
    if p_results:
        df_p = pd.DataFrame(p_results)
        
        # Laat waarschuwing zien als iets te duur wordt (RSI > 70)
        for _, row in df_p.iterrows():
            if row['RSI'] >= 70:
                st.warning(f"### ⚠️ VERKOOP: {row['Ticker']}\n**RSI:** {row['RSI']}\n\nWinst pakken?")
            else:
                st.write(f"✅ {row['Ticker']} staat op HOLD (RSI: {row['RSI']})")
        
        st.divider()
        st.write("**Spreiding:**")
        st.bar_chart(df_p['Sector'].value_counts())

# --- NIEUW: BELASTING CORRECTIE CALCULATOR ---
with col_port:
    st.divider()
    st.subheader("💰 Belasting-Impact (Box 3)")
    
    totaal_waarde = st.number_input("Totaal belegd vermogen (€):", value=100000)
    
    # Berekening voor jou (als Nederlander)
    vrijstelling = 57000  # Standaard 2026
    belastbaar = max(0, totaal_waarde - vrijstelling)
    jaarlijkse_heffing = belastbaar * 0.021  # De 2.1% effectieve druk
    
    # Berekening voor je vriendin (0% route)
    besparing = jaarlijkse_heffing
    
    col_tax1, col_tax2 = st.columns(2)
    with col_tax1:
        st.error(f"**Jouw Heffing:**\n€{jaarlijkse_heffing:,.0f}/jaar")
    with col_tax2:
        st.success(f"**Route Partner:**\n€0 /jaar")
        
    st.info(f"💡 Door het vermogen via je partner te laten lopen, bespaar je jaarlijks **€{besparing:,.0f}** aan belasting.")

