import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        # RSI 14 Berekening
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = (info.get('dividendYield', 0) or 0) * 100
        
        # --- DE HOLY GRAIL LOGICA ---
        rsi_factor = 100 - rsi
        if rsi > 70: rsi_factor -= 30  # Strafpunt: Te duur
        if rsi < 35: rsi_factor += 25  # Bonus: Echte koopkans
        
        # De Mix: RSI is leidend, Dividend is de kers op de taart
        holy_grail_score = rsi_factor + (div * 3)
        
        return {
            "Ticker": ticker, 
            "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2), 
            "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'), 
            "Score": round(holy_grail_score, 2)
        }
    except: return None

# --- 2. STYLING ---
def style_results(df):
    return df.style.background_gradient(cmap='RdYlGn', subset=['Score'], vmin=40, vmax=100) \
                   .applymap(lambda x: 'color: #90ee90; font-weight: bold' if x < 35 else '', subset=['RSI'])

# --- 3. DASHBOARD (4 KOLOMMEN) ---
st.title("🚀 Holy Grail Portfolio Dashboard 2026")

c1, c2, c3, c4 = st.columns([1.3, 0.7, 1, 1])

with c1:
    st.header("🔍 Holy Grail Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO, V, AAPL", key="w1")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    results = [scan_aandeel(t) for t in tickers if scan_aandeel(t)]
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(style_results(df_all[['Ticker', 'RSI', 'Div %', 'Score']]), use_container_width=True)

with c2:
    st.header("💎 Buy Alert")
    grails = [r for r in results if r['Score'] >= 85]
    if grails:
        for g in grails:
            st.success(f"**{g['Ticker']}**\nScore: {g['Score']}\n\n*Perfecte timing!*")
    else:
        st.info("Geen Holy Grails op dit moment.")

with c3:
    st.header("⚖️ Portfolio")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p1")
    p_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_res = [scan_aandeel(t) for t in p_tickers if scan_aandeel(t)]
    if p_res:
        for r in p_res:
            label = "🔥 VERKOOP?" if r['RSI'] > 70 else "🛡️ HOLD"
            st.write(f"{label} **{r['Ticker']}** (RSI: {r['RSI']})")
        st.bar_chart(pd.DataFrame(p_res)['Sector'].value_counts())

with c4:
    st.header("💰 Tax Benefit")
    vermogen = st.number_input("Totaal Vermogen (€):", value=100000, step=10000)
    belasting = max(0, vermogen - 57000) * 0.021
    st.metric("Besparing via Partner", f"€{belasting:,.0f}", "100% Tax Free")
    st.write(f"Netto dividend voordeel: **+{belasting/12:,.2f} p/m**")
