import streamlit as st
import pandas as pd
import requests
import json
import time

# --- AIRTABLE CONFIG ---
# Zorg dat deze tokens exact kloppen!
AIRTABLE_TOKEN = "JOUW_PAT_TOKEN_HIER"
BASE_ID = "JOUW_BASE_ID_HIER"
TABLE_NAME = "Portfolio"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

st.set_page_config(layout="wide", page_title="Airtable Scanner 2026")

# --- DATA FUNCTIES ---
def get_airtable_data():
    try:
        response = requests.get(f"{URL}?t={int(time.time())}", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            records = response.json().get('records', [])
            if not records:
                return pd.DataFrame()
            
            rows = []
            for r in records:
                row = r['fields']
                row['airtable_id'] = r['id']  # Nodig voor verwijderen
                rows.append(row)
            return pd.DataFrame(rows)
        else:
            st.error(f"Airtable verbinding mislukt: {response.status_code}")
            st.write(response.text)
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Fout bij ophalen data: {e}")
        return pd.DataFrame()

def add_to_airtable(ticker, inleg, koers, strategy):
    payload = {
        "fields": {
            "Ticker": ticker,
            "Inleg": inleg,
            "Koers": koers,
            "Type": strategy
        }
    }
    res = requests.post(URL, headers=HEADERS, json=payload)
    return res.status_code == 200

def delete_from_airtable(record_id):
    res = requests.delete(f"{URL}/{record_id}", headers=HEADERS)
    return res.status_code == 200

# --- MAIN APP ---
st.title("🛡️ Strategie Dashboard 2026")

df = get_airtable_data()

# VEILIG FILTEREN: Check of de kolommen bestaan
if not df.empty and 'Type' in df.columns:
    df['Type'] = df['Type'].astype(str).str.strip()
    growth_df = df[df['Type'] == 'Growth']
    div_df = df[df['Type'] == 'Dividend']
else:
    growth_df = pd.DataFrame()
    div_df = pd.DataFrame()

# Tabs voor de weergave
tab1, tab2 = st.tabs(["🚀 Growth", "💎 Dividend"])

def render_section(df_subset, label):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(f"Nieuwe {label} Trade")
        with st.form(f"form_{label}"):
            t = st.text_input("Ticker (bijv. NVDA)").upper().strip()
            i = st.number_input("Inleg (€)", min_value=0, value=100)
            k = st.number_input("Koers", min_value=0.0, value=0.0, format="%.2f")
            
            if st.form_submit_button(f"Toevoegen aan {label}"):
                if t and k > 0:
                    if add_to_airtable(t, i, k, label):
                        st.success(f"{t} toegevoegd!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Opslaan mislukt. Check je Airtable velden.")
                else:
                    st.warning("Vul een ticker en koers in.")

    with col2:
        st.subheader(f"Actieve {label} Posities")
        if not df_subset.empty:
            # Alleen relevante kolommen tonen voor de tabel
            cols_to_show = [c for c in ['Ticker', 'Inleg', 'Koers'] if c in df_subset.columns]
            st.dataframe(df_subset[cols_to_show], use_container_width=True, hide_index=True)
            
            # Verwijderen sectie
            with st.expander("🗑️ Positie sluiten"):
                to_delete = st.selectbox("Selecteer aandeel om te verwijderen:", 
                                         options=[""] + df_subset['Ticker'].tolist(), 
                                         key=f"del_select_{label}")
                if st.button(f"Verwijder {to_delete} definitief", key=f"btn_{label}"):
                    if to_delete:
                        rec_id = df_subset[df_subset['Ticker'] == to_delete]['airtable_id'].values[0]
                        if delete_from_airtable(rec_id):
                            st.success(f"{to_delete} verwijderd!")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info(f"Geen actieve {label} posities gevonden.")

with tab1:
    render_section(growth_df, "Growth")

with tab2:
    render_section(div_df, "Dividend")

# Sidebar status
with st.sidebar:
    st.write("### Systeem Status")
    if not df.empty:
        st.success(f"Verbonden! ({len(df)} rijen in database)")
    else:
        st.warning("Database is leeg of kolomnamen kloppen niet.")
    
    if st.button("Forceer Refresh"):
        st.rerun()