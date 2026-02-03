import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

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

# 4. Data Functies met MultiIndex Fix
@st.cache_data(ttl=3600)
def get_market_data(symbol):
    try:
        # Download data
        df = yf.download(symbol, period="1y", interval="1d")
        if df.empty: return None
        
        # FIX: Soms geeft yfinance MultiIndex kolommen (bv. ['Close', 'AAPL']). 
        # We maken dit 'plat' naar alleen ['Close', 'Open', etc.]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # RSI Berekenen via pandas_ta
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except Exception as e:
        return None

def analyze_trends(df):
    # Pak de laatste waardes als pure getallen (floats)
    current_price = float(df['Close'].iloc[-1])
    
    # Gemiddelde 6m (126 dagen) en 1j (alle data in de df)
    ma_6m = float(df['Close'].tail(126).mean())
    ma_1y = float(df['Close'].mean())
    
    # RSI waarde (pak de laatste niet-lege waarde)
    current_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
    
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

if data_rows:
    df_final = pd.DataFrame(data_rows)

    # 6. Kleurfunctie voor de tabel
    def color_rows(row):
        color = ''
        if row['Trend Status'] == 'Bullish': color = 'background-color: rgba(40, 167, 69, 0.3)'
        elif row['Trend Status'] == 'Bearish': color = 'background-color: rgba(220, 53, 69, 0.3)'
        elif row['Trend Status'] == 'Correctie': color = 'background-color: rgba(255, 193, 7, 0.3)'
        elif row['Trend Status'] == 'Herstel': color = 'background-color: rgba(23, 162, 184, 0.3)'
        return [color] * len(row)

    # 7. Tabel tonen
    st.subheader("📊 Market Heatmap")
    st.dataframe(df_final.style.apply(color_rows, axis=1), use_container_width=True)

    # 8. Grafiek Sectie
    st.divider()
    selected_symbol = st.selectbox("Selecteer een CFD voor grafiek details", df_final['Ticker'].tolist())
    
    if selected_symbol:
        plot_data = get_market_data(selected_symbol)
        fig = go.Figure()
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=plot_data.index,
            open=plot_data['Open'], high=plot_data['High'],
            low=plot_data['Low'], close=plot_data['Close'],
            name=selected_symbol
        ))
        
        # 1-jaars gemiddelde lijn
        avg_1y = plot_data['Close'].mean()
        fig.add_trace(go.Scatter(x=plot_data.index, y=[avg_1y]*len(plot_data), 
                                 line=dict(color='gray', dash='dash'), name="Jaar Gemiddelde"))

        fig.update_layout(
            title=f"Koersverloop {selected_symbol}",
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=True
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Kon geen data ophalen. Controleer je internetverbinding of tickers.")
