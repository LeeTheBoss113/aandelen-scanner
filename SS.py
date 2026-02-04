import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import time

# 1. Pagina instellingen
st.set_page_config(page_title="Realtime Dividend Screener", layout="wide")

# Realtime klokje in de titel
st.title(f"🛡️ Realtime Dividend Screener (Update: {time.strftime('%H:%M:%S')})")

# 2. De "Vaste" lijst (Je hoeft deze nooit meer in te voeren)
symbols_dict = {
    'KO': 'Coca-Cola', 'PEP': 'Pepsi', 'JNJ': 'Healthcare', 'O': 'Realty Income', 
    'PG': 'P&G', 'ABBV': 'AbbVie', 'CVX': 'Chevron', 'XOM': 'Exxon Mobil',
    'MMM': '3M', 'T': 'AT&T', 'VZ': 'Verizon', 'WMT': 'Walmart', 
    'LOW': 'Lowes', 'TGT': 'Target', 'ABT': 'Abbott Labs', 'MCD': 'McDonalds',
    'ADBE': 'Adobe', 'MSFT': 'Microsoft', 'AAPL': 'Apple', 'IBM': 'IBM',
    'HD': 'Home Depot', 'COST': 'Costco', 'LLY': 'Eli Lilly', 'PFE': 'Pfizer',
    'MRK': 'Merck', 'DHR': 'Danaher', 'UNH': 'UnitedHealth', 'BMY': 'Bristol Myers',
    'AMGN': 'Amgen', 'SBUX': 'Starbucks', 'CAT': 'Caterpillar', 'DE': 'John Deere',
    'HON': 'Honeywell', 'UPS': 'UPS', 'FDX': 'FedEx', 'NEE': 'NextEra Energy',
    'SO': 'Southern Co', 'D': 'Dominion Energy', 'DUK': 'Duke Energy', 'PM': 'Philip Morris'
}

# 3. Knop om handmatig te verversen
if st.button('🔄 Update Koersen Nu'):
    st.cache_data.clear()

# 4. Data Functie (Caching staat nu op 10 minuten voor 'realtime' gevoel)
@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0, 1.0
        
        # Probeer dividend en beta
        try:
            # We pakken fast_info indien mogelijk voor snelheid
            div = (t.info.get('dividendYield', 0) or 0) * 100
            beta = t.info.get('beta', 1.0) or 1.0
        except:
            div, beta = 0, 1.0
            
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div, beta
    except:
        return None, 0, 1.0

# 5. Verwerking
data_rows = []
symbols = list(symbols_dict.keys())
progress_bar = st.progress(0)

for i, sym in enumerate(symbols):
    df, div, beta = get_stock_data(sym)
    if df is not None:
        closes = df['Close'].values.flatten()
        current_price = float(closes[-1])
        
        # Trend Checks
        ma_6m = float(np.mean(closes[-126:])) if len(closes) >= 126 else float(np.mean(closes))
        ma_1y = float(np.mean(closes))
        
        trend_6m = "✅" if current_price > ma_6m else "❌"
        trend_1y = "✅" if current_price > ma_1y else "❌"
        
        # RSI & Korting
        rsi = float(df['RSI'].fillna(50).values[-1])
        ath = float(np.max(closes))
        discount = ((ath - current_price) / ath) * 100
        
        # Advies Logica
        if trend_1y == "✅" and trend_6m == "✅" and rsi < 60:
            advies = "🌟 STERK KOOP"
        elif trend_1y == "✅" and trend_6m == "❌":
            advies = "⏳ PULLBACK"
        elif rsi > 70:
            advies = "⚠️ OVERVERHIT"
        else:
            advies = "😴 GEEN TREND"

        data_rows.append({
            "Ticker": sym,
            "Sector": symbols_dict[sym],
            "Advies": advies,
            "Div %": round(div, 2),
            "6m": trend_6m,
            "1j": trend_1y,
            "RSI": round(rsi, 1),
            "Korting %": round(discount, 1),
            "Beta": round(beta, 2)
        })
    progress_bar.progress((i + 1) / len(symbols))

# 6. Tabel Weergave
if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values(by="Div %", ascending=False)
    
    def color_advies(val):
        if "STERK KOOP" in val: return 'background-color: rgba(40, 167, 69, 0.3)'
        if "PULLBACK" in val: return 'background-color: rgba(255, 193, 7, 0.3)'
        return ''

    st.dataframe(df_final.style.applymap(color_advies, subset=['Advies']), use_container_width=True)
    
    # Automatische verversing (elke 10 minuten)
    # Dit zorgt ervoor dat de pagina zichzelf herlaadt zonder dat jij iets doet
    time.sleep(600)
    st.rerun()
