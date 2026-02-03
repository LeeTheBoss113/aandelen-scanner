import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# 1. Pagina instellingen
st.set_page_config(page_title="CFD Sector Analyzer", layout="wide")

st.title("📈 CFD Sector & Trend Analyzer")

# 2. Definieer je CFD's en Sectoren
# Voeg hier je eigen tickers toe (let op de yfinance notatie)
symbols_dict = {
    'AAPL': 'Tech', 
    'MSFT': 'Tech', 
    'NVDA': 'Semi-conductors',
    'GC=F': 'Commodities (Gold)', 
    'CL=F': 'Energy (Oil)',
    'TSLA': 'Automotive', 
    'EURUSD=X': 'Forex',
    '^GSPC': 'Indices (S&P500)'
}

# 3. Legenda direct in het hoofdscherm (geen sidebar)
st.markdown("### 📋 Trend Legenda & Betekenis")
L1, L2, L3, L4 = st.columns(4)
L1.info("🟦 **Herstel (✅❌)**\n\n6m > Gem, 1j < Gem")
L2.success("🟩 **Bullish (✅✅)**\n\n6m > Gem, 1j > Gem")
L3.warning("🟨 **Correctie (❌✅)**\n\n6m < Gem, 1j > Gem")
L4.error("🟥 **Bearish (❌❌)**\n\n6m < Gem, 1j < Gem")

st.divider()

# 4. Data Functies
@st.cache_data(ttl=3600) # Cache data voor 1 uur om snelheid te verhogen
def get_market_data(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d")
        if df.empty: return None
        # RSI Berekenen
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except:
        return None

def analyze_trends(df):
    current_price = df['Close'].iloc[-1]
    # Gemiddelde 6m (126 trading days) en 1j (252 trading days)
    ma_6m = df['Close'].tail(126).mean()
    ma_1y = df['Close'].mean()
    
    s_6m = "✅" if current_price > ma_6m else "❌"
    s_1y = "✅" if current_price > ma_1y else "❌"
    
    if s_6m == "✅" and s_1y == "✅": status = "Bullish"
    elif s_6m == "❌" and s_1y == "✅": status = "Correctie"
    elif s_6m == "✅" and s_1y == "❌": status = "Herstel"
    else: status = "Bearish"
    
    return s_6m, s_1y, status, round(float(current_price), 2), round(float(df['RSI'].iloc[-1]), 2)

# 5. Data Verzamelen voor de tabel
data_rows = []
for sym, sector in symbols_dict.items():
    raw_data = get_market_data(sym)
    if raw_data is not None:
        s6, s1, stat, price, rsi = analyze_trends(raw_data)
        data_rows.append({
            "Ticker": sym,
            "Sector": sector,
            "Prijs": price,
            "RSI": rsi,
            "6 Maanden": s6,
            "1 Jaar": s1,
            "Trend Status": stat
        })

df_final = pd.DataFrame(data_rows)

# 6. Kleurfunctie voor de tabel
def color_rows(row):
    color = ''
    if row['Trend Status'] == 'Bullish': color = 'background-color: rgba(40, 167, 69, 0.3)' # Groen
    elif row['Trend Status'] == 'Bearish': color = 'background-color: rgba(220, 53, 69, 0.3)' # Rood
    elif row['Trend Status'] == 'Correctie': color = 'background-color: rgba(255, 193, 7, 0.3)' # Geel
    elif row['Trend Status'] == 'Herstel': color = 'background-color: rgba(23, 162, 184, 0.3)' # Blauw
    return [color] * len(row)

# 7. Weergave Tabel
st.subheader("📊 Sector Risk Heatmap")
st.dataframe(df_final.style.apply(color_rows, axis=1), use_container_width=True)

# 8. Grafieken Sectie
st.divider()
st.subheader("📈 Gedetailleerde Beweging (1 Jaar)")
selected_symbol = st.selectbox("Kies een CFD voor de grafiek", list(symbols_dict.keys()))

if selected_symbol:
    plot_data = get_market_data(selected_symbol)
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=plot_data.index,
        open=plot_data['Open'], high=plot_data['High'],
        low=plot_data['Low'], close=plot_data['Close'],
        name="Prijsactie"
    ))
    
    # Voeg 1-jaars gemiddelde toe om de trend te zien
    fig.add_trace(go.Scatter(x=plot_data.index, y=[plot_data['Close'].mean()]*len(plot_data), 
                             line=dict(color='white', dash='dash'), name="1j Gemiddelde"))

    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)
