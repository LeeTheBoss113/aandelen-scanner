import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & EMAIL ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

def stuur_alert_mail(ticker, score, rsi, type="KOOP"):
    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        msg = MIMEText(f"🚨 {type} ALERT!\n\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}")
        msg['Subject'] = f"🚀 {type} Signaal: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        return True
    except: return False

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
        
        # HOLY GRAIL LOGICA
        rsi_factor = 100 - rsi
        if rsi > 70: rsi_factor -= 30 
        if rsi < 35: rsi_factor += 25  
        score = rsi_factor + (div * 3)
        
        return {
            "Ticker": ticker, "RSI": round(rsi, 2), "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), "Score": round(score, 2)
        }
    except: return None

# --- 2. DASHBOARD ---
st.title("🚀 Holy Grail Portfolio Dashboard 2026")

# Definieer de 4 kolommen
c1, c2, c3, c4 = st.columns([1.2, 0.8, 1, 1])

# --- KOLOM 1: SCANNER ---
with c1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO", key="w1")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    results = [scan_aandeel(t) for t in tickers if scan_aandeel(t)]
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(df_all[['Ticker', 'RSI', 'Div %', 'Score']].style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)

# --- KOLOM 2: ACTIE-CENTRUM (HIER GING HET MIS) ---
with c2:
    st.header("⚡ Signalen")
    
    # Buy Alerts
    st.subheader("💎 Buy")
    buys = [r for r in results if r['Score'] >= 85]
    if buys:
        for b in buys: st.success(f"**{b['Ticker']}** (Score: {b['Score']})")
    else: st.info("Geen koopkansen")

    st.divider()

    # Sell Alerts
    st.subheader("🔥 Sell")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p_in")
    p_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_res = [scan_aandeel(t) for t in p_tickers if scan_aandeel(t)]
    
    if p_res:
        sells = [r for r in p_res if r['RSI'] >= 70]
        if sells:
            for s in sells: st.warning(f"**{s['Ticker']}** (RSI: {s['RSI']})")
        else: st.write("Geen verkoop nodig")

# --- KOLOM 3: PORTFOLIO DETAILS ---
with c3:
    st.header("⚖️ Portfolio")
    if p_res:
        df_p = pd.DataFrame(p_res)
        st.bar_chart(df_p['Sector'].value_counts())
        for r in p_res:
            st.write(f"✅ {r['Ticker']} - RSI: {r['RSI']}")

# --- KOLOM 4: TAX BENEFIT ---
with c4:
    st.header("💰 Tax Benefit")
    vermogen = st.number_input("Vermogen (€):", value=100000)
    besparing = max(0, vermogen - 57000) * 0.021
    st.metric("Jaarlijkse Besparing", f"€{besparing:,.0f}")
    st.success(f"Route Partner: €0 belasting")
