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
    user_tickers = st.text_area("Mijn Watchlist:", "ASML.AS, KO, TSLA, AAPL")
    
    # DE MARKT OVERALL (TOP 50)
    # Een mix van Tech, Dividend, AEX en Groei
    markt_top_50 = [
        "NVDA", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "COST", "NFLX", "AMD", # Tech
        "ASML.AS", "ADYEN.AS", "INGA.AS", "AD.AS", "SHEL.AS", "RDSA.AS", # AEX
        "JNJ", "PG", "V", "MA", "ABBV", "PEP", "XOM", "CVX", "WMT", # Dividend / Value
        "NKE", "DIS", "PYPL", "BABA", "CRM", "INTC", "PLTR", "UBER", "ABNB", # Groei / Herstel
        "O", "MO", "T", "VZ", "PFE", "MRK", "MCD", "NSRGY", "OR.PA", "MC.PA" # Global Giants
    ]
    
    st.info(f"De scanner analyseert nu {len(markt_top_50)} markt-leiders + jouw watchlist.")

# Combineer en verwijder dubbelen
ticker_list = list(set([t.strip().upper() for t in user_tickers.split(",") if t.strip()] + markt_top_50))
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

    # We maken twee hoofdkolommen: links de tabel (60%), rechts de topkaarten (40%)
    main_col_left, main_col_right = st.columns([1.5, 1])

    with main_col_left:
        st.subheader("🔥 Markt Heatmap")
        st.dataframe(
            df.style.background_gradient(cmap='RdYlGn', subset=['Kans_Score'], vmin=40, vmax=100),
            column_config={
                "Kans_Score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=150),
                "Korting_Top": st.column_config.NumberColumn("Korting", format="%.1f%%"),
                "Prijs": st.column_config.NumberColumn("Koers", format="€%.2f"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.0f"),
            },
            hide_index=True,
            use_container_width=True,
            height=800 # Zorgt dat de tabel lang genoeg is voor je monitor
        )

    with main_col_right:
        st.subheader("🏆 Top 15 Selectie")
        
        # We maken binnen de rechterkolom een grid van 2 breed voor de kaartjes
        grid_cols = st.columns(2)
        top_15 = df.head(15)
        
        for idx, row in enumerate(top_15.itertuples()):
            with grid_cols[idx % 2]:
                with st.container(border=True):
                    # Compactere weergave voor de zijbalk
                    st.markdown(f"**{idx+1}. {row.Ticker}**")
                    st.metric(label="Score", value=f"{row.Kans_Score}", delta=f"-{row.Korting_Top}%")
                    
                    if "STRONG BUY" in row.Status:
                        st.success(row.Status)
                    elif "Buy" in row.Status:
                        st.info(row.Status)
                    elif "Hold" in row.Status:
                        st.warning(row.Status)
                    else:
                        st.error(row.Status)
                    
                    st.caption(f"€{row.Prijs} | RSI: {row.RSI}")

else:
    st.warning("Geen data gevonden. Voeg meer tickers toe in de sidebar.")
