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

# TEST-SECTIE IN DE SIDEBAR
with st.sidebar:
    st.header("⚙️ Instellingen")
    if st.button("📧 Test E-mail Verbinding"):
        if stuur_alert_mail("TEST", 0, "TEST-MODUS"):
            st.success("Test-mail verstuurd!")
        else:
            st.error("Mail mislukt. Check je Secrets.")

# --- 3. SECTIE 1: DE SCANNER ---
st.header("🔍 Markt Scanner")
watchlist_input = st.text_input("Vul tickers in (gescheiden door komma)", "ASML.AS, KO, PG, JNJ, TSLA, SHEL.AS")
tickers = [t.strip().upper() for t in watchlist_input.split(",")]

if st.button("🚀 Start Analyse"):
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data:
            results.append(data)
            # Mail Triggers
            if data['RSI'] < 30:
                stuur_alert_mail(t, data['RSI'], "KANS: ONDERGEWAARDEERD")
            elif data['RSI'] > 75:
                stuur_alert_mail(t, data['RSI'], "WAARSCHUWING: OVERGEKOCHT")
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df.sort_values(by="Score", ascending=False), use_container_width=True)

# --- 4. SECTIE 2: PORTFOLIO & RISICO SPREIDING ---
st.divider()
st.header("⚖️ Risico & Spreiding Monitor")
portfolio_input = st.text_input("Aandelen die je nu bezit", "KO, ASML.AS")
mijn_tickers = [t.strip().upper() for t in portfolio_input.split(",")]

if st.button("📊 Analyseer Mijn Spreiding"):
    p_results = []
    for t in mijn_tickers:
        d = scan_aandeel(t)
        if d:
            p_results.append(d)
    
    if p_results:
        df_p = pd.DataFrame(p_results)
        
        # Sectorverdeling
        sector_counts = df_p['Sector'].value_counts()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Verdeling per Sector:**")
            st.bar_chart(sector_counts)
        
        with col2:
            st.write("**Status Overzicht:**")
            for _, row in df_p.iterrows():
                status = "✅ HOLD"
                if row['RSI'] > 70: status = "⚠️ VERKOOPKANS"
                if row['RSI'] < 35: status = "💎 BIJKOOPKANS"
                st.write(f"{row['Ticker']}: {status} ({row['Sector']})")
        
        # Risico Waarschuwing
        for sector, count in sector_counts.items():
            perc = (count / len(df_p)) * 100
            if perc > 40:
                st.warning(f"🚨 Let op: {perc:.0f}% van je geld zit in de sector '{sector}'. Koop een aandeel in een andere sector om je risico te verlagen!")



