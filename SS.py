import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# VUL HIER JE GEGEVENS IN
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
    try:
        vandaag = str(date.today())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                if f.read().strip() == vandaag:
                    return
        
        inhoud = f"Holy Grail Scanner Update ({vandaag}):\n\n"
        for sb in strong_buys:
            inhoud += f"💎 {sb['Ticker']} | Score: {sb['Score']} | Trend: {sb['Trend1J']}\n"
        
        msg = MIMEText(inhoud)
        msg['Subject'] = f"🎯 Holy Grail Alert: {len(strong_buys)} Strong Buys"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        with open(LOG_FILE, "w") as f:
            f.write(vandaag)
    except:
        pass

# --- 4. SCANNER LOGICA ---
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
        
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)).iloc[-1]))
        hi = float(close.tail(252).max()) 
        dist_top = ((hi - curr) / hi) * 100
        
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma_252: score += 10
        if curr > sma_63: score += 5
        
        status = "⚖️ Hold"
        if score > 100 and curr > sma_252: status = "💎 STRONG BUY"
        elif score > 80: status = "✅ Buy"
        elif rsi > 75: status = "🔥 SELL"
            
        return {
            "Sector": sector, "Ticker": ticker, "Score": round(float(score), 1),
            "Prijs": round(float(curr), 2), "Status": status,
            "Trend3M": "✅" if curr > sma_63 else "❌",
            "Trend1J": "✅" if curr > sma_252 else "❌"
        }
    except:
        return None

# --- 5. UI & SORTERING ---
st.title("🎯 Holy Grail: Sector Dashboard")

all_results = []
ticker_items = [(t, s) for s, ts in SECTOREN.items() for t in ts]
progress_bar = st.progress(0)

for i, (t, s) in enumerate(ticker_items):
    res = scan_aandeel(t, s)
    if res:
        all_results.append(res)
    progress_bar.progress((i + 1) / len(ticker_items))

progress_bar.empty()

if all_results:
    # --- DE FIX VOOR DE ATTRIBUTEERROR ---
    df_all = pd.DataFrame(all_results).sort_values(by="Score", ascending=False).reset_index(drop=True)
    
    # Mail op de achtergrond
    strong_buys = [r for r in all_results if r["Status"] == "💎 STRONG BUY"]
    if strong_buys:
        stuur_dagelijkse_mail(strong_buys)

    col1, col2 = st.columns([1.2, 1.3])

    with col1:
        st.subheader("📊 Volledige Lijst (Strong Buy Bovenaan)")
        st.dataframe(df_all, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("🏆 Sector Favorieten")
        for sec in SECTOREN.keys():
            sec_df = df_all[df_all['Sector'] == sec].head(3)
            if not sec_df.empty:
                st.markdown(f"#### {sec}")
                card_cols = st.columns(len(sec_df))
                for idx, row in enumerate(sec_df.itertuples()):
                    with card_cols[idx]:
                        with st.container(border=True):
                            st.write(f"**{row.Ticker}**")
                            st.metric("Score", f"{row.Score}")
                            st.write(f"{row.Trend3
