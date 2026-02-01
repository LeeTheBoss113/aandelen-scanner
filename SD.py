import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Sector Spread Scanner 2026", layout="wide")

# --- 2. SECTOR INDELING ---
SECTOREN = {
    "💻 Big Tech & Groei": ["NVDA", "MSFT", "GOOGL", "AMZN", "META", "AAPL", "TSLA", "ADYEN.AS", "ASML.AS", "AMD", "PLTR", "NFLX"],
    "🏦 Finance & Dividend": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO", "PEP", "PG", "JNJ", "ABBV", "O"],
    "⛽ Energie & Industrie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP", "CAT", "DE", "GE", "UPS", "FEDEX"],
    "🛒 Retail & Consument": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD", "HD", "LOW", "ABNB", "BKNG"],
    "🧪 Health & Tech-Recovery": ["PFE", "MRK", "AZN.L", "BABA", "PYPL", "INTC", "CRM", "SQ", "SHOP", "BA"]
}

# --- 3. SCAN FUNCTIE ---
def scan_aandeel(ticker, sector_naam):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 20: return None
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # RSI & Afstand Top
        delta = close.diff()
        up, down = delta.clip(lower=0).rolling(14).mean(), -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)))).iloc[-1]
        hi, curr = float(close.max()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        kans_score = (100 - float(rsi)) + (dist_top * 1.5)
        status = "💎 STRONG BUY" if kans_score > 85 else "✅ Buy" if kans_score > 70 else "⚖️ Hold" if rsi < 70 else "🔥 SELL"
        
        return {
            "Sector": sector_naam,
            "Ticker": ticker,
            "Kans_Score": round(float(kans_score), 1),
            "RSI": round(float(rsi), 1),
            "Korting": round(float(dist_top), 1),
            "Prijs": round(float(curr), 2),
            "Status": status
        }
    except: return None

# --- 4. DATA VERZAMELEN ---
st.title("🎯 Sector-Gespreide Markt Heatmap")

all_results = []
progress_bar = st.progress(0)
total_tickers = sum(len(v) for v in SECTOREN.values())
counter = 0

with st.spinner('Scannen van alle sectoren...'):
    for sector, tickers in SECTOREN.items():
        for t in tickers:
            res = scan_aandeel(t, sector)
            if res: all_results.append(res)
            counter += 1
            progress_bar.progress(counter / total_tickers)

# --- 5. VISUALISATIE ---
if all_results:
    df_all = pd.DataFrame(all_results)
    
    # Weergave in 5 kolommen (voor elke sector één)
    st.header("🏆 Top 3 Kansen per Sector")
    sector_cols = st.columns(5)
    
    for i, (sector_naam, col) in enumerate(zip(SECTOREN.keys(), sector_cols)):
        with col:
            st.markdown(f"### {sector_naam}")
            # Filter op sector en pak de top 3
            sector_df = df_all[df_all['Sector'] == sector_naam].sort_values('Kans_Score', ascending=False).head(3)
            
            for row in sector_df.itertuples():
                with st.container(border=True):
                    st.metric(label=row.Ticker, value=f"{row.Kans_Score} Ptn", delta=f"-{row.Korting}%")
                    if "STRONG" in row.Status: st.success(row.Status)
                    elif "Buy" in row.Status: st.info(row.Status)
                    else: st.warning(row.Status)
                    st.caption(f"RSI: {row.RSI} | €{row.Prijs}")

    st.divider()
    st.subheader("📊 Volledige Marktlijst (Sorteerbaar)")
    st.dataframe(df_all.sort_values('Kans_Score', ascending=False), use_container_width=True, hide_index=True)

else:
    st.error("Laden mislukt. Herstart de app.")