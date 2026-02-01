import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

# Gebruik session_state om bij te houden wanneer we voor het laatst gemaild hebben
if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(naam, ticker, score, rsi, type="KOOP"):
    huidige_tijd = time.time()
    log_key = f"{ticker}_{type}"
    
    # --- CHECK: 1x PER DAG (86400 seconden) ---
    if type != "TEST":
        laatste_mail_tijd = st.session_state.mail_log.get(log_key, 0)
        if huidige_tijd - laatste_mail_tijd < 86400: # 24 uur regel
            return False

    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        body = f"🚀 {type} ALERT (Dagelijkse Update)\n\nBedrijf: {naam}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nDeze melding ontvang je maximaal 1x per 24 uur."
        msg = MIMEText(body)
        msg['Subject'] = f"💎 {type} Signaal: {naam}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        # Log de tijd van verzending
        st.session_state.mail_log[log_key] = huidige_tijd
        return True
    except:
        return False

def scan_aandeel(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 10:
            return None
        
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # RSI berekening
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Data ophalen en corrigeren
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        naam = info.get('longName', ticker)
        
        raw_div = info.get('dividendYield', 0)
        if raw_div is None: raw_div = 0
        # Correctie voor Yahoo data (0.005 vs 0.5)
        div = float(raw_div) * 100 if float(raw_div) < 1 else float(raw_div)
        if div > 25: div = div / 100 # Apple/Microsoft fix
        
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Bedrijf": naam,
            "Ticker": ticker, 
            "RSI": round(float(rsi), 1), 
            "Div %": round(float(div), 2), 
            "Score": round(float(score), 1)
        }
    except:
        return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    watch_input = st.text_area("Watchlist:", "ASML.AS, KO, PG, O, ABBV, SHEL.AS, MO, AD.AS, AAPL, MSFT, TSLA")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")
    st.info("Update-frequentie: Maximaal 1x per dag per aandeel.")
    if st.button("📧 Stuur Test Mail"):
        if stuur_alert_mail("TEST BEDRIJF", "TEST", 99, 25, type="TEST"):
            st.success("Test-mail verzonden!")

# --- 4. DATA VERZAMELEN ---
st.title("🚀 Holy Grail Market Scanner 2026")

markt_benchmarks = ["NVDA", "AMZN", "META", "GOOGL", "ADYEN.AS", "INGA.AS", "BABA", "PYPL", "NKE"]
tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w, results_p, results_m = [], [], []
status = st.empty() 

with st.spinner('Markt-analyse uitvoeren...'):
    for t in tickers_w:
        status.text(f"🔍 Scannen: {t}...")
        res = scan_aandeel(t)
        if res: results_w.append(res)
        time.sleep(0.1)
    for t in tickers_p:
        status.text(f"📊 Portfolio check: {t}...")
        res = scan_aandeel(t)
        if res: results_p.append(res)
        time.sleep(0.1)
    for t in markt_benchmarks:
        if t not in tickers_w:
            status.text(f"🌍 Markt kansen: {t}...")
            res = scan_aandeel(t)
            if res and (res['RSI'] < 35 or res['Score'] > 85):
                results_m.append(res)
            time.sleep(0.1)
status.empty()

# --- 5. LAYOUT ---
if not results_w and not results_p:
    st.warning("⚠️ Geen data. Voeg tickers toe in de sidebar.")
else:
    c1, c2, c3, c4 = st.columns([1.6, 0.8, 1, 1])
    
    with c1:
        st.header("🔍 Scanner")
        tab1, tab2 = st.tabs(["📋 Watchlist", "🌍 Markt"])
        with tab1:
            if results_w:
                df_w = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
                # Harde kleurcodes (vmin/vmax) zodat 50 niet rood wordt
                st.dataframe(df_w.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=35, vmax=85), use_container_width=True)
        with tab2:
            if results_m:
                df_m = pd.DataFrame(results_m).sort_values(by="Score", ascending=False)
                st.dataframe(df_m.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=35, vmax=85), use_container_width=True)

    with c2:
        st.header("⚡ Signalen")
        st.subheader("💎 Buy")
        for r in (results_w + results_m):
            if r['Score'] >= 85 and r['RSI'] < 60:
                st.success(f"**{r['Bedrijf']}**")
                # Verzend mail (de functie checkt zelf of het al 1x per dag gedaan is)
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

    with c4:
        st.header("💰 Tax 2026")
        vermogen = st.number_input("Totaal Vermogen (€):", value=120000)
        # 2026 Cijfers: Partnerroute vrijstelling is €114.000
        vrijstelling = 114000
        belastbaar = max(0, vermogen - vrijstelling)
        # Effectieve belastingdruk Box 3 is ~2.1% boven de vrijstelling
        taks = belastbaar * 0.0212
        
        st.metric("Te betalen Box 3", f"€{taks:,.0f}")
        st.write(f"Vrijstelling: €{vrijstelling:,.0f}")
        if taks == 0:
            st.success("✅ Je betaalt geen belasting!")
        else:
            st.error("⚠️ Je zit boven de vrijstelling.")
