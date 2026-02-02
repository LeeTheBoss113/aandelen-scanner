import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# VUL HIER JE GEGEVENS IN
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" # De 16 letters van Google zonder spaties
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. MAIL FUNCTIE (Aangepast naar Poort 587) ---
def stuur_dagelijkse_mail(strong_buys):
    vandaag = str(date.today())
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            if f.read().strip() == vandaag:
                return

    inhoud = f"Holy Grail Scanner Update ({vandaag}):\n\n"
    for sb in strong_buys:
        inhoud += f"💎 {sb['Ticker']} | Score: {sb['Score']} | 1J Trend: {sb['Trend1J']}\n"
    
    msg = MIMEText(inhoud)
    msg['Subject'] = f"🎯 Holy Grail Alert: {len(strong_buys)} Strong Buys"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        # Geb
