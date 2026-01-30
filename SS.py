import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & EMAIL FUNCTIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

def stuur_alert_mail(ticker, score, rsi):
    try:
        # Haal gegevens uit Streamlit Secrets
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        msg = MIMEText(f"🚀 HOLY GRAIL ALERT!\n\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nDit aandeel voldoet aan je koop-criteria. Check je dashboard!")
        msg['Subject'] = f"💎 Holy Grail Koopkans: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        return True
    except:
        return False

def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = (info.get('dividendYield', 0) or 0) * 100
        
        # HOLY GRAIL LOGICA
        rsi_factor = 100 - rsi
        if rsi > 70: rsi_factor -= 30 
        if rsi < 35: rsi_factor += 25  
        holy_grail_score = rsi_factor + (div * 3)
        
        return {
            "Ticker": ticker, "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2), "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), "Score": round(holy_grail_score, 2)
        }
    except: return None

# --- 2. DASHBOARD LAYOUT (4 KOLOMMEN) ---
st.title("🚀 Holy Grail Portfolio Dashboard 2026")

# TEST KNOP IN SIDEBAR
with st.sidebar:
    st.header("Systeem")
    if st.button("📧 Test Email Verbinding"):
        if stuur_alert_mail("TEST", "N.V.T.", "N.V.T."):
            st.success("Testmail verzonden!")
        else:
            st.error("Email mislukt. Check je Secrets.")

c1, c2, c3, c4 = st.columns([1.3, 0.7, 1, 1])

with c1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO, V, AAPL", key="w1")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data:
            results.append(data)
    
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        # Styling heatmap
        styled_df = df_all[['Ticker', 'RSI', 'Div %', 'Score']].style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=40, vmax=100)
        st.dataframe(styled_df, use_container_width=True)

# --- KOLOM 2: HET ACTIE-CENTRUM ---
with col2:
    st.header("⚡ Actie-Signalen")
    
    # 1. KOOP-SIGNALEN (Watchlist)
    st.subheader("💎 Buy Alerts")
    grails = [r for r in results if r['Score'] >= 85]
    if grails:
        for g in grails:
            st.success(f"**KOOP: {g['Ticker']}**\nScore: {g['Score']} (RSI: {g['RSI']})")
    else:
        st.info("Geen Holy Grails gevonden.")

    st.divider()

    # 2. VERKOOP-SIGNALEN (Eigen Portfolio)
    st.subheader("🔥 Sell Alerts")
    if p_res:
        sells = [r for r in p_res if r['RSI'] >= 70]
        if sells:
            for s in sells:
                st.warning(f"**VERKOOP: {s['Ticker']}**\nRSI: {s['RSI']}\n\n*Winst pakken?*")
                # Optioneel: Mail sturen bij verkoop-signaal
                # stuur_alert_mail(s['Ticker'], "N.V.T.", s['RSI']) 
        else:
            st.write("Geen aandelen oververhit.")
    else:
        st.write("Vul je bezit in in kolom 3.")

with c3:
    st.header("⚖️ Portfolio")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p1")
    p_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_res = [scan_aandeel(t) for t in p_tickers if scan_aandeel(t)]
    if p_res:
        for r in p_res:
            label = "🔥 VERKOOP?" if r['RSI'] > 70 else "🛡️ HOLD"
            st.write(f"{label} **{r['Ticker']}** (RSI: {r['RSI']})")
        st.bar_chart(pd.DataFrame(p_res)['Sector'].value_counts())

with c4:
    st.header("💰 Tax Benefit")
    vermogen = st.number_input("Totaal Vermogen (€):", value=100000)
    belasting = max(0, vermogen - 57000) * 0.021
    st.metric("Besparing p/j", f"€{belasting:,.0f}")
    st.write(f"Maandelijkse extra cash: **€{belasting/12:,.2f}**")

