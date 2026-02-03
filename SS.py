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
    selected_symbol = st.selectbox("Selecteer CFD voor analyse", symbols)
    df = get_data(selected_symbol)

    # Bereken Bollinger Bands voor visuele 'beweging'
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Upper'] = df['MA20'] + (df['Close'].rolling(window=20).std() * 2)
    df['Lower'] = df['MA20'] - (df['Close'].rolling(window=20).std() * 2)

    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name="Market Movement"
    ))

    # Bollinger Bands (deze laten de volatiliteit zien)
    fig.add_trace(go.Scatter(x=df.index, y=df['Upper'], line=dict(color='rgba(173, 216, 230, 0.5)'), name="Upper Band"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower'], line=dict(color='rgba(173, 216, 230, 0.5)'), fill='tonexty', name="Lower Band"))

    fig.update_layout(
        title=f"Volatiliteit Analyse: {selected_symbol}",
        xaxis_rangeslider_visible=True, # Hiermee kun je onderin schuiven tussen 6m en 1j
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
