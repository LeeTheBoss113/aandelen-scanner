import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Debug Holy Grail", layout="wide")

def scan_aandeel(ticker):
    try:
        # yf.download is vaak stabieler op cloud servers
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if data.empty or len(data) < 15:
            return None
        
        # RSI Berekening (veiligere methode)
        close = data['Close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Voor dividend gebruiken we een aparte call
        stock_info = yf.Ticker(ticker)
        div = (stock_info.info.get('dividendYield', 0) or 0) * 100
        
        # Score berekening
        score = (100 - rsi) + (div * 3)
        
        return {
            "Ticker": ticker,
            "RSI": float(rsi),
            "Div %": float(div),
            "Score": float(score)
        }
    except Exception as e:
        # Dit laat in je app zien wat er precies misgaat
        st.sidebar.warning(f"Fout bij {ticker}: {str(e)}")
        return None

# --- 2. LAYOUT ---
st.title("🛠️ Scanner Debug Mode")

# TEST: Werkt Yahoo Finance überhaupt?
if st.button("🔄 Forceer Handmatige Scan"):
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🔍 Watchlist Scan")
        test_tickers = ["AAPL", "KO", "ASML.AS"] # Kleine testset
        results = []
        for t in test_tickers:
            with st.status(f"Scannen: {t}..."):
                res = scan_aandeel(t)
                if res:
                    results.append(res)
        
        if results:
            st.write("### ✅ Resultaten Gevonden!")
            st.dataframe(pd.DataFrame(results))
        else:
            st.error("❌ De scanner heeft helemaal niets teruggegeven.")

    with c2:
        st.subheader("ℹ️ Systeem Status")
        st.info("Als je hierboven rode foutmeldingen ziet, ligt het aan de verbinding met Yahoo.")

