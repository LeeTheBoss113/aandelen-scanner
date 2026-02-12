import streamlit as st
import pandas as pd
import requests
import json
import time

API_URL = "https://script.google.com/macros/s/AKfycbzbmiiW9CfjmchRe-2Ii0rKUWjB84MTdCC2hYAXkNosD9R4PzYR1Fwh0h8Wv4P7-XE3/exec"

def get_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}").json()
        df_a = pd.DataFrame(r['active'][1:], columns=r['active'][0])
        df_l = pd.DataFrame(r['log'][1:], columns=r['log'][0])
        return df_a, df_l
    except:
        return pd.DataFrame(columns=["Ticker","Inleg","Koers","Type"]), pd.DataFrame()

df_a, df_l = get_data()

st.title("🛡️ Stabiel Dashboard 2026")

# Splitsen op basis van kolom 'Type'
growth = df_a[df_a['Type'].astype(str).str.upper() == "GROWTH"]
dividend = df_a[df_a['Type'].astype(str).str.upper() == "DIVIDEND"]

tab1, tab2 = st.tabs(["🚀 Growth", "💎 Dividend"])

def render(df, p_type):
    st.dataframe(df, use_container_width=True, hide_index=True)
    with st.form(f"add_{p_type}"):
        t = st.text_input("Ticker")
        i = st.number_input("Inleg", 100)
        k = st.number_input("Koers")
        if st.form_submit_button("Toevoegen"):
            requests.post(API_URL, data=json.dumps({"ticker":t, "inleg":i, "koers":k, "type":p_type}))
            st.rerun()

with tab1: render(growth, "Growth")

with tab2: render(dividend, "Dividend")
