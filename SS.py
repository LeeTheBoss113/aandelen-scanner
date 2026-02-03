import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Safe Dividend & Buy Scanner", layout="wide")
st.title("🛡️ Slimme Dividend Scanner: Koopsignalen & Risico")

# De selectie: Stabiele dividendbetalers
symbols_dict = {
    'KO': 'Consumptie (Coca-Cola)', 'PEP': 'Consumptie (Pepsi)', 
    'JNJ': 'Healthcare (J&J)', 'O': 'Vastgoed (Realty Income)', 
    'PG': 'Consumptie (P&G)', 'ABBV': 'Farma (AbbVie)',
    'CVX': 'Energie (Chevron)', 'VUSA.AS': 'Index (S&P 500 Dividend)'
}

@st.cache_data(ttl=3600)
def get_data_and_info(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, t.info
    except: return None, None

def analyze_logic(df, info):
    closes = df['Close'].values.flatten()
    current_price = float(closes[-1])
    ath = float(np.max(closes))
    discount = ((ath - current_price) / ath) * 100
    
    # Fundamentele data
    div_yield = (info.get('dividendYield', 0) or 0) * 100
    beta = info.get('beta', 1.0) or 1.0
    
    # Technische data
    rsi = float(df['RSI'].fillna(50).values[-1])
    ma_1y = float(np.mean(closes))
    trend_1j = "✅" if current_price > ma_1y else "❌"
    
    # KOOPSIGNAAL LOGICA
    # We kopen als: Trend is goed EN RSI is niet te hoog (onder 60) EN er is een kleine korting (>2%)
    if trend_1j == "✅" and rsi < 60 and discount > 2:
        advies = "🌟 NU KOPEN"
    elif trend_1j == "✅" and rsi > 70:
        advies = "⚠️ OVERVERHIT (Wacht)"
    elif trend_1j == "❌":
        advies = "😴 GEEN TREND"
    else:
        advies = "⏳ AFWACHTEN"
        
    return trend_1j, round(current_price, 2), round(div_pct, 2), round(beta, 2), round(rsi, 1), round(discount, 1), advies

# Data verwerken
data_rows = []
for sym, sector in symbols_dict.items():
    df, info = get_data_and_info(sym)
    if df is not None:
        tr1, pr, dv, bt, rs, disc, adv = analyze_logic(df, info)
        data_rows.append({
            "Ticker": sym, "Advies": adv, "Div %": dv, "Risico (Beta)": bt,
            "RSI": rs, "Korting v. Top %": disc, "1j Trend": tr1
        })

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)

    # Kleurcodes voor Advies
    def color_advies(val):
        if "NU KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.4); font-weight: bold'
        if "OVERVERHIT" in val: return 'background-color: rgba(220, 53, 69, 0.2)'
        return ''

    st.subheader("📊 Selectie op basis van Dividend en Koopsignaal")
    st.dataframe(df_final.style.applymap(color_advies, subset=['Advies']), use_container_width=True)

    # Uitleg Pullback
    st.info("""
    **Hoe werkt het Koopsignaal?** Een aandeel krijgt '🌟 NU KOPEN' als de lange trend positief is (✅), maar de prijs op dit moment een kleine 'dip' (Pullback) vertoont. 
    Dit verlaagt het risico dat je op de absolute top koopt.
    """)

    # Grafiek
    sel = st.selectbox("Analyseer koersverloop:", df_final['Ticker'].tolist())
    if sel:
        hist_df, _ = get_data_and_info(sel)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=
