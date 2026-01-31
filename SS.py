import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

# Initialiseer mail log in session state
if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(ticker, score, rsi, type="KOOP"):
    huidige_tijd = time.time()
    log_key = f"{ticker}_{type}"
    
    if type != "TEST":
        last_sent = st.session_state.mail_log.get(log_key, 0)
        if huidige_tijd - last_sent < 3600:
            return False

    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        msg = MIMEText(f"Type: {type}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nCheck je dashboard voor de Box 3 route!")
        msg['Subject'] = f"💎 {type} Alert: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        st.session_state.mail_log[log_key] = huidige_tijd
        return True
    except:
        return False

def scan_aandeel(ticker):
    try:
        # LIGHT METHODE: threads=False voorkomt MemoryError
        # period="1mo" is genoeg voor RSI en bespaart geheugen
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        
        if df.empty or len(df) < 15:
            return None

        # Fix voor Multi-index
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][ticker]
        else:
            close_prices = df['Close']
            
        # Efficiënte RSI berekening
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / down
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Alleen essentiële info ophalen
        t_obj = yf.Ticker(ticker)
        div = (t_obj.info.get('dividendYield', 0) or 0) * 100
        
        # Holy Grail Score
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Ticker": ticker, 
            "RSI": round(float(rsi), 2), 
            "Div %": round(float(div), 2), 
            "Score": round(float(score), 2)
        }
    except:
        return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    if st.button("📧 Stuur Test Mail"):
        if stuur_alert_mail("TEST", 99, 25, type="TEST"):
            st.success("Test-mail verzonden!")
        else:
            st.error("Mail mislukt. Check je Secrets.")
            
    st.divider()
    watch_input = st.text_area("Watchlist:", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO, AAPL")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")

# --- 4. DASHBOARD LAYOUT ---
st.title("🚀 Holy Grail Dashboard 2026")

c1, c2, c3, c4 = st.columns([1.2, 0.8, 1, 1])

# Data ophalen met pauzes tegen server-stress
tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w = []
results_p = []

with st.spinner('Beursdata één voor één inladen...'):
    # Watchlist scan
    for tw in tickers_w:
        res = scan_aandeel(tw)
        if res: results_w.append(res)
        time.sleep(0.2) # Korte pauze voor stabiliteit
        
    # Portfolio scan
    for tp in tickers_p:
        res = scan_aandeel(tp)
        if res: results_p.append(res)
        time.sleep(0.2)

# --- KOLOMMEN VULLEN ---

with c1:
    st.header("🔍 Scanner")
    if results_w:
        df_w = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
        st.dataframe(df_w, use_container_width=True)

with c2:
    st.header("⚡ Signalen")
    
    # --- GEFILTERDE BUY ALERTS ---
    st.subheader("💎 Buy Alerts")
    # Een koop is pas een koop als de score hoog is EN de RSI niet te hoog (bijv. onder 60)
    buys = [r for r in results_w if r['Score'] >= 85 and r['RSI'] < 60]
    
    if buys:
        for b in buys:
            st.success(f"**KOOP: {b['Ticker']}** (Score: {b['Score']})")
            if b['Score'] >= 90:
                stuur_alert_mail(b['Ticker'], b['Score'], b['RSI'], "KOOP")
    else:
        st.info("Geen 'ondergewaardeerde' Holy Grails gevonden.")

    st.divider()

    # --- GEFILTERDE SELL ALERTS ---
    st.subheader("🔥 Sell Alerts")
    # Een verkoop doe je alleen als de RSI echt extreem is (bijv. boven 75)
    sells = [r for r in results_p if r['RSI'] >= 75]
    
    if sells:
        for s in sells:
            st.warning(f"**VERKOOP: {s['Ticker']}** (RSI: {s['RSI']})")
            stuur_alert_mail(s['Ticker'], "N.V.T.", s['RSI'], "VERKOOP")
    else:
        st.write("Geen verkoop nodig.")

with c3:
    st.header("⚖️ Portfolio")
    if results_p:
        df_p = pd.DataFrame(results_p)
        st.bar_chart(df_p.set_index('Ticker')['RSI'])

with c4:
    st.header("💰 Tax")
    vermogen = st.number_input("Vermogen (€):", value=100000)
    besparing = max(0, vermogen - 57000) * 0.021
    st.metric("Box 3 Besparing", f"€{besparing:,.0f}")

