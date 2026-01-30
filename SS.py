import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & EMAIL ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

# Initializeer een 'log' om mail-tijden bij te houden
if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

def stuur_alert_mail(ticker, score, rsi, type="KOOP"):
    huidige_tijd = time.time()
    last_sent = st.session_state.mail_log.get(f"{ticker}_{type}", 0)
    
    # Check of er al een uur verstreken is (3600 seconden)
    if huidige_tijd - last_sent < 3600:
        return False # Te vroeg voor een nieuwe mail

    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        inhoud = f"🚀 {type} ALERT!\n\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nCheck je dashboard voor details."
        msg = MIMEText(inhoud)
        msg['Subject'] = f"💎 {type} Signaal: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        # Update de log na succesvol verzenden
        st.session_state.mail_log[f"{ticker}_{type}"] = huidige_tijd
        return True
    except:
        return False

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
        
        rsi_factor = 100 - rsi
        if rsi > 70: rsi_factor -= 30 
        if rsi < 35: rsi_factor += 25  
        score = rsi_factor + (div * 3)
        
        return {
            "Ticker": ticker, "RSI": round(rsi, 2), "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), "Score": round(score, 2)
        }
    except: return None

# --- 2. HET DASHBOARD ---
st.title("🚀 Holy Grail Portfolio Dashboard 2026")

c1, c2, c3, c4 = st.columns([1.2, 0.8, 1, 1])

# --- KOLOM 1: SCANNER ---
with c1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist (tickers met komma):", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO", key="w1")
    
    if watch_input:
        tickers = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
        
        with st.spinner('Data ophalen...'):
            results = []
            for t in tickers:
                data = scan_aandeel(t)
                if data:
                    results.append(data)
            
            if results:
                df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
                st.dataframe(df_all[['Ticker', 'RSI', 'Div %', 'Score']].style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
            else:
                st.error("Geen data gevonden. Check of de tickers correct zijn (bijv. ASML.AS).")
    else:
        st.warning("Vul tickers in om te scannen.")

# --- KOLOM 2: SIGNALEER-CENTRUM ---
with c2:
    st.header("⚡ Signalen")
    
    # Gebruik de results van kolom 1
    if 'results' in locals() and results:
        buys = [r for r in results if r['Score'] >= 85]
        if buys:
            for b in buys:
                st.success(f"**KOOP: {b['Ticker']}** (Score: {b['Score']})")
                if b['Score'] >= 90:
                    if stuur_alert_mail(b['Ticker'], b['Score'], b['RSI'], "KOOP"):
                        st.toast(f"Mail verzonden voor {b['Ticker']}!")
        else:
            st.info("Geen koop-signalen.")
    
    st.divider()

    st.subheader("🔥 Sell")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p_in")
    
    if port_input:
        p_tickers = [t.strip().upper() for t in port_input.split(",") if t.strip()]
        with st.spinner('Portfolio scannen...'):
            p_res = []
            for pt in p_tickers:
                p_data = scan_aandeel(pt)
                if p_data:
                    p_res.append(p_data)
            
            if p_res:
                sells = [r for r in p_res if r['RSI'] >= 70]
                if sells:
                    for s in sells:
                        st.warning(f"**VERKOOP: {s['Ticker']}** (RSI: {s['RSI']})")
                        if s['RSI'] >= 75:
                            if stuur_alert_mail(s['Ticker'], "N.V.T.", s['RSI'], "VERKOOP"):
                                st.toast(f"Verkoop-alert verzonden!")
                else:
                    st.write("Geen verkoop nodig.")
# --- KOLOM 3: PORTFOLIO WEERGAVE ---
with c3:
    st.header("⚖️ Portfolio")
    if p_res:
        df_p = pd.DataFrame(p_res)
        st.bar_chart(df_p.set_index('Ticker')['RSI']) # RSI per aandeel
        for r in p_res:
            st.write(f"🔹 **{r['Ticker']}** - {r['Sector']}")
    else:
        st.write("Portfolio is leeg.")

# --- KOLOM 4: TAX BENEFIT ---
with c4:
    st.header("💰 Tax-Hedge")
    vermogen = st.number_input("Totaal Vermogen (€):", value=100000)
    besparing = max(0, vermogen - 57000) * 0.021
    st.metric("Jaarlijkse Besparing", f"€{besparing:,.0f}", delta="Tax Free")
    st.info("Status: Box 3 Vrijstelling actief.")

