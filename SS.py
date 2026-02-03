import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("📈 CFD Sector & RSI Analyzer")

# Voorbeeldlijst van CFD symbols (pas dit aan naar jouw brokers symbols)
symbols = ['AAPL', 'TSLA', 'MSFT', 'NVDA', 'GC=F', 'CL=F'] 

def get_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d")
    # RSI berekenen (meestal op 14 dagen)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    return df

# Layout kolommen
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Top Performers")
    for s in symbols:
        data = get_data(s)
        current_rsi = data['RSI'].iloc[-1]
        
        # Kleurcode op basis van RSI
        color = "green" if current_rsi < 30 else "red" if current_rsi > 70 else "white"
        st.markdown(f"**{s}**: RSI: <span style='color:{color}'>{current_rsi:.2f}</span>", unsafe_allow_html=True)

with col2:
    selected_symbol = st.selectbox("Selecteer CFD voor details", symbols)
    detail_data = get_data(selected_symbol)
    
    # Grafiek met 6m en 1j toggle
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=detail_data.index, y=detail_data['Close'], name="Prijs"))
    st.plotly_chart(fig, use_container_width=True)
