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
        body = f"🚀 {type} ALERT\n\nBedrijf: {naam}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nCheck je dashboard voor de Box 3 route!"
        msg = MIMEText(body)
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
        
        # --- VERBETERD DIVIDEND ---
        raw_div = info.get('dividendYield', 0)
        if raw_div is None: raw_div = 0
        # Yahoo geeft soms 0.005 voor 0.5%, we maken er een percentage van:
        div = float(raw_div) * 100 if float(raw_div) < 1 else float(raw_div)
        if div > 20: div = div / 100 # Extra check voor '40%' fouten
        
        naam = info.get('longName', ticker)
        
        # Holy Grail Score: RSI van 50 = 50 punten + (Div 0.5 * 3) = 51.5 score.
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Bedrijf": naam, 
            "Ticker": ticker, 
            "RSI": round(float(rsi), 1), 
            "Div %": round(float(div), 2), 
            "Score": round(float(score), 1)
        }
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    watch_input = st.text_area("Mijn Watchlist:", "ASML.AS, KO, PG, O, ABBV, SHEL.AS, MO, AD.AS, AAPL")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")
    if st.button("📧 Stuur Test Mail"):
        if stuur_alert_mail("TEST CORP", "TEST", 99, 25, type="TEST"):
            st.success("Test-mail verzonden!")

# --- 4. DATA VERZAMELEN ---
st.title("🚀 Holy Grail Market Scanner 2026")

markt_benchmarks = ["NVDA", "TSLA", "AMZN", "MSFT", "META", "GOOGL", "ADYEN.AS", "INGA.AS", "BABA", "PYPL", "NKE"]
tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w, results_p, results_m = [], [], []
status = st.empty() 

with st.spinner('Bezig met diepe markt-analyse...'):
    for t in tickers_w:
        status.text(f"🔍 Scannen Watchlist: {t}...")
        res = scan_aandeel(t)
        if res: results_w.append(res)
        time.sleep(0.1)
    for t in tickers_p:
        status.text(f"📊 Controleren Portfolio: {t}...")
        res = scan_aandeel(t)
        if res: results_p.append(res)
        time.sleep(0.1)
    for t in markt_benchmarks:
        if t not in tickers_w:
            status.text(f"🌍 Zoeken naar Markt-kansen: {t}...")
            res = scan_aandeel(t)
            if res and (res['RSI'] < 35 or res['Score'] > 85):
                results_m.append(res)
            time.sleep(0.1)
status.empty()

# --- 5. LAYOUT ---
if not results_w and not results_p:
    st.warning("⚠️ Wachten op data... Gebruik de sidebar om tickers toe te voegen.")
else:
    c1, c2, c3, c4 = st.columns([1.5, 0.8, 1, 1])
    
    with c1:
        st.header("🔍 Scanner")
        tab1, tab2 = st.tabs(["📋 Watchlist", "🌍 Markt"])
        with tab1:
            if results_w:
                df_w = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
                st.dataframe(df_w.style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
        with tab2:
            if results_m:
                df_m = pd.DataFrame(results_m).sort_values(by="Score", ascending=False)
                st.dataframe(df_m.style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
            else: st.info("Geen uitschieters.")

    with c2:
        st.header("⚡ Signalen")
        st.subheader("💎 Buy")
        for r in (results_w + results_m):
            if r['Score'] >= 85 and r['RSI'] < 60:
                st.success(f"**{r['Bedrijf']}**")
                if r['Score'] >= 90: stuur_alert_mail(r['Bedrijf'], r['Ticker'], r['Score'], r['RSI'], "KOOP")
        st.divider()
        st.subheader("🔥 Sell")
        for r in results_p:
            if r['RSI'] >= 75:
                st.warning(f"**{r['Bedrijf']}**")
                stuur_alert_mail(r['Bedrijf'], r['Ticker'], "NVT", r['RSI'], "VERKOOP")

    with c3:
        st.header("⚖️ Portfolio")
        if results_p:
            df_p = pd.DataFrame(results_p)
            st.bar_chart(df_p.set_index('Bedrijf')['RSI'])
            for r in results_p:
                st.write(f"✅ {r['Bedrijf']}")

    with c4:
        st.header("💰 Tax")
        vermogen = st.number_input("Totaal Vermogen (€):", value=100000)
        besparing = max(0, vermogen - 57000) * 0.021
        st.metric("Box 3 Besparing", f"€{besparing:,.0f}")
        st.info("Besparing via partner-route.")

