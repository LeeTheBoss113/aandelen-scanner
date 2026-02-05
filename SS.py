import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

st.set_page_config(page_title="Scanner", layout="wide")
st.title("🛡️ Dividend Trader")

# Tijd zonder f-string
nu = time.strftime('%H:%M:%S')
st.write("Update:", nu)

# De 50 Tickers
t_list = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=600)
def get_data(s):
    try:
        t = yf.Ticker(s)
        d = t.history(period="1y")
        if d.empty: return None, 0
        dv = (t.info.get('dividendYield', 0) or 0) * 100
        d['RSI'] = ta.rsi(d['Close'], length=14)
        return d, dv
    except:
        return None, 0

res = []
p_bar = st.progress(0)

for i, s in enumerate(t_list):
    df, div = get_data(s)
    if df is not None and len(df) > 20:
        c = df['Close'].iloc[-1]
        r = df['RSI'].iloc[-1]
        m1 = df['Close'].mean()
        
        # Simpele status
        stat = "KOOP" if c > m1 and r < 45 else "HOLD"
        if c < m1: stat = "NEGEER"
        if r > 70: stat = "WINST"

        res.append({"Ticker": s, "Status": stat, "Div%": round(div, 2), "RSI": round(r, 1)})
    p_bar.progress((i + 1) / len(t_list))

if res:
    st.dataframe(pd.DataFrame(res).sort_values("Div%", ascending=False), use_container_width=True)

time.sleep(900)
st.rerun()
