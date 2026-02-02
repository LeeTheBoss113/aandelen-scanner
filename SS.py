import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner", layout="wide")

SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 2. CORE SCAN FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or len(df) < 252:
            return None
        
        # Data opschonen
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        
        # Berekeningen
        sma63 = close.rolling(63).mean().iloc[-1]
        sma252 = close.rolling(252).mean().iloc[-1]
        
        # RSI
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)).iloc[-1]))
        
        # Score
        hi = float(close.tail(252).max())
        dist_top = ((hi - curr) / hi) * 100
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma252: score += 10
        if curr > sma63: score += 5
        
        # Status bepalen
        status = "⚖️ Hold"
        if score > 100 and curr > sma252:
            status = "💎 STRONG BUY"
        elif score > 80:
            status = "✅ Buy"
        elif rsi > 75:
            status = "🔥 SELL"
            
        # We maken het resultaat object STAP VOOR STAP om afkappen te voorkomen
        res = {}
        res["Sector"] = sector
        res["Ticker"] = ticker
        res["Score"] = round(score, 1)
        res["Status"] = status
        res["Trend3M"] = "✅" if curr > sma63 else "❌"
        res["Trend1J"] = "✅" if curr > sma252 else "❌"
        res["History"] = close.tail(126).values # Alleen de waardes voor de grafiek
        return res
    except:
        return None

# --- 3. UI UITVOERING ---
st.title("🎯 Holy Grail: Sector Dashboard")

all_res = []
tickers = [(t, s) for s, ts in SECTOREN.items() for t in ts]
pb = st.progress(0)

for i, (t, s) in enumerate(tickers):
    data = scan_aandeel(t, s)
    if data:
        all_res.append(data)
    pb.progress((i + 1) / len(tickers))
pb.empty()

if all_res:
    # Maak DataFrame en sorteer direct
    df = pd.DataFrame(all_res)
    df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
    
    col_tabel, col_cards = st.columns([1, 2])
    
    with col_tabel:
        st.subheader("📊 Ranking")
        # Toon tabel zonder de zware History kolom
        st.dataframe(df.drop(columns=["History"]), hide_index=True)
        
    with col_cards:
        st.subheader("🏆 Sector Top 3 Trends")
        for sec in SECTOREN.keys():
            sec_df = df[df['Sector'] == sec].head(3)
            if not sec_df.empty:
                st.markdown(f"#### {sec}")
                card_cols = st.columns(len(sec_df))
                
                for idx, row in enumerate(sec_df.itertuples()):
                    with card_cols[idx]:
                        with st.container(border=True):
                            st.write(f"**{row.Ticker}**")
                            # Teken de grafiek met de opgeslagen History data
                            st.line_chart(row.History, height=100)
                            st.write(f"Score: {row.Score}")
                            st.caption(f"{row.Status}")
                            st.write(f"{row.Trend3M} 3M | {row.Trend1J} 1J")
else:
    st.error("Geen data gevonden.")
