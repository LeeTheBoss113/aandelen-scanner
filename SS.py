import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# 1. Pagina instellingen
st.set_page_config(page_title="CFD Sector Analyzer", layout="wide")

st.title("📈 CFD Sector & Trend Analyzer")

# 2. Definieer je CFD's en Sectoren
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

# 3. Legenda direct in het hoofdscherm
st.markdown("### 📋 Trend Legenda & Betekenis")
L1, L2, L3, L4 = st.columns(4)
L1.info("🟦 **Herstel (✅❌)**\n\n6m > Gem, 1j < Gem")
L2.success("🟩 **Bullish (✅✅)**\n\n6m > Gem, 1j > Gem")
L3.warning("🟨 **Correctie (❌✅)**\n\n6m < Gem, 1j > Gem")
L4.error("🟥 **Bearish (❌❌)**\n\n6m < Gem, 1j < Gem")

st.divider()

# 4. Data Functies met extra foutafhandeling
@st.cache_data(ttl=3600)
def get_market_data(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d")
        if df.empty: return None
        
        # Sla de MultiIndex plat
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # RSI Berekenen
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except Exception:
        return None

def analyze_trends(df):
    # Pak de waarden en zet ze om naar een platte lijst van getallen
    closes = df['Close'].values.flatten()
    current_price = float(closes[-1])
    
    # Gemiddeldes (6m = 126 dagen, 1j = totaal)
    ma_6m = float(np.mean(closes[-126:])) if len(closes) >= 126 else float(np.mean(closes))
    ma_1y = float(np.mean(closes))
    
    # RSI veilig uitlezen (pak de laatste waarde die geen NaN is)
    rsi_series = df['RSI'].fillna(50).values.flatten()
    current_rsi = float(rsi_series[-1])
    
    # Trend logica
    s_6m = "✅" if current_price > ma_6m else "❌"
    s_1y = "✅" if current_price > ma_1y else "❌"
    
    if s_6m == "✅" and s_1y == "✅": status = "Bullish"
    elif s_6m == "❌" and s_1y == "✅": status = "Correctie"
    elif s_6m == "✅" and s_1y == "❌": status = "Herstel"
    else: status = "Bearish"
    
    return s_6m, s_1y, status, round(current_price, 2), round(current_rsi, 2)

# 5. Data Verwerking
data_rows = []
for sym, sector in symbols_dict.items():
    raw_data = get_market_data(sym)
    if raw_data is not None and len(raw_data) > 0:
        try:
            s6, s1, stat, price, rsi = analyze_trends(raw_data)
            data_rows.append({
                "Ticker": sym, "Sector": sector, "Prijs": price,
                "RSI": rsi, "6 Maanden": s6, "1 Jaar": s1, "Trend Status": stat
            })
        except Exception as e:
            continue

if data_rows:
    df_final = pd.DataFrame(data_rows)

    # 6. Kleurfunctie
    def color_rows(row):
        colors = {
            'Bullish': 'background-color: rgba(40, 167, 69, 0.3)',
            'Bearish': 'background-color: rgba(220, 53, 69, 0.3)',
            'Correctie': 'background-color: rgba(255, 193, 7, 0.3)',
            'Herstel': 'background-color: rgba(23, 162, 184, 0.3)'
        }
        return [colors.get(row['Trend Status'], '')] * len(row)

    # 7. Tabel
    st.subheader("📊 Market Heatmap")
    st.dataframe(df_final.style.apply(color_rows, axis=1), use_container_width=True)

    # 8. Grafiek
    st.divider()
    selected_symbol = st.selectbox("Selecteer voor grafiek", df_final['Ticker'].tolist())
    
    if selected_symbol:
        plot_data = get_market_data(selected_symbol)
        if plot_data is not None:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=plot_data.index, open=plot_data['Open'], high=plot_data['High'],
                low=plot_data['Low'], close=plot_data['Close'], name=selected_symbol
            ))
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True)
            st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Geen data gevonden. Controleer de tickers of de verbinding.")
