import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# Pas deze aan in Streamlit Secrets of hier (tussen aanhalingstekens)
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" 
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. MAIL FUNCTIE ---
def stuur_dagelijkse_mail(strong_buys):
    vandaag = str(date.today())
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            if f.read().strip() == vandaag:
                return

    inhoud = f"Holy Grail Scanner Update ({vandaag}):\n\n"
    for sb in strong_buys:
        inhoud += f"💎 {sb['Ticker']} | Score: {sb['Score']} | Status: {sb['Status']}\n"
    
    msg = MIMEText(inhoud)
    msg['Subject'] = f"🎯 Dagelijkse Strong Buys - {vandaag}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        with open(LOG_FILE, "w") as f:
            f.write(vandaag)
        st.sidebar.success("Daily Mail Sent!")
    except Exception as e:
        st.sidebar.error(f"Mail Error: {e}")

# --- 4. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or df.empty or len(df) < 252:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        sma_63 = close.rolling(63).mean().iloc[-1]
        sma_252 = close.rolling(252).mean().iloc[-1]
        
        # RSI
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)).iloc[-1]))
        
        # Korting
        hi = float(close.tail(252).max()) 
        dist_top = ((hi - curr) / hi) * 100
        
        # Score
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma_252: score += 10
        if curr > sma_63: score += 5
        
        # Status
        if score > 100 and curr > sma_252: status = "💎 STRONG BUY"
        elif score > 80: status = "✅ Buy"
        elif rsi > 75: status = "🔥 SELL"
        else: status = "⚖️ Hold"
        
        return {
            "Sector": sector, "Ticker": ticker, "Score": round(float(score), 1),
            "Prijs": round(float(curr), 2), "Status": status,
            "Trend3M": "✅" if curr > sma_63 else "❌",
            "Trend1J": "✅" if curr > sma_252 else "❌"
        }
    except Exception:
        return None

# --- 5. DASHBOARD UI ---
st.title("🎯 Holy Grail: Sector Dashboard")

all_results = []
ticker_items = [(t, s) for s, ts in SECTOREN.items() for t in ts]
progress_bar = st.progress(0)

for i, (t, s) in enumerate(ticker_items):
    res = scan_aandeel(t, s)
    if res:
        all_results.append(res)
    progress_bar.progress((i + 1) / len(ticker_items))

if all_results:
    # 1. Maak DataFrame en sorteer ALLES op score van hoog naar laag
    df_all = pd.DataFrame(all_results).sort_values(by="Score", ascending=False)
    
    # 2. Mail check
    strong_buys_list = [r for r in all_results if r["Status"] == "💎 STRONG BUY"]
    if strong_buys_list:
        stuur_dagelijkse_mail(strong_buys_list)

    col_left, col_right = st.columns([1.2, 1.3])

    with col_left:
        st.subheader("📊 Volledige Lijst (Besten bovenaan)")
        st.dataframe(df_all, hide_index=True, use_container_width=True)

    with col_right:
        st.subheader("🏆 Top Picks per Sector")
        for sec_name in SECTOREN.keys():
            st.markdown(f"### {sec_name}")
            # Filter de al gesorteerde lijst op de huidige sector
            sec_df = df_all[df_all['Sector'] == sec_name].head(3)
            
            c1, c2, c3 = st.columns(3)
            cols = [c1, c2, c3]
            
            for idx, row in enumerate(sec_df.itertuples()):
                with cols[idx]:
                    with st.container(border=True):
                        st.metric(row.Ticker, f"{row.Score} Ptn")
                        st.write(f"3M:{row.Trend3M} | 1J:{row.Trend1J}")
                        if "STRONG" in row.Status: st.success(row.Status)
                        elif "Buy" in row.Status: st.info(row.Status)
                        elif "SELL" in row.Status: st.error(row.Status)
                        else: st.warning(row.Status)
else:
    st.error("Data kon niet geladen worden.")
