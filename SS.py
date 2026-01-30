import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Debug Holy Grail", layout="wide")

def scan_aandeel(ticker):
    try:
        # We gebruiken een langere timeout en expliciete periode
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo") # Even kort voor de test
        
        if hist.empty:
            st.error(f"Geen koersdata gevonden voor {ticker}")
            return None
        
        # RSI Berekening
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Info ophalen (dividend)
        info = stock.info
        div = (info.get('dividendYield', 0) or 0) * 100
        
        return {
            "Ticker": ticker, 
            "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2), 
            "Div %": round(div, 2),
            "Score": round((100 - rsi) + (div * 3), 2)
        }
    except Exception as e:
        st.error(f"Fout bij {ticker}: {e}")
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
