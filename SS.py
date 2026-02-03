import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# 1. Pagina instellingen
st.set_page_config(page_title="Safe Dividend Scanner", layout="wide")
st.title("🛡️ Slimme Dividend Scanner: Koopsignalen & Risico")

# 2. De selectie: Stabiele dividendbetalers
symbols_dict = {
    'KO': 'Consumptie (Coca-Cola)', 
    'PEP': 'Consumptie (Pepsi)', 
    'JNJ': 'Healthcare (J&J)', 
    'O': 'Vastgoed (Realty Income)', 
    'PG': 'Consumptie (P&G)', 
    'ABBV': 'Farma (AbbVie)',
    'CVX': 'Energie (Chevron)', 
    'VUSA.AS': 'Index (S&P 500 Dividend)'
}

# 3. Data Functies
@st.cache_data(ttl=3600)
def get_data_and_info(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, t.info
    except: 
        return None, None

def analyze_logic(df, info):
    closes = df['Close'].values.flatten()
    current_price = float(closes[-1])
    ath = float(np.max(closes))
    discount = ((ath - current_price) / ath) * 100
    
    # Dividend & Risico
    div_yield = info.get('dividendYield', 0)
    div_pct = (div_yield * 100) if div_yield else 0
    beta = info.get('beta', 1.0) if info.get('beta') else 1.0
    
    # Techniek
    rsi = float(df['RSI'].fillna(50).values[-1])
    ma_1y = float(np.mean(closes))
    trend_1j = "✅" if current_price > ma_1y else "❌"
    
    # Advies Logica
    if trend_1j == "✅" and rsi < 60 and discount > 2:
        advies = "🌟 NU KOPEN"
    elif trend_1j == "✅" and rsi > 70:
        advies = "⚠️ OVERVERHIT"
    elif trend_1j == "❌":
