import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta

# 1. Configuratie en Sectoren
symbols_dict = {
    'AAPL': 'Tech', 'MSFT': 'Tech', 
    'GC=F': 'Commodities', 'CL=F': 'Energy',
    'TSLA': 'Consumer', 'EURUSD=X': 'Forex'
}

def get_detailed_status(symbol):
    df = yf.download(symbol, period="1y", interval="1d")
    current_price = df['Close'].iloc[-1]
    
    # Bereken gemiddeldes (252 handelsdagen in een jaar, 126 in 6 mnd)
    ma_6m = df['Close'].tail(126).mean()
    ma_1y = df['Close'].mean()
    
    s_6m = "✅" if current_price > ma_6m else "❌"
    s_1y = "✅" if current_price > ma_1y else "❌"
    
    # Bepaal status tekst
    if s_6m == "✅" and s_1y == "✅": status = "Bullish"
    elif s_6m == "❌" and s_1y == "✅": status = "Correctie"
    elif s_6m == "✅" and s_1y == "❌": status = "Herstel"
    else: status = "Bearish"
    
    return s_6m, s_1y, status, round(current_price, 2)

# 2. Data Verzamelen
data_rows = []
for sym, sector in symbols_dict.items():
    s6, s1, stat, price = get_detailed_status(sym)
    data_rows.append({
        "Ticker": sym,
        "Sector": sector,
        "Prijs": price,
        "6 Maanden": s6,
        "1 Jaar": s1,
        "Trend": stat
    })

df_final = pd.DataFrame(data_rows)

# 3. Kleurfunctie voor de tabel
def color_rows(row):
    if row['Trend'] == 'Bullish': return ['background-color: #d4edda'] * len(row) # Groen
    if row['Trend'] == 'Bearish': return ['background-color: #f8d7da'] * len(row) # Rood
    if row['Trend'] == 'Correctie': return ['background-color: #fff3cd'] * len(row) # Geel
    if row['Trend'] == 'Herstel': return ['background-color: #d1ecf1'] * len(row) # Blauw
    return [''] * len(row)

# 4. Streamlit Display
st.subheader("🔥 Sector Risk & Trend Heatmap")
st.dataframe(df_final.style.apply(color_rows, axis=1), use_container_width=True)

# 5. Legenda (onder de tabel)
st.info("""
**Legenda:**
- 🟩 **Bullish (✅✅):** Alles op groen. Momentum is sterk.
- 🟨 **Correctie (❌✅):** Lange termijn trend is nog stijgend, maar korte termijn zwakte.
- 🟦 **Herstel (✅❌):** Krabbelt op uit een dal, maar lange termijn nog negatief.
- 🟥 **Bearish (❌❌):** Vermijden of defensief positioneren.
""")
