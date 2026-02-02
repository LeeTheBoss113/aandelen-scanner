import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & MAIL SETTINGS ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# TIP: Gebruik Streamlit Secrets voor je wachtwoord!
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord"
EMAIL_RECEIVER = "ontvanger-email@gmail.com"

def stuur_mail(ticker, score, status):
    msg = MIMEText(f"Holy Grail Signaal: {ticker} heeft status {status} met een score van {score}!")
    msg['Subject'] = f"🎯 SCANNER ALERT: {ticker}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 252:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])

        # TRENDS
        sma_63 = close.rolling(window=63).mean().iloc[-1]
        sma_252 = close.rolling(window=252).mean().iloc[-1]
        is_above_3m = bool(curr > sma_63)
        is_above_1y = bool(curr > sma_252)
        
        # RSI & KORTING
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        hi = float(close.tail(252).max()) 
        dist_top = ((hi - curr) / hi) * 100
        
        # SCORE
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if is_above_1y: score += 10
        if is_above_3m: score += 5
        
        # STATUS & MAIL TRIGGER
        if score > 100 and is_above_1y: 
            status = "💎 STRONG BUY"
            # Schakel dit in als je echt mails wilt ontvangen:
            # stuur_mail(ticker, round(score, 1), status) 
        elif score > 80: status = "✅ Buy"
        elif rsi > 75 or (curr < sma_252 and dist_top < 2): status = "🔥 SELL"
        else: status = "⚖️ Hold"
        
        return {
            "Sector": sector, "Ticker": ticker, "Score": round(float(score), 1),
            "RSI": round(float(rsi), 1), "Korting": round(float(dist_top), 1),
            "Prijs": round(float(curr), 2), 
            "Boven_3M": "✅" if is_above_3m else "❌",
            "Boven_1J": "✅" if is_above_1y else "❌",
            "Status": status
        }
    except:
        return None

# --- 4. UI & LOOP (Hetzelfde als voorheen) ---
st.title("🎯 Holy Grail: Sector Spread Dashboard")

all_results = []
ticker_items = [(t, s) for s, ts in SECTOREN.items() for t in ts]
progress_bar = st.progress(0)

for i, (t, s) in enumerate(ticker_items):
    res = scan_aandeel(t, s)
    if res: all_results.append(res)
    progress_bar.progress((i + 1) / len(ticker_items))

if all_results:
    df_all = pd.DataFrame(all_results).sort_values("Score", ascending=False)
    col1, col2 = st.columns([1.2, 1.3])

    with col1:
        st.subheader("📊 Marktlijst")
        st.dataframe(df_all, hide_index=True)

    with col2:
        st.subheader("🏆 Sector Favorieten")
        for sector_naam in SECTOREN.keys():
            st.markdown(f"#### {sector_naam}")
            sec_df = df_all[df_all['Sector'] == sector_naam].head(3)
            cols = st.columns(3)
            for idx, row in enumerate(sec_df.itertuples()):
                with cols[idx]:
                    with st.container(border=True):
                        st.metric(row.Ticker, f"{row.Score} Ptn")
                        st.write(f"3M:{row.Boven_3M} 1J:{row.Boven_1J}")
                        st.caption(row.Status)
