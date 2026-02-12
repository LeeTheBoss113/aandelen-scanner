import streamlit as st
import pandas as pd
import requests
import json
import time

# --- DE ENIGE ECHTE URL ---
# VERVANG DIT DOOR DE URL VAN JE NIEUWE SCRIPT (UIT DE NIEUWE SHEET)
API_URL = "https://script.google.com/macros/s/AKfycbzbmiiW9CfjmchRe-2Ii0rKUWjB84MTdCC2hYAXkNosD9R4PzYR1Fwh0h8Wv4P7-XE3/exec"

st.set_page_config(layout="wide", page_title="Stabiel Dashboard 2026")

# --- DEBUG INFO IN DE SIDEBAR ---
with st.sidebar:
    st.write("### 🛠 Verbindingscontrole")
    st.info(f"Huidige API URL eindigt op: ...{API_URL[-15:]}")
    if st.button("🔄 Forceer Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- DATA FUNCTIES ---
def get_data():
    try:
        # Timestamp voorkomt dat de browser 'oude' data uit het geheugen laat zien
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        # We bouwen de tabel op uit de JSON data
        active_data = r.get('active', [])
        log_data = r.get('log', [])
        
        if len(active_data) > 1:
            df_a = pd.DataFrame(active_data[1:], columns=active_data[0])
        else:
            df_a = pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"])
            
        if len(log_data) > 1:
            df_l = pd.DataFrame(log_data[1:], columns=log_data[0])
        else:
            df_l = pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst", "Type"])
            
        return df_a, df_l
    except Exception as e:
        st.error(f"Kan geen data ophalen. Check de URL. Fout: {e}")
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

# --- DATA LADEN ---
df_a, df_l = get_data()

# --- UI ---
st.title("🛡️ Stabiel Dashboard 2026")

# Splitsen op basis van kolom 'Type' (we maken het hoofdletter-ongevoelig)
df_a['Type'] = df_a['Type'].astype(str).str.strip().upper()
growth = df_a[df_a['Type'] == "GROWTH"]
dividend = df_a[df_a['Type'] == "DIVIDEND"]

tab1, tab2, tab3 = st.tabs(["🚀 Growth", "💎 Dividend", "📜 Logboek"])

def render_view(df, p_type_label):
    st.subheader(f"Portfolio: {p_type_label}")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Geen {p_type_label} aandelen gevonden in de nieuwe sheet.")

    with st.expander(f"➕ Voeg {p_type_label} toe"):
        with st.form(f"form_{p_type_label}"):
            t = st.text_input("Ticker (bijv. NVDA)").upper().strip()
            i = st.number_input("Inleg (€)", 100)
            k = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan"):
                if t and k > 0:
                    payload = {"ticker": t, "inleg": i, "koers": k, "type": p_type_label.upper()}
                    response = requests.post(API_URL, data=json.dumps(payload))
                    if response.status_code == 200:
                        st.success(f"{t} opgeslagen!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Fout bij opslaan.")

with tab1:
    render_view(growth, "Growth")

with tab2:
    render_view(dividend, "Dividend")

with tab3:
    st.subheader("Laatste verkopen")

    st.dataframe(df_l, use_container_width=True, hide_index=True)
