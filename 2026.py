import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Scanner 2026 - Rollback")

# PLAK HIER JE NIEUWE URL VAN JE NIEUWE GOOGLE SHEET
API_URL = "https://script.google.com/macros/s/AKfycbzbmiiW9CfjmchRe-2Ii0rKUWjB84MTdCC2hYAXkNosD9R4PzYR1Fwh0h8Wv4P7-XE3/exec"

# --- DATA OPHALEN (STABIELE METHODE) ---
def get_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        # We gebruiken de namen die we in de nieuwe sheet hebben gezet
        def clean(raw_data, fallback_cols):
            if not raw_data or len(raw_data) <= 1:
                return pd.DataFrame(columns=fallback_cols)
            # Headers van rij 1, data van de rest
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            return df
            
        df_a = clean(r.get('active', []), ["Ticker", "Inleg", "Koers", "Type"])
        df_l = clean(r.get('log', []), ["Datum", "Ticker", "Inleg", "Winst", "Type"])
        return df_a, df_l
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

# --- INTERFACE ---
df_active, df_log = get_data()

st.title("🚀 Dual-Strategy Dashboard (v11-02)")

# Splitsen van de data
if not df_active.empty and 'Type' in df_active.columns:
    # Zorg dat 'Type' geen vreemde spaties heeft
    df_active['Type'] = df_active['Type'].astype(str).str.strip()
    growth_df = df_active[df_active['Type'].str.upper() == "GROWTH"]
    div_df = df_active[df_active['Type'].str.upper() == "DIVIDEND"]
else:
    growth_df = pd.DataFrame()
    div_df = pd.DataFrame()

t1, t2, t3 = st.tabs(["🚀 Growth", "💎 Dividend", "📜 Logboek"])

def render_section(df, label):
    st.subheader(f"Actieve {label} Posities")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Nog geen {label} aandelen in de nieuwe sheet.")
    
    with st.expander(f"➕ Voeg {label} toe"):
        with st.form(f"f_{label}"):
            tick = st.text_input("Ticker").upper()
            inl = st.number_input("Inleg (€)", 100)
            krs = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan"):
                requests.post(API_URL, data=json.dumps({
                    "ticker": tick, "inleg": inl, "koers": krs, "type": label
                }))
                st.rerun()

with t1: render_section(growth_df, "Growth")
with t2: render_section(div_df, "Dividend")
with t3:
    st.subheader("Logboek (Verkopen)")

    st.dataframe(df_log, use_container_width=True, hide_index=True)
