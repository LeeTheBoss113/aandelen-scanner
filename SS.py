import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Ultimate Score Scanner", layout="wide")
st.title("🏆 Beste Kansen: RSI + Dividend Score")

# Je lijst met aandelen
watchlist = ["ASML.AS", "AAPL", "MSFT", "NVDA", "TSLA", "SHELL.AS", "KO", "ABBV", "PEP", "INTC"]

def scan_aandeel(ticker_symbol):
    t = yf.Ticker(ticker_symbol)
    hist = t.history(period="1y")
    
    # 1. RSI Berekening
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    huidige_rsi = rsi.iloc[-1]
    
    # 2. Dividend Yield ophalen
    div_yield = t.info.get('dividendYield', 0)
    if div_yield is None: div_yield = 0
    yield_perc = div_yield * 100
    
    # 3. DE SCORE BEREKENING (Onze eigen logica)
    # Lage RSI is goed (punten = 100 - RSI)
    # Hoog dividend is goed (we tellen yield * 5 erbij op als bonus)
    score = (100 - huidige_rsi) + (yield_perc * 5)
    
    return {
        "Ticker": ticker_symbol,
        "Prijs": round(hist['Close'].iloc[-1], 2),
        "RSI": round(huidige_rsi, 1),
        "Dividend": f"{yield_perc:.2f}%",
        "Kansen-Score": round(score, 1)
    }

if st.button("Bereken Beste Kansen"):
    results = []
    progress_bar = st.progress(0)
    
    for i, s in enumerate(watchlist):
        try:
            data = scan_aandeel(s)
            results.append(data)
        except Exception as e:
            st.warning(f"Kon {s} niet laden. Check of de ticker klopt.")
        progress_bar.progress((i + 1) / len(watchlist))
    
    # CHECK: Hebben we wel data?
    if len(results) > 0:
        df = pd.DataFrame(results)
        
        # Dubbelcheck of de kolom echt bestaat voor we sorteren
        if "Kansen-Score" in df.columns:
            df_final = df.sort_values(by="Kansen-Score", ascending=False)
            st.subheader("Top Resultaten")
            st.dataframe(df_final.style.background_gradient(subset=['Kansen-Score'], cmap='YlGn'))
            
            top_ticker = df_final.iloc[0]['Ticker']
            st.success(f"🎯 Volgens de scan is **{top_ticker}** momenteel de meest interessante optie.")
        else:
            st.error("Kolom 'Kansen-Score' ontbreekt. Er gaat iets mis in de scan_aandeel functie.")
    else:
        st.error("De lijst met resultaten is leeg. Controleer je internetverbinding of de tickers in je watchlist.")