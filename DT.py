import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.set_page_config(layout="wide", title="Stability Dashboard")

# Shared API Logic
API_URL = "JOUW_APPS_SCRIPT_URL_HIER"

@st.cache_data(ttl=600)
def get_portfolio():
    try:
        r = requests.get(API_URL, timeout=5)
        data = r.json()
        df = pd.DataFrame(data[1:], columns=["T", "I", "P"])
        return df.dropna()
    except:
        return pd.DataFrame()

st.title("📈 Jouw Stability Dashboard")

df_pf = get_portfolio()

if not df_pf.empty:
    # Hier komen je metrics en grafieken
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Aantal Posities", len(df_pf))
    with col2:
        st.write("Hier kun je later je winst-grafiek toevoegen")
    
    st.dataframe(df_pf, use_container_width=True)
else:
    st.warning("Geen data gevonden. Ga naar 'Beheer' om tickers toe te voegen.")
