import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(naam, ticker, score, rsi, type="KOOP"):
    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        msg = MIMEText(f"Alert voor {naam} ({ticker})\nScore: {score}\nRSI: {rsi}")
        msg['Subject'] = f"💎 {type} Signaal: {naam}"
        msg['From'] = user
        msg['To'] = receiver
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        return True
    except: return False

def scan_aandeel(ticker):
    try:
        # We halen alleen de noodzakelijke kolommen op
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 10: return None
        
        # Multi-index fix
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
        # RSI berekening (robuust)
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / (down + 0.000001) # Voorkom delen door nul
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Info ophalen (Bedrijf + Dividend)
        t_obj = yf.Ticker(ticker)
        naam = t_obj.info.get('longName', ticker)
        div = (t_obj.info.get('dividendYield', 0) or 0) * 100
        
        score = (100 - float(rsi)) + (float(div) * 3)
        return {"Bedrijf": naam, "Ticker": ticker, "RSI": round(float(rsi), 1), "Div %": round(float(div), 2), "Score": round(float(score), 1)}
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    watch_input = st.text_area("Watchlist:", "ASML.AS, KO, PG, O, SHEL.AS, MO, AAPL")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")
    if st.button("📧 Test Mail"):
        stuur_alert_mail("Test", "TEST", 0, 0, "TEST")

# --- 4. DATA VERZAMELEN ---
st.title("🚀 Holy Grail Market Scanner")

markt_benchmarks = ["NVDA", "TSLA", "AMZN", "MSFT", "META", "GOOGL", "ADYEN.AS", "INGA.AS", "BABA"]
tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w, results_p, results_m = [], [], []

# Dit voorkomt het 'blanco' effect: we tonen voortgang
status = st.empty() 

with st.spinner('Bezig met scannen...'):
    # Watchlist
    for t in tickers_w:
        status.text(f"🔍 Scannen: {t}...")
        res = scan_aandeel(t)
        if res: results_w.append(res)
        time.sleep(0.2)
    
    # Portfolio
    for t in tickers_p:
        status.text(f"📊 Portfolio check: {t}...")
        res = scan_aandeel(t)
        if res: results_p.append(res)
        time.sleep(0.2)

    # Markt
    for t in markt_benchmarks:
        if t not in tickers_w:
            status.text(f"🌍 Markt kansen: {t}...")
            res = scan_aandeel(t)
            if res and (res['RSI'] < 35 or res['Score'] > 85):
                results_m.append(res)
            time.sleep(0.2)

status.empty() # Verwijder de status-tekst als hij klaar is

# --- 5. LAYOUT ---
if not results_w and not results_p:
    st.warning("⚠️ Geen data gevonden. Check je internetverbinding of tickers.")
else:
    c1, c2, c3 = st.columns([1.5, 1, 1])
    
    with c1:
        st.header("🔍 Scanner")
        tab1, tab2 = st.tabs(["📋 Watchlist", "🌍 Markt"])
        with tab1: st.dataframe(pd.DataFrame(results_w), use_container_width=True)
        with tab2: st.dataframe(pd.DataFrame(results_m), use_container_width=True)

    with c2:
        st.header("⚡ Signalen")
        # Signalen logica
        for r in results_w + results_m:
            if r['Score'] >= 85 and r['RSI'] < 60:
                st.success(f"**KOOP: {r['Bedrijf']}**")
        
        st.divider()
        for r in results_p:
            if r['RSI'] >= 75:
                st.warning(f"**VERKOOP: {r['Bedrijf']}**")

    with c3:
        st.header("⚖️ Portfolio")
        if results_p:
            df_p = pd.DataFrame(results_p)
            st.bar_chart(df_p.set_index('Bedrijf')['RSI'])
