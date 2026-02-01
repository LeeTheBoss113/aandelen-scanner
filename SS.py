import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

if 'last_mail_sent' not in st.session_state:
    st.session_state.last_mail_sent = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(naam, ticker, score, rsi, type="KOOP"):
    vandaag = time.strftime("%Y-%m-%d")
    log_key = f"{ticker}_{type}_{vandaag}"
    
    if log_key in st.session_state.last_mail_sent:
        return False

    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        body = f"🚀 {type} ALERT\n\nBedrijf: {naam}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nCheck dashboard: Maximaal 1 mail per dag."
        msg = MIMEText(body)
        msg['Subject'] = f"💎 {type} Signaal: {naam}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        st.session_state.last_mail_sent[log_key] = True
        return True
    except:
        return False

def scan_aandeel(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 10: return None
        
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        naam = info.get('longName', ticker)
        raw_div = info.get('dividendYield', 0) or 0
        div = float(raw_div) * 100 if float(raw_div) < 1 else float(raw_div)
        if div > 25: div = div / 100 
        
        score = (100 - float(rsi)) + (float(div) * 3)
        return {"Bedrijf": naam, "Ticker": ticker, "RSI": round(float(rsi), 1), "Div %": round(float(div), 2), "Score": round(float(score), 1)}
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    watch_input = st.text_area("Watchlist:", "ASML.AS, KO, PG, O, ABBV, SHEL.AS, MO, AD.AS, AAPL, MSFT, TSLA")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")
    st.info("E-mail filter: Sweet Spot (Score 88-94)")

# --- 4. DATA VERZAMELEN ---
st.title("🚀 Holy Grail Dashboard 2026")

markt_benchmarks = ["NVDA", "AMZN", "META", "GOOGL", "ADYEN.AS", "INGA.AS", "BABA", "PYPL", "NKE"]
tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w, results_p, results_m = [], [], []
status = st.empty() 

with st.spinner('Bezig met scannen...'):
    for t in tickers_w:
        status.text(f"🔍 Scan: {t}")
        res = scan_aandeel(t)
        if res: results_w.append(res)
        time.sleep(0.1)
    for t in tickers_p:
        status.text(f"📊 Portfolio: {t}")
        res = scan_aandeel(t)
        if res: results_p.append(res)
        time.sleep(0.1)
    for t in markt_benchmarks:
        if t not in tickers_w:
            status.text(f"🌍 Markt: {t}")
            res = scan_aandeel(t)
            if res and (res['RSI'] < 35 or res['Score'] > 85): results_m.append(res)
            time.sleep(0.1)
status.empty()

# --- 5. LAYOUT ---
if results_w or results_p:
    c1, c2, c3, c4 = st.columns([1.6, 0.9, 1, 1])
    
    with c1:
        st.header("🔍 Scanner")
        tab1, tab2 = st.tabs(["📋 Watchlist", "🌍 Markt"])
        with tab1:
            df_w = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
            st.dataframe(df_w.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=35, vmax=85), use_container_width=True)
        with tab2:
            if results_m:
                df_m = pd.DataFrame(results_m).sort_values(by="Score", ascending=False)
                st.dataframe(df_m.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=35, vmax=85), use_container_width=True)

    with c2:
        st.header("⚡ Signalen")
        st.subheader("💎 Buy")
        for r in (results_w + results_m):
            s, rsi = r['Score'], r['RSI']
            if s >= 85:
                if s > 95:
                    st.error(f"⚠️ **{r['Ticker']}** ({s}) - Falling Knife?")
                else:
                    st.success(f"**{r['Ticker']}** ({s})")
                
                # Sweet spot mail trigger
                if 88 <= s <= 94 and rsi > 15:
                    stuur_alert_mail(r['Bedrijf'], r['Ticker'], s, rsi, "OPTIMALE KOOP")
        
        st.divider()
        st.subheader("🔥 Sell")
        for r in results_p:
            if r['RSI'] >= 75:
                st.warning(f"**{r['Ticker']}** (RSI: {r['RSI']})")
                if r['RSI'] >= 80:
                    stuur_alert_mail(r['Bedrijf'], r['Ticker'], "NVT", r['RSI'], "VERKOOP")

    with c3:
        st.header("⚖️ Portfolio")
        if results_p:
            df_p = pd.DataFrame(results_p)
            st.bar_chart(df_p.set_index('Ticker')['RSI'])

    with c4:
        st.header("💰 Tax 2026")
        vermogen = st.number_input("Totaal Vermogen (€):", value=120000)
        vrijstelling = 114000
        taks = max(0, vermogen - vrijstelling) * 0.0212
        st.metric("Box 3 Belasting", f"€{taks:,.0f}")
        st.caption(f"Gezamenlijke vrijstelling: €{vrijstelling:,.0f}")
