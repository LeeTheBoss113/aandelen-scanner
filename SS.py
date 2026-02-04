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

# --- SIDEBAR VOOR INSTELLINGEN & MAIL ---
st.sidebar.title("📧 Mail Instellingen")
st.sidebar.info("Gebruik een Google 'App Password' voor de verbinding.")
GMAIL_USER = st.sidebar.text_input("Je Gmail adres", value="")
GMAIL_PASSWORD = st.sidebar.text_input("App-Wachtwoord (16 letters)", type="password")
SEND_TO = st.sidebar.text_input("Ontvanger adres", value="")

def stuur_mail(ticker, advies, div, rsi, is_test=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        
        if is_test:
            msg['Subject'] = "🧪 TEST: Scanner Mail Systeem"
            body = "Gefeliciteerd! Je mail-verbinding werkt. De scanner kan je nu notificaties sturen bij koopsignalen."
        else:
            msg['Subject'] = f"🚀 ACTIE NODIG: {ticker} is {advies}"
            body = f"De scanner heeft een kans gevonden!\n\nAandeel: {ticker}\nStatus: {advies}\nDividend: {div}%\nRSI: {rsi}\n\nCheck je dashboard voor meer details."
            
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")
        return False

# De Testknop
if st.sidebar.button("Stuur Test Mail"):
    if GMAIL_USER and GMAIL_PASSWORD:
        if stuur_mail("TEST", "TEST", 0, 0, is_test=True):
            st.sidebar.success("Test mail verzonden! Check je inbox.")
    else:
        st.sidebar.warning("Vul eerst je Gmail en App-Wachtwoord in.")

# --- HOOFDPROGRAMMA ---
st.title(f"🛡️ Dividend Trader Dashboard (Update: {time.strftime('%H:%M:%S')})")

# De 50 Tickers (Mix van Aristocraten & Groei)
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

# Verwerking van de lijst
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
        
        # MIX STRATEGIE LOGICA (Veilig + Actief)
        if trend_1y == "✅" and trend_6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
        elif trend_1y == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1y == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym, 
            "Sector": symbols_dict[sym], 
            "Advies": advies,
            "Div %": round(div, 2), 
            "RSI": round(rsi, 1), 
            "6m": trend_6m, 
            "1j": trend_1y, 
            "Beta": round(beta, 2)
        })
    progress_bar.progress((i + 1) / len(symbols))

# Weergave in de App
if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    
    def color_trade(val):
        if "KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.4)'
        if "WINST" in val: return 'background-color: rgba(0, 123, 255, 0.4)'
        if "VERMIJDEN" in val: return 'background-color: rgba(220, 53, 69, 0.2)'
        return ''

    st.subheader(f"📊 Marktoverzicht ({len(df_final)} aandelen)")
    st.dataframe(df_final.style.applymap(color_trade, subset=['Advies']), use_container_width=True)

    # Automatische verversing (elke 15 minuten voor de 'mix' strategie)
    time.sleep(900)
    st.rerun()
