import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Pagina instellingen
st.set_page_config(page_title="Dividend Trader Pro", layout="wide")

# --- DIAGNOSE & SECRETS CHECK ---
st.sidebar.title("🔐 Systeem Status")
try:
    sleutels = list(st.secrets.keys())
except:
    sleutels = []

check_user = "GMAIL_USER" in sleutels
check_pass = "GMAIL_PASSWORD" in sleutels

if check_user: st.sidebar.success("✅ GMAIL_USER geladen")
else: st.sidebar.error("❌ GMAIL_USER mist")

if check_pass: st.sidebar.success("✅ GMAIL_PASSWORD geladen")
else: st.sidebar.error("❌ GMAIL_PASSWORD mist")

GMAIL_USER = st.secrets.get("GMAIL_USER")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD")
SEND_TO = st.secrets.get("SEND_TO", GMAIL_USER)

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies, div, rsi, is_test=False):
    if not (check_user and check_pass): return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = "🧪 TEST" if is_test else f"🚀 ACTIE: {ticker}"
        inhoud = "Verbinding werkt!" if is_test else f"Kans gevonden voor {ticker} ({advies})"
        msg.attach(MIMEText(inhoud, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Fout: {e}")
        return False

if st.sidebar.button("Stuur Test Mail"):
    if stuur_mail("TEST", "TEST", 0, 0, is_test=True):
        st.sidebar.success("📩 Verzonden!")

# --- HOOFDPROGRAMMA ---
st.title("🛡️ Dividend Trader Dashboard")
st.caption(f"Update: {time.strftime('%H:%M:%S')} - Ververst elke 15 min")

# 2. De 50 Tickers (In compact formaat om SyntaxErrors te vermijden)
symbols_dict = {
    'KO':'Consumptie','PEP':'Consumptie','JNJ':'Health','O':'Vastgoed','PG':'Consumptie',
    'ABBV':'Health','CVX':'Energie','XOM':'Energie','MMM':'Industrie','T':'Telecom',
    'VZ':'Telecom','WMT':'Retail','LOW':'Retail','TGT':'Retail','ABT':'Health',
    'MCD':'Horeca','ADBE':'Tech','MSFT':'Tech','AAPL':'Tech','IBM':'Tech',
    'HD':'Retail','COST':'Retail','LLY':'Health','PFE':'Health','MRK':'Health',
    'DHR':'Industrie','UNH':'Health','BMY':'Health','AMGN':'Health','SBUX':'Horeca',
    'CAT':'Industrie','DE':'Industrie','HON':'Industrie','UPS':'Logistiek','FDX':'Logistiek',
    'NEE':'Utility','SO':'Utility','D':'Utility','DUK':'Utility','PM':'Tabak',
    'MO':'Tabak','SCHW':'Finance','BLK':'Finance','SPGI':'Finance','V':'Finance',
    'MA':'Finance','AVGO':'Tech','TXN':'Tech','NVDA':'Tech','JPM':'Finance'
}

@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0, 1.0
        # Veilig ophalen van info
        info = t.info
        div = (info.get('dividendYield', 0) or 0) * 100
        beta = info.get('beta', 1.0) or 1.0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div, beta
    except:
        return None, 0, 1.0

# 3. Verwerking
data_rows = []
progress_bar = st.progress(0)
symbols = list(symbols_dict.keys())

for i, sym in enumerate(symbols):
    df, div, beta = get_stock_data(sym)
    if df is not None:
        closes = df['Close'].values.flatten()
        rsi = float(df['RSI'].fillna(50).values[-1])
        ma_6m = float(np.mean(closes[-126:])) if len(closes) >= 126 else float(np.mean(closes))
        ma_1y = float(np.mean(closes))
        
        trend_6m = "✅" if closes[-1] > ma_6m else "❌"
        trend_1y = "✅" if closes[-1] > ma_1y else "❌"
        
        if trend_1y == "✅" and trend_6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
        elif trend_1y == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1y == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym, "Advies": advies, "Div %": round(div, 2), 
            "RSI": round(rsi, 1), "6m": trend_6m, "1j": trend_1y, "Beta": round(beta, 2)
        })
    progress_bar.progress((i + 1) / len(symbols))

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    
    def style_advies(val):
        if "KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.4)'
        if "WINST" in val: return 'background-color: rgba(0, 123, 255, 0.4)'
        return ''

    st.dataframe(df_final.style.applymap(style_advies, subset=['Advies']), use_container_width=True)

# Auto-refresh
time.sleep(900)
st.rerun()
