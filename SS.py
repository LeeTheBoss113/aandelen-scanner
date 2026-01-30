import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. FUNCTIES ---
def scan_aandeel(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    if hist.empty:
        return None
    
    # RSI Berekening
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Dividend & Prijs
    info = stock.info
    div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
    prijs = hist['Close'].iloc[-1]
    
    # Kansen-Score
    score = (100 - rsi) + (div * 5)
    
    return {
        "Ticker": ticker,
        "Prijs": round(prijs, 2),
        "RSI": round(rsi, 2),
        "Dividend %": round(div, 2),
        "Kansen-Score": round(score, 2)
    }

def stuur_alert_mail(ticker, rsi, advies):
    try:
        afzender = st.secrets["email"]["user"]
        wachtwoord = st.secrets["email"]["password"]
        ontvanger = st.secrets["email"]["receiver"]
        msg = MIMEText(f"Actie voor {ticker}.\nRSI: {rsi:.2f}\nStatus: {advies}")
        msg['Subject'] = f"🚨 ALERT: {ticker} = {advies}"
        msg['From'] = afzender
        msg['To'] = ontvanger
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(afzender, wachtwoord)
            server.sendmail(afzender, ontvanger, msg.as_string())
        return True
    except:
        return False

# --- 2. DE APP LAYOUT ---
st.title("🚀 Ultimate Score Scanner 2026")

# Watchlist Scanner
watchlist = st.text_input("Scanner Watchlist (tickers met komma)", "ASML.AS, AAPL, KO, SHEL.AS")
tickers = [t.strip().upper() for t in watchlist.split(",")]

if st.button("Start Marktsurvey"):
    results = []
    progress = st.progress(0)
    for i, t in enumerate(tickers):
        res = scan_aandeel(t)
        if res:
            results.append(res)
            # Mail triggers
            if res['RSI'] < 30:
                stuur_alert_mail(t, res['RSI'], "KOOPKANS")
            elif res['RSI'] > 70:
                stuur_alert_mail(t, res['RSI'], "VERKOOPKANS")
        progress.progress((i + 1) / len(tickers))
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df.sort_values(by="Kansen-Score", ascending=False))

# --- 3. PORTFOLIO MONITOR (De verdwenen sectie) ---
st.divider()
st.header("📈 Portfolio Monitor")
mijn_aandelen = st.text_input("Aandelen in bezit", "ASML.AS, KO")
eigen_tickers = [t.strip().upper() for t in mijn_aandelen.split(",")]

if st.button("Check mijn Status"):
    portfolio_data = []
    for t in eigen_tickers:
        res = scan_aandeel(t)
        if res:
            if res['RSI'] > 70:
                res['Advies'] = "⚠️ VERKOPEN"
            elif res['RSI'] < 35:
                res['Advies'] = "💎 BIJKOPEN"
            else:
                res['Advies'] = "✅ HOLD"
            portfolio_data.append(res)
    
    if portfolio_data:
        st.table(pd.DataFrame(portfolio_data)[['Ticker', 'Prijs', 'RSI', 'Advies']])
