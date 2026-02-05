import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import time

# 1. Pagina instellingen
st.set_page_config(page_title="Scanner", layout="wide")

# 2. Titel en Tijd (zonder f-strings om fouten te voorkomen)
st.title("🛡️ Dividend Trader")
nu_tijd = time.strftime('%H:%M:%S')
st.write("Laatste update om:", nu_tijd)

# 3. De Lijst met 50 Tickers
tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=600)
def get_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0
        info = t.info
        div = (info.get('dividendYield', 0) or 0) * 100
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div
    except:
        return None, 0

# 4. Analyse Loop
rows = []
bar = st.progress(0)

for i, sym in enumerate(tickers):
    df, div = get_data(sym)
    if df is not None and len(df) > 20:
        p = df['Close'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        m1y = df['Close'].mean()
        m6m = df['Close'].tail(126).mean()
        
        t1y = "OK" if p > m1y else "X"
        t6m = "OK" if p > m6m else "X"
        
        # Simpele Advies Logica
        if t1y == "OK" and t6m == "OK" and rsi < 45:
            adv = "KOOP"
        elif t1y == "OK" and rsi > 70:
            adv = "WINST"
        elif t1y == "OK":
            adv = "HOLD"
        else:
            adv = "NEGEER"

        rows.append({
            "Ticker": sym, 
            "Status": adv, 
            "Dividend%": round(div, 2),
            "RSI": round(rsi, 1), 
            "6m": t6m, 
            "1j": t1y
        })
    bar.progress((i + 1) / len(tickers))

# 5. Tabel tonen
if rows:
    res = pd.DataFrame(rows).sort_values("Dividend%", ascending=False)
    st.dataframe(res, use_container_width=True, height=800)

# 6. Herladen
time.sleep(900)
st.rerun()
