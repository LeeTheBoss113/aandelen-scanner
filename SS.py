import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Heatmap", layout="wide")

# --- 2. DE SCAN FUNCTIE (EXTRA ROBUUST) ---
def scan_aandeel(ticker):
    try:
        # We proberen de data op te halen. Threads=False is stabieler in de cloud.
        data = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        
        if data.empty or len(data) < 20:
            return None
        
        # Herstel voor Multi-index (soms stuurt Yahoo een extra laag mee)
        if isinstance(data.columns, pd.MultiIndex):
            close = data['Close'][ticker]
        else:
            close = data['Close']
            
        # Berekeningen
        delta = close.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / (down + 0.000001)
        rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
        
        hi, curr = float(close.max()), float(close.iloc[-1])
        dist_top = ((hi - curr) / hi) * 100
        
        # Kans Score
        kans_score = (100 - float(rsi_val)) + (dist_top * 1.5)
        
        status = "💎 STRONG BUY" if kans_score > 85 else "✅ Buy" if kans_score > 70 else "⚖️ Hold" if rsi_val < 70 else "🔥 SELL"
        
        return {
            "Status": status,
            "Ticker": ticker,
            "Kans_Score": round(float(kans_score), 1),
            "Prijs": round(float(curr), 2),
            "RSI": round(float(rsi_val), 1),
            "Korting_Top": round(float(dist_top), 1),
        }
    except Exception as e:
        # Dit helpt ons zien wat er misgaat in de logs
        print(f"Fout bij {ticker}: {e}")
        return None

# --- 3. DASHBOARD ---
st.title("🎯 Markt Kansen Heatmap")

with st.sidebar:
    st.header("⚙️ Instellingen")
    # Kortere lijst om te testen of hij nu wel laadt
    tickers_default = "ASML.AS, KO, GOOGL, NVDA, TSLA, SHEL.AS, AAPL"
    tickers = st.text_area("Vul hier je tickers in:", tickers_default)
    st.divider()
    if st.button("♻️ Forceer Herstart"):
        st.cache_data.clear()
        st.rerun()

ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
results = []

# --- 4. HET LADEN ---
if ticker_list:
    placeholder = st.empty()
    with placeholder.container():
        st.info("Bezig met ophalen van live marktdata... Een moment geduld.")
        progress_bar = st.progress(0)
        
        for i, t in enumerate(ticker_list):
            res = scan_aandeel(t)
            if res:
                results.append(res)
            # Kleine pauze om Yahoo niet te overbelasten
            time.sleep(0.2)
            progress_bar.progress((i + 1) / len(ticker_list))
    
    placeholder.empty() # Verwijder de laad-melding

# --- 5. WEERGAVE ---
if results:
    df = pd.DataFrame(results).sort_values(by="Kans_Score", ascending=False)

    st.subheader("🔥 Actuele Kansen")
    st.dataframe(
        df,
        column_config={
            "Kans_Score": st.column_config.ProgressColumn("Verdienkans", format="%.1f", min_value=0, max_value=150),
            "Korting_Top": st.column_config.NumberColumn("Korting %", format="%.1f%%"),
            "Prijs": st.column_config.NumberColumn("Koers", format="€%.2f"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.divider()
    st.subheader("🏆 Top 15")
    top_3 = df.head(15)
    cols = st.columns(15)
    for idx, row in enumerate(top_3.itertuples()):
        with cols[idx]:
            st.metric(label=row.Ticker, value=f"{row.Kans_Score} Ptn", delta=f"-{row.Korting_Top}%")
            st.write(f"Status: **{row.Status}**")
else:
    st.warning("Er kon geen data worden opgehaald. Probeer de 'Forceer Herstart' knop in de sidebar of check of je tickers (bijv. AAPL) correct zijn.")

