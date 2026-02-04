import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- VEILIGHEID: SECRETS LADEN ---
try:
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_PASSWORD"]
    SEND_TO = st.secrets["SEND_TO"]
except:
    st.error("Secrets niet gevonden! Voeg GMAIL_USER, GMAIL_PASSWORD en SEND_TO toe aan Streamlit Secrets.")
    st.stop()

# 1. Pagina instellingen
st.set_page_config(page_title="Safe Dividend Trader", layout="wide")

def stuur_mail(ticker, advies, div, rsi, is_test=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        
        if is_test:
            msg['Subject'] = "🧪 TEST: Scanner Mail Systeem"
            body = "Je mail-verbinding via Secrets werkt perfect!"
        else:
            msg['Subject'] = f"🚀 ACTIE: {ticker} is {advies}"
            body = f"Kans gevonden!\nAandeel: {ticker}\nStatus: {advies}\nDiv: {div}%\nRSI: {rsi}"
            
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail fout: {e}")
        return False

# --- UI ELEMENTEN ---
st.title(f"🛡️ Dividend Trader Pro (Update: {time.strftime('%H:%M:%S')})")

if st.button("🧪 Test Mail Verbinding"):
    if stuur_mail("TEST", "TEST", 0, 0, is_test=True):
        st.success("Test mail verzonden via Secrets!")

# 2. De 50 Tickers (Voorbeeld set)
symbols_dict = {
    'KO': 'Consumptie', 'PEP': 'Consumptie', 'JNJ': 'Healthcare', 'O': 'Vastgoed', 
    'PG': 'Consumptie', 'ABBV': 'Healthcare', 'CVX': 'Energie', 'XOM': 'Energie',
    'MSFT': 'Tech', 'AAPL': 'Tech', 'COST': 'Retail', 'MCD': 'Horeca'
    # Vul hier aan tot 50...
}

@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0
        df['RSI'] = ta.rsi(df['Close'], length=14)
        div = (t.info.get('dividendYield', 0) or 0) * 100
        return df, div
    except: return None, 0

# 3. Analyse & Display
data_rows = []
symbols = list(symbols_dict.keys())
progress = st.progress(0)

for i, sym in enumerate(symbols):
    df, div = get_stock_data(sym)
    if df is not None:
        closes = df['Close'].values.flatten()
        rsi = float(df['RSI'].fillna(50).values[-1])
        ma_1y = float(np.mean(closes))
        ma_6m = float(np.mean(closes[-126:]))
        
        trend_1j = "✅" if closes[-1] > ma_1y else "❌"
        trend_6m = "✅" if closes[-1] > ma_6m else "❌"

        if trend_1j == "✅" and trend_6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
        elif trend_1j == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1j == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym, "Advies": advies, "Div %": round(div, 2), 
            "RSI": round(rsi, 1), "6m": trend_6m, "1j": trend_1y
        })
    progress.progress((i + 1) / len(symbols))

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    st.dataframe(df_final, use_container_width=True)

# Auto-refresh
time.sleep(900)
st.rerun()
