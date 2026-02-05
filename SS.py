import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

st.set_page_config(page_title="Dividend Scanner Pro", layout="wide")
st.title("🛡️ Dividend Trader Dashboard")

# Update tijd
nu = time.strftime('%H:%M:%S')
st.write("Laatste update:", nu)

# De 50 Tickers
tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=3600)
def get_stock_info(s):
    try:
        t = yf.Ticker(s)
        hist = t.history(period="1y")
        if hist.empty: return None
        
        info = t.info
        return {
            "hist": hist,
            "div": (info.get('dividendYield', 0) or 0) * 100,
            "sector": info.get('sector', 'Onbekend'),
            "target": info.get('targetMeanPrice', None),
            "price": hist['Close'].iloc[-1]
        }
    except:
        return None

res = []
p_bar = st.progress(0)

for i, s in enumerate(tickers):
    data = get_stock_info(s)
    if data:
        df = data['hist']
        price = data['price']
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        m1y = df['Close'].mean()
        m6m = df['Close'].tail(126).mean()
        
        # Trend checks
        t1y = "✅" if price > m1y else "❌"
        t6m = "✅" if price > m6m else "❌"
        
        # Koersdoel berekening
        target = data['target']
        potentieel = round(((target - price) / price) * 100, 1) if target else 0
        
        # Advies Logica
        if t1y == "✅" and t6m == "✅" and rsi < 45:
            stat = "🌟 KOOP"
        elif t1y == "✅" and rsi > 70:
            stat = "💰 WINST"
        elif t1y == "✅":
            stat = "🟢 HOLD"
        else:
            stat = "🔴 VERMIJDEN"

        res.append({
            "Ticker": s,
            "Sector": data['sector'],
            "Status": stat,
            "Prijs": round(price, 2),
            "Koersdoel": target,
            "Potentieel %": potentieel,
            "Div %": round(data['div'], 2),
            "RSI": round(rsi, 1),
            "6m": t6m,
            "1j": t1y
        })
    p_bar.progress((i + 1) / len(tickers))

if res:
    df_final = pd.DataFrame(res).sort_values("Div %", ascending=False)
    
    # Styling functie
    def color_stat(val):
        if val == "🌟 KOOP": return 'background-color: #28a745; color: white'
        if val == "💰 WINST": return 'background-color: #007bff; color: white'
        if val == "🔴 VERMIJDEN": return 'color: #dc3545'
        return ''

    st.dataframe
