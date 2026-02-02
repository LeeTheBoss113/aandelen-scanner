import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib, os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" 
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 2. MAIL FUNCTIE ---
def stuur_mail(strong_buys):
    try:
        vandaag = str(date.today())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                if f.read().strip() == vandaag: return
        
        inhoud = "Holy Grail Alerts:\n\n"
        for s in strong_buys:
            line = f"💎 {s['Ticker']} | Score: {s['Score']}\n"
            inhoud += line
            
        msg = MIMEText(inhoud)
        msg['Subject'] = f"🎯 Scanner: {len(strong_buys)} Strong Buys"
        msg['From'], msg['To'] = EMAIL_SENDER, EMAIL_RECEIVER
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        
        with open(LOG_FILE, "w") as f: 
            f.write(vandaag)
    except: 
        pass

# --- 3. SCAN LOGICA ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or len(df) < 252: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        sma63 = close.rolling(63).mean().iloc[-1]
        sma252 = close.rolling(252).mean().iloc[-1]
        
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)).iloc[-1]))
        
        hi = float(close.tail(252).max())
        dist_top = ((hi - curr) / hi) * 100
        
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma252: score += 10
        if curr > sma63: score += 5
        
        status = "⚖️ Hold"
        if score > 100 and curr > sma252: 
            status = "💎 STRONG BUY"
        elif score > 80: 
            status = "✅ Buy"
        elif rsi > 75: 
            status = "🔥 SELL"
            
        # Resultaat opbouwen in kleine stapjes
        res = {"Sector": sector, "Ticker": ticker}
        res["Score"] = round(score, 1)
        res["Prijs"] = round(curr, 2)
        res["Status"] = status
        res["Trend3M"] = "✅" if curr > sma63 else "❌"
        res["Trend1J"] = "✅" if curr > sma252 else "❌"
        return res
    except: 
        return None

# --- 4. DASHBOARD ---
st.title("🎯 Holy Grail: Sector Dashboard")
all_res = []
ticker_items = [(t, s) for s, ts in SECTOREN.items() for t in ts]
pb = st.progress(0)

for i, (t, s) in enumerate(ticker_items):
    res = scan_aandeel(t, s)
    if res: all_res.append(res)
    pb.progress((i + 1) / len(ticker_items))
pb.empty()

if all_res:
    # SORTERING: ALLES OP SCORE
    df = pd.DataFrame(all_res)
    df = df.sort_values(by="Score", ascending=False)
    df = df.reset_index(drop=True)
    
    sb = [r for r in all_res if r["Status"] == "💎 STRONG BUY"]
    if sb: stuur_mail(sb)

    c1, c2 = st.columns([1.2, 1.3])
    with c1:
        st.subheader("📊 Marktlijst")
        st.dataframe(df, hide_index=True, use_container_width=True)
        
    with c2:
        st.subheader("🏆 Sector Top 3")
        for sec in SECTOREN.keys():
            sec_df = df[df['Sector'] == sec].head(3)
            if not sec_df.empty:
                st.markdown(f"#### {sec}")
                cols = st.columns(len(sec_df))
                for idx, row in enumerate(sec_df.itertuples()):
                    with cols[idx]:
                        with st.container(border=True):
                            st.write(f"**{row.Ticker}**")
                            st.metric("Score", f"{row.Score}")
                            st.write(f"3M:{row.Trend3M} | 1J:{row.Trend1J}")
                            st.caption(row.Status)
