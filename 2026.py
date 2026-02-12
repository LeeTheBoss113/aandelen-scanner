import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json

# --- AIRTABLE CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
TABLE_NAME = "Portfolio"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Airtable Scanner 2026")

# --- DATA FUNCTIES ---
def get_airtable_data():
    response = requests.get(URL, headers=HEADERS)
    if response.status_code == 200:
        data = response.json().get('records', [])
        # Airtable data platmaken voor Pandas
        rows = []
        for r in data:
            row = r['fields']
            row['id'] = r['id'] # Uniek ID om later te kunnen verwijderen
            rows.append(row)
        return pd.DataFrame(rows)
    else:
        st.error(f"Airtable verbinding mislukt: {response.status_code}")
        return pd.DataFrame()

def add_to_airtable(ticker, inleg, koers, strategy):
    payload = {"fields": {"Ticker": ticker, "Inleg": inleg, "Koers": koers, "Type": strategy}}
    requests.post(URL, headers=HEADERS, json=payload)

def delete_from_airtable(record_id):
    requests.delete(f"{URL}/{record_id}", headers=HEADERS)

# --- UI ---
st.title("💎 Airtable Strategy Dashboard")

# --- DATA LADEN EN FILTEREN ---
df = get_airtable_data()

st.title("💎 Airtable Strategy Dashboard")

# Controleer of we data hebben en of de kolom 'Type' bestaat
if not df.empty and 'Type' in df.columns:
    # Zorg dat eventuele kleine letters of spaties geen invloed hebben
    df['Type'] = df['Type'].astype(str).str.strip()
    growth_df = df[df['Type'] == 'Growth']
    div_df = df[df['Type'] == 'Dividend']
else:
    # Als de kolom ontbreekt of de tabel leeg is, maak lege dataframes
    growth_df = pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"])
    div_df = pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"])
    if df.empty:
        st.info("De tabel is nog leeg. Voeg je eerste aandeel toe!")
    elif 'Type' not in df.columns:
        st.error("Fout: Kolom 'Type' niet gevonden in Airtable. Controleer de spelling!")

tab1, tab2 = st.tabs(["🚀 Growth", "🛡️ Dividend"])

def render_strategy(df_subset, label):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(f"Nieuwe {label} Trade")
        with st.form(f"form_{label}"):
            t = st.text_input("Ticker").upper()
            i = st.number_input("Inleg (€)", 100)
            k = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan naar Airtable"):
                add_to_airtable(t, i, k, label)
                st.success(f"{t} opgeslagen!")
                st.rerun()

    with col2:
        st.subheader("Actieve Posities")
        if not df_subset.empty:
            # We tonen alleen relevante kolommen
            display_df = df_subset[['Ticker', 'Inleg', 'Koers']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Verwijder knop
            to_delete = st.selectbox("Sluit positie:", [""] + df_subset['Ticker'].tolist(), key=f"del_{label}")
            if st.button("Verwijderen", key=f"btn_{label}"):
                rec_id = df_subset[df_subset['Ticker'] == to_delete]['id'].values[0]
                delete_from_airtable(rec_id)
                st.rerun()
        else:
            st.info("Geen posities gevonden.")

with tab1: render_strategy(growth_df, "Growth")

with tab2: render_strategy(div_df, "Dividend")
