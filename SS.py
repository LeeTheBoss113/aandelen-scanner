import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & FUNCTIES ---
st.set_page_config(page_title="Ultimate Score Scanner 2026", layout="wide")

def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        # RSI 14 dagen
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        return {
            "Ticker": ticker,
            "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2),
            "Div %": round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            "Sector": info.get('sector', 'Onbekend'),
            "Score": round((100 - rsi) + ((info.get('dividendYield', 0) * 100 or 0) * 5), 2)
        }
    except:
        return None

def stuur_alert_mail(ticker, rsi, advies):
    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        msg = MIMEText(f"🚨 ALERT: {ticker}\nAdvies: {advies}\nRSI: {rsi:.2f}")
        msg['Subject'] = f"Scanner Alert: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        return True
    except: return False

# --- 2. HEADER & TEST OPTIE ---
st.title("🚀 Ultimate Score Scanner 2026")
with st.sidebar:
    if st.button("📧 Stuur Test Mail"):
        if stuur_alert_mail("TEST", 0, "TEST"): st.success("Verstuurd!")
        else: st.error("Check Secrets!")

# --- 3. HORIZONTALE LAYOUT (AUTO-LOAD) ---
col_left, col_right = st.columns(2)

# LINKER KANT: SCANNER
with col_left:
    st.header("🔍 Markt Scanner")
    watch_input = st.text_input("Tickers om te volgen:", "ASML.AS, KO, PG, JNJ, TSLA", key="scan_in")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data:
            results.append(data)
            if data['RSI'] < 30: stuur_alert_mail(t, data['RSI'], "KOOPKANS")
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df.sort_values(by="Score", ascending=False), use_container_width=True)

# RECHTER KANT: PORTFOLIO & RISICO
with col_right:
    st.header("⚖️ Portfolio Monitor")
    port_input = st.text_input("Je huidige aandelen:", "KO, ASML.AS", key="port_in")
    mijn_tickers = [t.strip().upper() for t in port_input.split(",")]
    
    p_results = []
    for t in mijn_tickers:
        d = scan_aandeel(t)
        if d: p_results.append(d)
    
    if p_results:
        df_p = pd.DataFrame(p_results)
        # Sector spreiding
        sector_counts = df_p['Sector'].value_counts()
        st.bar_chart(sector_counts)
        
        # Beknopte status weergave
        for _, row in df_p.iterrows():
            kleur = "🟢" if 35 < row['RSI'] < 65 else "💎" if row['RSI'] <= 35 else "⚠️"
            st.write(f"{kleur} **{row['Ticker']}**: RSI {row['RSI']} ({row['Sector']})")
        
        # Risico waarschuwing
        for sector, count in sector_counts.items():
            if (count / len(df_p)) > 0.4:
                st.warning(f"Spreidingsrisico in **{sector}**!")
