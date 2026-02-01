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
        msg = MIMEText(f"🚀 {type} ALERT\n\nBedrijf: {naam}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}")
        msg['Subject'] = f"💎 {type} Signaal: {naam}"
        msg['From'] = user
        msg['To'] = receiver
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        st.session_state.last_mail_sent[log_key] = True
        return True
    except: return False

def scan_aandeel(ticker):
    try:
        # We halen 1 jaar data op voor de 52-wk stats
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 20: return None
        
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # 1. RSI (laatste 14 dagen)
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # 2. 52-Weken Stats
        current_price = float(close_prices.iloc[-1])
        hi_52 = float(close_prices.max())
        lo_52 = float(close_prices.min())
        # Hoe ver van de top in % (0% = op de top, 100% = op de bodem)
        dist_from_high = ((hi_52 - current_price) / (hi_52 - lo_52)) * 100 if hi_52 != lo_52 else 0
        
        # 3. Dividend & Naam
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        naam = info.get('longName', ticker)
        raw_div = info.get('dividendYield', 0) or 0
        div = float(raw_div) * 100 if float(raw_div) < 1 else float(raw_div)
        if div > 25: div = div / 100 
        
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Bedrijf": naam,
            "Ticker": ticker, 
            "Prijs": round(current_price, 2),
            "RSI": round(float(rsi), 1), 
            "Score": round(float(score), 1),
            "Afstand Top %": round(dist_from_high, 1),
            "Div %": round(float(div), 2)
        }
    except: return None

# --- 3. SIDEBAR & DATA ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    watch_input = st.text_area("Watchlist:", "ASML.AS, KO, PG, O, ABBV, SHEL.AS, MO, AD.AS, AAPL, MSFT, GOOGL")
    port_input = st.text_area("Mijn Bezit:", "KO, ASML.AS")

st.title("🚀 Holy Grail Dashboard 2026")

tickers_w = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in port_input.split(",") if t.strip()]

results_w, results_p = [], []
status = st.empty()

with st.spinner('Analyseren...'):
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
status.empty()

# --- 4. LAYOUT ---
if results_w or results_p:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.header("🔍 Scanner")
        df_w = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
        # We voegen kleur toe: Afstand Top (Groen = ver van top/goedkoop, Rood = dichtbij top)
        st.dataframe(
            df_w.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=35, vmax=85)
            .background_gradient(cmap='RdYlGn_r', subset=['Afstand Top %'], vmin=0, vmax=50),
            use_container_width=True
        )
        st.caption("ℹ️ **Afstand Top %**: 0% betekent het aandeel staat op zijn hoogste prijs in 52 weken.")

    with c2:
        st.header("⚡ Signalen")
        for r in results_w:
            s, dist = r['Score'], r['Afstand Top %']
            # Slimme koop: Hoge score én niet op de allerhoogste prijs (afstand > 5%)
            if s >= 88 and dist > 5:
                st.success(f"💎 **KOOP KANS**: {r['Ticker']} (Score: {s})")
                stuur_alert_mail(r['Bedrijf'], r['Ticker'], s, r['RSI'], "OPTIMALE KOOP")
            elif s >= 88 and dist <= 5:
                st.info(f"🚀 **UITBRAAK?**: {r['Ticker']} op recordhoogte. Pas op.")
        
        st.divider()
        for r in results_p:
            if r['RSI'] >= 75:
                st.warning(f"🔥 **VERKOOP**: {r['Ticker']} (Oververhit)")

# --- 5. TAX ---
st.divider()
col_t1, col_t2 = st.columns(2)
with col_t1:
    st.header("💰 Tax Calculator 2026")
    vermogen = st.number_input("Totaal Vermogen (€):", value=120000)
    vrijstelling = 114000 # Partner-route
    taks = max(0, vermogen - vrijstelling) * 0.0212
    st.metric("Box 3 Belasting", f"€{taks:,.0f}")
