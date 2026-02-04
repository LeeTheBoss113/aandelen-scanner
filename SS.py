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
sleutels = list(st.secrets.keys())

# Controleer of de benodigde secrets aanwezig zijn
check_user = "GMAIL_USER" in sleutels
check_pass = "GMAIL_PASSWORD" in sleutels

if check_user:
    st.sidebar.success("✅ GMAIL_USER geladen")
else:
    st.sidebar.error("❌ GMAIL_USER mist in Secrets")

if check_pass:
    st.sidebar.success("✅ GMAIL_PASSWORD geladen")
else:
    st.sidebar.error("❌ GMAIL_PASSWORD mist in Secrets")

# Gegevens toewijzen uit de kluis
GMAIL_USER = st.secrets.get("GMAIL_USER")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD")
SEND_TO = st.secrets.get("SEND_TO", GMAIL_USER) # Fallback naar user als send_to mist

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies, div, rsi, is_test=False):
    if not check_user or not check_pass:
        st.error("Mail versturen afgebroken: Secrets niet correct geconfigureerd.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        
        if is_test:
            msg['Subject'] = "🧪 TEST: Dividend Scanner Verbinding"
            body = "Gefeliciteerd! De verbinding met de Gmail-server via de Secrets is gelukt."
        else:
            msg['Subject'] = f"🚀 ACTIE NODIG: {ticker} is {advies}"
            body = f"Kans gevonden!\n\nAandeel: {ticker}\nStatus: {advies}\nDividend: {div}%\nRSI: {rsi}\n\nCheck je dashboard."
            
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"⚠️ Mail fout: {e}")
        return False

# Testknop in Sidebar
if st.sidebar.button("Stuur Test Mail"):
    with st.spinner("Bezig met verzenden..."):
        if stuur_mail("TEST", "TEST", 0, 0, is_test=True):
            st.sidebar.success("📩 Test mail verzonden!")

# --- HOOFDPROGRAMMA ---
st.title(f"🛡️ Dividend Trader Dashboard")
st.caption(f"Laatste update: {time.strftime('%H:%M:%S')} - Ververst elke 15 minuten")

# De 50 Tickers
symbols_dict = {
    'KO': 'Consumptie', 'PEP': 'Consumptie', 'JNJ': 'Healthcare', 'O': 'Vastgoed', 
    'PG': 'Consumptie', 'ABBV': 'Healthcare', 'CVX': 'Energie', 'XOM': 'Energie',
    'MMM': 'Industrie', 'T': 'Telecom', 'VZ': 'Telecom', 'WMT': 'Retail', 
    'LOW': 'Retail', 'TGT': 'Retail', 'ABT': 'Healthcare', 'MCD': 'Horeca',
    'ADBE': 'Tech', 'MSFT': 'Tech', 'AAPL': 'Tech', 'IBM': 'Tech',
    'HD': 'Retail', 'COST': 'Retail', 'LLY': 'Healthcare', 'PFE': 'Healthcare',
    'MRK': 'Healthcare', 'DHR': 'Industrie', 'UNH': 'Healthcare', 'BMY': 'Healthcare',
    'AMGN': 'Healthcare', 'SBUX': 'Horeca', 'CAT': 'Industrie', 'DE': 'Industrie',
    'HON': 'Industrie', 'UPS': 'Logistiek', 'FDX': 'Logistiek', 'NEE': 'Utility',
    'SO': 'Utility', 'D': 'Utility', 'DUK': 'Utility', 'PM': 'Tabak',
    'MO': 'Tabak', 'SCHW': 'Finance', 'BLK': 'Finance', 'SPGI': 'Finance',
    'V': 'Finance', 'MA': 'Finance', 'AVGO': 'Tech', 'TXN': 'Tech', 'NVDA': 'Tech'
}

@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0, 1.0
        
        try:
            info = t.info
            div = (info.get('dividendYield', 0) or 0) * 100
            beta = info.get('beta', 1.0) or 1.0
        except:
            div, beta = 0, 1.0
            
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div, beta
    except:
        return None, 0, 1.0

# Verwerking
data_rows = []
progress_bar = st.progress(0)
symbols = list(symbols_dict.keys())

for i, sym in enumerate(symbols):
    df, div, beta = get_stock_data(sym)
    if df is not None:
        closes = df['Close'].values.flatten()
        current_price = float(closes[-1])
        rsi = float(df['RSI'].fillna(50).values[-1])
        
        # Trend Checks
        ma_6m = float(np.mean(closes[-126:])) if len(closes) >= 126 else float(np.mean(closes))
        ma_1y = float(np.mean(closes))
        trend_6m = "✅" if current_price > ma_6m else "❌"
        trend_1y = "✅" if current_price > ma_1y else "❌"
        
        # MIX LOGICA
        if trend_1y == "✅" and trend_6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
        elif trend_1y == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1y == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym, "Sector": symbols_dict[sym], "Advies": advies,
            "Div %": round(div, 2), "RSI": round(rsi, 1), 
            "6m": trend_6m, "1j": trend_1y, "Beta": round(beta, 2)
        })
    progress_bar.progress((i + 1) / len(symbols))

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    
    def style_advies(val):
        if "KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.4)'
        if "WINST" in val: return 'background-color: rgba(0, 123, 255, 0.4)'
        return ''

    st.dataframe(df_final.style.applymap(style_advies, subset=['Advies']), use_container_width=True)

# Automatische verversing (elke 15 minuten)
time.sleep(900)
st.rerun()
