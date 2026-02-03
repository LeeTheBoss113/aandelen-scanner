import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# 1. Pagina instellingen
st.set_page_config(page_title="Safe Dividend Scanner", layout="wide")

st.title("🛡️ Stabiele Dividend & Risico Scanner")
st.markdown("Focus op lage volatiliteit (Beta < 1) en stabiele inkomsten.")

# 2. Selectie van stabiele Dividend Aristocrats / Strong Yielders
symbols_dict = {
    'KO': 'Consumptie (Coca-Cola)', 
    'PEP': 'Consumptie (Pepsi)', 
    'JNJ': 'Healthcare (J&J)',
    'O': 'Vastgoed (Realty Income)', 
    'PG': 'Consumptie (P&G)',
    'ABBV': 'Farma (AbbVie)',
    'CVX': 'Energie (Chevron)',
    'MAIN': 'Financieel (Main St Capital)',
    'VUSA.AS': 'Index (S&P 500 Dividend)'
}

# 3. Legenda
st.markdown("### 📋 Dashboard Legenda")
L1, L2, L3 = st.columns(3)
L1.success("🟩 **Bullish:** Veilig herstel/groei. Prijs boven 6m en 1j gemiddelde.")
L2.warning("🟨 **Correctie:** Lange termijn OK, maar nu een dip (mogelijk koopmoment).")
L3.info("ℹ️ **Beta:** < 1.0 is veiliger dan de markt. > 1.0 is beweeglijker.")

st.divider()

# 4. Data Functies
@st.cache_data(ttl=3600)
def get_data_and_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        info = ticker.info
        
        if df.empty: return None, None
        
        # MultiIndex fix
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df, info
    except:
        return None, None

def analyze_stock(df, info):
    closes = df['Close'].values.flatten()
    current_price = float(closes[-1])
    
    # Dividend & Risico data
    div_yield = info.get('dividendYield', 0)
    div_pct = (div_yield * 100) if div_yield else 0
    beta = info.get('beta', 1.0)
    
    # Trend logica
    ma_6m = float(np.mean(closes[-126:])) if len(closes) >= 126 else float(np.mean(closes))
    ma_1y = float(np.mean(closes))
    
    s_6m = "✅" if current_price > ma_6m else "❌"
    s_1y = "✅" if current_price > ma_1y else "❌"
    
    if s_6m == "✅" and s_1y == "✅": status = "Bullish"
    elif s_6m == "❌" and s_1y == "✅": status = "Correctie"
    else: status = "Lage Momentum"
    
    return s_6m, s_1y, status, round(current_price, 2), round(div_pct, 2), round(beta, 2)

# 5. Verwerking
data_rows = []
for sym, sector in symbols_dict.items():
    df, info = get_data_and_info(sym)
    if df is not None:
        s6, s1, stat, price, div, beta = analyze_stock(df, info)
        data_rows.append({
            "Ticker": sym,
            "Sector": sector,
            "Prijs": price,
            "Div %": div,
            "Risico (Beta)": beta,
            "6m": s6,
            "1j": s1,
            "Trend Status": stat
        })

if data_rows:
    df_final = pd.DataFrame(data_rows)
    # Sorteren op Dividend (hoogste eerst)
    df_final = df_final.sort_values(by="Div %", ascending=False)

    # 6. Kleurfunctie
    def color_rows(row):
        if row['Trend Status'] == 'Bullish': return ['background-color: rgba(40, 167, 69, 0.2)'] * len(row)
        if row['Trend Status'] == 'Correctie': return ['background-color: rgba(255, 193, 7, 0.2)'] * len(row)
        return [''] * len(row)

    # 7. Weergave Tabel
    st.subheader("💰 Dividend Overzicht (Gesorteerd op opbrengst)")
    st.dataframe(df_final.style.apply(color_rows, axis=1), use_container_width=True)

    # 8. Grafiek met Risico-analyse
    st.divider()
    sel = st.selectbox("Bekijk grafiek van:", df_final['Ticker'].tolist())
    
    if sel:
        hist_df, _ = get_data_and_info(sel)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'], name="Koers", line=dict(color='#17a2b8')))
        
        # Voeg voortschrijdend gemiddelde toe voor visuele trend
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'].rolling(50).mean(), 
                                 name="50d Gemiddelde", line=dict(color='orange', dash='dot')))
        
        fig.update_layout(title=f"Trend Analyse: {sel}", height=500, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Kon geen data laden. Controleer je internet of tickers.")
