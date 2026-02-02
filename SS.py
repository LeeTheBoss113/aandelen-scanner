import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

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
        inhoud += f"💎 {sb['Ticker']} | Score: {sb['Score']} | Prijs: €{sb['Prijs']}\n"
    
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
        st.sidebar.success("Dagelijkse mail verzonden!")
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")

# --- 4. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        # Haal data op (2 jaar nodig voor SMA 252)
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 252:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        
        # Trends berekenen
        sma_63 = close.rolling(window=63).mean().iloc[-1]
        sma_252 = close.rolling(window=252).mean().iloc[-1]
        
        # RSI (14)
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)).iloc[-1]))
        
        # Jaarlijkse top en korting
        hi = float(close.tail(252).max()) 
        dist_top = ((hi - curr) / hi) * 100
        
        # Score bepaling
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma_252: score += 10
        if curr > sma_63: score += 5
        
        # Status
        if score > 100 and curr > sma_252:
            status = "💎 STRONG BUY"
        elif score > 80:
            status = "✅ Buy"
        elif rsi > 75:
            status = "🔥 SELL"
        else:
            status = "⚖️ Hold"
        
        return {
            "Sector": sector, 
            "Ticker": ticker, 
            "Score": round(float(score), 1),
            "Prijs": round(float(curr), 2), 
            "Status": status,
            "Trend_3M": "✅" if curr > sma_63 else "❌",
            "Trend_1J": "✅" if curr > sma_252 else "❌"
        }
    except Exception as e:
        # Dit is het blok dat Python miste
        return None

# --- 5. EXECUTIE ---
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
    # Sorteren: Hoogste score (Strong Buy) bovenaan
    df_all = pd.DataFrame(all_results).sort_values(by="Score", ascending=False)
    
    # Mail sturen
    strong_buys = [r for r in all_results if r["Status"] == "💎 STRONG BUY"]
    if strong_buys:
        stuur_dagelijkse_mail(strong_buys)

    col1, col2 = st.columns([1.2, 1.3])
    
    with col1:
        st.subheader("📊 Marktlijst")
        st.dataframe(df_all, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("🏆 Sector Favorieten")
        for sector in SECTOREN.keys():
            st.markdown(f"#### {sector}")
            sec_df = df_all[df_all['Sector'] == sector].head(3)
            cols = st.columns(3)
            for idx, row in enumerate(sec_df.itertuples()):
                with cols[idx]:
                    with st.container(border=True):
                        st.metric(row.Ticker, f"{row.Score} Ptn")
                        st.write(f"3M:{row.Trend_3M} 1J:{row.Trend_1J}")
                        st.caption(row.Status)
