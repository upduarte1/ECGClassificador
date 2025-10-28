import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# Connect to Google Sheets
def connect_sheets():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scopes)
    client = gspread.authorize(credentials)
    classification_sheet = client.open("ECG Classificações").worksheet("Folha1")
    return classification_sheet