import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# 1. Pagina instellingen
st.set_page_config(page_title="Safe Dividend Scanner", layout="wide")
st.title("🛡️ Slimme Dividend Scanner: Koopsignalen & Risico")

# 2. De selectie (Lijst ingekort voor snellere check)
symbols_dict = {
    'KO': 'Coca-Cola', 
    'PEP': 'Pepsi', 
    'JNJ': 'Healthcare', 
    'O': 'Realty Income', 
    'PG': 'P&G', 
    'ABBV': 'AbbVie'
}

@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        # We halen alleen de koershistorie op (dit gaat bijna altijd goed)
        df = t.history(period="1y")
        if df.empty:
            return None, {}
            
        # Probeer fundamentele data op te halen (dividend/beta)
        # We doen dit apart zodat bij een fout niet alles vastloopt
        try:
            info = t.info
        except:
            info = {}
            
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, info
    except Exception as e:
        return None, {}

def analyze_logic(df, info):
    closes = df['Close'].values.flatten()
    current_price = float(closes[-1])
    ath = float(np.max(closes))
    discount = ((ath - current_price) / ath) * 100
    
    # Dividend & Risico (met fallbacks als Yahoo info blokkeert)
    div_yield = info.get('dividendYield', 0) if info else 0
    div_pct = (div_yield * 100) if div_yield else 0
    beta = info.get('beta', 1.0) if info and info.get('beta') else 1.0
    
    # Techniek
    rsi_vals = df['RSI'].fillna(50).values
    rsi = float(rsi_vals[-1])
    ma_1y = float(np.mean(closes))
    trend_1j = "✅" if current_price > ma_1y else "❌"
    
    # Advies Logica
    if trend_1j == "✅" and rsi < 60 and discount > 2:
        advies = "🌟 NU KOPEN"
    elif trend_1j == "✅" and rsi > 70:
        advies = "⚠️ OVERVERHIT"
    elif trend_1j == "❌":
        advies = "😴 GEEN TREND"
    else:
        advies = "⏳ AFWACHTEN"
        
    return trend_1j, round(current_price, 2), round(div_pct, 2), round(beta, 2), round(rsi, 1), round(discount, 1), advies

# 4. Data Verwerking
data_rows = []
progress_bar = st.progress(0)
symbols = list(symbols_dict.keys())

for i, sym in enumerate(symbols):
    df, info = get_stock_data(sym)
    if df is not None:
        tr1, pr, dv, bt, rs, disc, adv = analyze_logic(df, info)
        data_rows.append({
            "Ticker": sym, 
            "Sector": symbols_dict[sym],
            "Advies": adv, 
            "Div %": dv, 
            "Beta": bt,
            "RSI": rs, 
            "Korting %": disc
        })
    progress_bar.progress((i + 1) / len(symbols))

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)

    def color_advies(val):
        if "NU KOPEN" in val: return 'background-color: rgba(40, 167, 69, 0.3)'
        if "OVERVERHIT" in val: return 'background-color: rgba(220, 53, 69, 0.3)'
        return ''

    st.subheader("📊 Overzicht & Koopsignalen")
    st.dataframe(df_final.style.applymap(color_advies, subset=['Advies']), use_container_width=True)
else:
    st.error("Yahoo Finance blokkeert momenteel de aanvraag. Probeer de pagina over een paar minuten te verversen.")
