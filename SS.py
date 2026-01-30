import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & FUNCTIES ---
def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty:
            return None
        
        # RSI Berekening (14 dagen)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Fundamentele Data
        info = stock.info
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        sector = info.get('sector', 'Onbekende Sector')
        prijs = hist['Close'].iloc[-1]
        
        # Score-berekening (Hoe lager RSI en hoe hoger Div, hoe beter)
        score = (100 - rsi) + (div * 5)
        
        return {
            "Ticker": ticker,
            "Prijs": round(prijs, 2),
            "RSI": round(rsi, 2),
            "Dividend %": round(div, 2),
            "Sector": sector,
            "Score": round(score, 2)
        }
    except:
        return None

def stuur_alert_mail(ticker, rsi, advies):
    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        msg = MIMEText(f"🚨 ALERT voor {ticker}\n\nAdvies: {advies}\nRSI: {rsi:.2f}\n\nCheck je Trading 212 app.")
        msg['Subject'] = f"Aandelen Scanner Alert: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        return True
    except:
        return False

# --- 2. APP LAYOUT ---
st.set_page_config(page_title="Ultimate Score Scanner 2026", layout="wide")
st.title("🚀 Ultimate Score Scanner 2026")

# Maak twee kolommen aan voor een horizontale layout
kolom_links, kolom_rechts = st.columns(2)

# --- LINKER KOLOM: DE SCANNER ---
with kolom_links:
    st.header("🔍 Markt Scanner")
    watchlist_input = st.text_input("Scanner (tickers + komma)", "ASML.AS, KO, PG, JNJ, TSLA", key="scan_in")
    
    if st.button("🚀 Start Analyse", use_container_width=True):
        results = []
        for t in [t.strip().upper() for t in watchlist_input.split(",")]:
            data = scan_aandeel(t)
            if data:
                results.append(data)
                # Mail Triggers
                if data['RSI'] < 30: stuur_alert_mail(t, data['RSI'], "KOOPKANS")
        
        if results:
            df = pd.DataFrame(results)
            st.dataframe(df.sort_values(by="Score", ascending=False))

# --- RECHTER KOLOM: PORTFOLIO & RISICO ---
with kolom_rechts:
    st.header("⚖️ Portfolio Monitor")
    portfolio_input = st.text_input("Mijn bezit (tickers + komma)", "KO, ASML.AS", key="port_in")
    
    if st.button("📊 Check Mijn Status", use_container_width=True):
        p_results = []
        for t in [t.strip().upper() for t in portfolio_input.split(",")]:
            d = scan_aandeel(t)
            if d:
                p_results.append(d)
        
        if p_results:
            df_p = pd.DataFrame(p_results)
            # Sector Grafiek
            st.bar_chart(df_p['Sector'].value_counts())
            # Beknopt statuslijstje
            for _, row in df_p.iterrows():
                st.write(f"**{row['Ticker']}**: RSI {row['RSI']} | {row['Sector']}")
