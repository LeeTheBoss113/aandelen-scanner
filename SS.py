import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 15:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rs = up / (down + 0.000001)
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        hi = float(close.max())
        curr = float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        score = (100 - float(rsi)) + (dist_top * 1.5)
        
        if score > 85: status = "💎 STRONG BUY"
        elif score > 70: status = "✅ Buy"
        elif rsi > 70 or dist_top < 0.5: status = "🔥 SELL"
        else: status = "⚖️ Hold"
        
        return {
            "Sector": sector, "Ticker": ticker, "Score": round(float(score), 1),
            "RSI": round(float(rsi), 1), "Korting": round(float(dist_top), 1),
            "Prijs": round(float(curr), 2), "Status": status
        }
    except:
        return None

# --- 4. DATA LADEN ---
st.title("🎯 Holy Grail: Sector Spread Dashboard")

ticker_items = []
for s, ts in SECTOREN.items():
    for t in ts:
        ticker_items.append((t, s))

all_results = []
progress_bar = st.progress(0)
status_text = st.empty()

for i, (t, s) in enumerate(ticker_items):
    status_text.text(f"Scannen: {t} ({s})")
    res = scan_aandeel(t, s)
    if res:
        all_results.append(res)
    progress_bar.progress((i + 1) / len(ticker_items))

status_text.empty()
progress_bar.empty()

# --- 5. VISUALISATIE ---
if all_results:
    df_all = pd.DataFrame(all_results).sort_values("Score", ascending=False)
    
    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.subheader("📊 Marktlijst")
        st.dataframe(
            df_all,
            column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=150, format="%.0f"),
                "Korting": st.column_config.NumberColumn("Korting %", format="%.1f%%"),
                "Prijs": st.column_config.NumberColumn("Koers", format="€%.2f"),
            },
            hide_index=True, use_container_width=True, height=800
        )

    with col_right:
        st.subheader("🏆 Sector Favorieten")
        for sector_naam in SECTOREN.keys():
            st.markdown(f"#### {sector_naam}")
            sec_df = df_all[df_all['Sector'] == sector_naam].head(3)
            
            # De fix voor de kaarten:
            card_cols = st.columns(3)
            for idx, row in enumerate(sec_df.itertuples()):
                # Belangrijk: alles hieronder moet 1 extra stap naar rechts ingesprongen zijn
                with card_cols[idx]:
                    with st.container(border=True):
                        st.metric(label=row.Ticker, value=f"{row.Score} Ptn", delta=f"-{row.Korting}%")
                        if "STRONG" in row.Status: st.success(row.Status)
                        elif "Buy" in row.Status: st.info(row.Status)
                        elif "SELL" in row.Status: st.error(row.Status)
                        else: st.warning(row.Status)
                        st.caption(f"RSI: {row.RSI} | €{row.Prijs}")
else:
    st.error("Data kon niet worden geladen.")
