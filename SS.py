import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATIE (Vul hier je gegevens in) ---
GMAIL_USER = "jouw-email@gmail.com"  # Je eigen Gmail
GMAIL_PASSWORD = "abcd efgh ijkl mnop"  # De 16 letters van Google App Password
SEND_TO = "jouw-email@gmail.com"  # Waar moet de mail heen?
# ----------------------------------------------

st.set_page_config(page_title="Dividend Trader Pro", layout="wide")
st.title("🛡️ Dividend Trader: Mix van Veiligheid & Actie")

# De 50 Tickers (Ingekort voor voorbeeld, maar je kunt aanvullen)
symbols_dict = {
    'KO': 'Coca-Cola', 'PEP': 'Pepsi', 'JNJ': 'Healthcare', 'O': 'Realty Income', 
    'PG': 'P&G', 'ABBV': 'AbbVie', 'MSFT': 'Microsoft', 'AAPL': 'Apple',
    'COST': 'Costco', 'MCD': 'McDonalds', 'WMT': 'Walmart' # Breid uit naar 50+
}

def stuur_mail(ticker, advies, div, rsi):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = f"🚀 ACTIE NODIG: {ticker} is {advies}"
        
        body = f"De scanner heeft een kans gevonden!\n\nAandeel: {ticker}\nStatus: {advies}\nDividend: {div}%\nRSI: {rsi}\n\nCheck je dashboard voor meer details."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

@st.cache_data(ttl=600)
def get_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        info = t.info
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, info
    except: return None, None

# Data verwerking
data_rows = []
for sym, sector in symbols_dict.items():
    df, info = get_data(sym)
    if df is not None:
        closes = df['Close'].values.flatten()
        current_price = float(closes[-1])
        rsi = float(df['RSI'].fillna(50).values[-1])
        ma_1y = float(np.mean(closes))
        trend_1j = "✅" if current_price > ma_1y else "❌"
        div = (info.get('dividendYield', 0) or 0) * 100
        
        # MIX STRATEGIE LOGICA
        if trend_1j == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
            # Optioneel: stuur_mail(sym, advies, round(div,2), round(rsi,1))
        elif trend_1j == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1j == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({"Ticker": sym, "Advies": advies, "Div %": round(div,2), "RSI": round(rsi,1), "1j Trend": trend_1j})

if data_rows:
    df_final = pd.DataFrame(data_rows)
    
    # Kleurfunctie voor de actieve handel
    def color_trade(val):
        if "KOPEN" in val: return 'background-color: #28a745'
        if "WINST" in val: return 'background-color: #007bff'
        return ''

    st.dataframe(df_final.style.applymap(color_trade, subset=['Advies']), use_container_width=True)

st.info("De mailfunctie staat in de code klaar. Vul je Gmail App-Password in om notificaties te ontvangen.")
