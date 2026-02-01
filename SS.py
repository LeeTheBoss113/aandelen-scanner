import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Heatmap", layout="wide")

# --- 2. DE SCAN FUNCTIE ---
def scan_aandeel(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 30: return None
        
        close = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        
        # Berekeningen
        rsi_val = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / (-1 * close.diff().clip(upper=0).rolling(14).mean() + 0.000001)))).iloc[-1]
        
        hi, lo, curr = float(close.max()), float(close.min()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        # KANS SCORE: Hoog als RSI laag is EN afstand tot top groot is
        # (100-RSI) geeft koopdruk aan, (dist_top * 2) geeft herstelpotentieel aan
        kans_score = (100 - rsi_val) + (dist_top * 1.5)
        
        status = "💎 STRONG BUY" if kans_score > 85 else "✅ Buy" if kans_score > 70 else "⚖️ Hold" if rsi_val < 70 else "🔥 SELL"
        
        return {
            "Status": status,
            "Ticker": ticker,
            "Kans Score": round(kans_score, 1),
            "Prijs": round(curr, 2),
            "RSI": round(rsi_val, 1),
            "Korting t.o.v. Top": round(dist_top, 1),
        }
    except: return None

# --- 3. DASHBOARD ---
st.title("🎯 Markt Kansen Heatmap")
st.subheader("Hoogste verdienkansen op basis van technische uitputting en herstelpotentieel.")

with st.sidebar:
    tickers = st.text_area("Tickers (comma separated):", "ASML.AS, KO, GOOGL, NVDA, TSLA, AMZN, NFLX, SHEL.AS, AD.AS, PYPL, DIS")
    refresh = st.button("🔄 Forceer Update")

ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
results = []

# Voortgangsbalk
progress_bar = st.progress(0)
for i, t in enumerate(ticker_list):
    res = scan_aandeel(t)
    if res: results.append(res)
    progress_bar.progress((i + 1) / len(ticker_list))

if results:
    df = pd.DataFrame(results).sort_values(by="Kans Score", ascending=False)

    # --- 4. DE HEATMAP WEERGAVE ---
    st.data_editor(
        df,
        column_config={
            "Kans Score": st.column_config.ProgressColumn(
                "Verdienkans Score",
                help="Gecombineerde score van RSI en Korting",
                format="%.1f",
                min_value=0,
                max_value=150,
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI (Hitte)",
                help="Lager is beter voor aankoop",
                format="%.1f"
            ),
            "Status": st.column_config.SelectboxColumn(
                "Actie",
                options=["💎 STRONG BUY", "✅ Buy", "⚖️ Hold", "🔥 SELL"],
            )
        },
        hide_index=True,
        use_container_width=True,
        disabled=True # Maakt het een pure weergave tool
    )

    # --- 5. TOP 3 HIGHLIGHTS ---
    st.divider()
    top_3 = df.head(3)
    cols = st.columns(3)
    for idx, row in enumerate(top_3.itertuples()):
        with cols[idx]:
            st.metric(label=f"TOP KANS: {row.Ticker}", value=f"{row.Kans Score} Ptn", delta=f"{row.Korting t.o.v. Top}% korting")
            st.write(f"Huidige Prijs: **€{row.Prijs}**")

else:
    st.error("Kon geen data ophalen. Controleer je internet of tickers.")
