import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import time

# 1. Pagina instellingen
st.set_page_config(page_title="Dividend Trader Pro", layout="wide")

# --- UI ELEMENTEN ---
st.title("🛡️ Dividend Trader Dashboard")
st.markdown("""
**Strategie:**
* **Trend:** Is de huidige prijs hoger dan het gemiddelde van het afgelopen jaar (1j) en half jaar (6m)?
* **Timing (RSI):** We kopen in de dip (RSI < 45) en overwegen winst bij oververhitting (RSI > 70).
""")

st.caption(f"Laatste update: {time.strftime('%H:%M:%S')} - Ververst elke 15 minuten")

# 2. De 50 Tickers (Veilig onder elkaar)
tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0
        
        # Dividend rendement ophalen
        div = (t.info.get('dividendYield', 0) or 0) * 100
        
        # RSI Berekenen
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div
    except:
        return None, 0

# 3. Analyse Loop
data_rows = []
progress_bar = st.progress(0)

for i, sym in enumerate(tickers):
    df, div = get_stock_data(sym)
    
    if df is not None and len(df) > 20:
        current_price = df['Close'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        ma_1y = df['Close'].mean()
        ma_6m = df['Close'].tail(126).mean()
        
        # Trends bepalen
        trend_1y = "✅" if current_price > ma_1y else "❌"
        trend_6m = "✅" if current_price > ma_6m else "❌"
        
        # Advies Logica
        if trend_1y == "✅" and trend_6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN (Dip)"
        elif trend_1y == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif trend_1y == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym,
            "Advies": advies,
            "Prijs": round(current_price, 2),
            "Div %": round(div, 2),
            "RSI": round(rsi, 1),
            "6m Trend": trend_6m,
            "1j Trend": trend_1y
        })
    
    progress_bar.progress((i + 1) / len(tickers))

# 4. Weergave in tabel
if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    
    # Styling voor de tabel
    def style_rows(val):
        if "KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.3)'
        if "WINST" in val: return 'background-color: rgba(0, 123, 255, 0.3)'
        if "VERMIJDEN" in val: return 'color: rgba(220, 53, 69, 0.8)'
        return ''

    st.dataframe(
        df_final.style.applymap(style_rows, subset=['Advies']), 
        use_container_width=True,
        height=800
    )

# 5. Auto-refresh
time.sleep(900)
st.rerun()
