import streamlit as st
import gspread
from plotting import show_ecg_plot
from extracting import get_signal_by_id
from connecting import connect_sheets
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io

# Authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Authorized users
USERS = {
    "user1": "3759",
    "user2": "2901",
    "user3": "5178"
}

# User roles
ROLES = {
    "user1": "classifier",
    "user2": "classifier",
    "user3": "classifier"
}

# Login
if not st.session_state.authenticated:
    
    st.title("Login")
    
    with st.form("login_form"):
        
        username = st.selectbox("Username", list(USERS.keys()))
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            
            if username in USERS and password == USERS[username]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect password.")

# Main app after login
else:
    
    # Upload CSV file with ECG signals
    if "ecg_signals" not in st.session_state:
        st.session_state.ecg_signals = None
    
    st.subheader("Upload ECGs File")

    uploaded_file = st.file_uploader("Load the ECG signals file (.csv)", type=["csv"])
    
    if uploaded_file is not None:
        
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.ecg_signals = df
            st.success("File loaded with success!")
            
        except Exception as e:
            st.error(f"Error loading ECG file: {e}")
            st.stop()
            
    if st.session_state.ecg_signals is None:
        st.warning("Please, load the CSV file with the ECGs to continue.")
        st.stop()
    
    df_ecg = st.session_state.ecg_signals

    required_columns = {"SignalID", "HeartRate", "ECGSignal"}
    
    if not required_columns.issubset(df_ecg.columns):
        st.error("CSV file should have the following columns: 'SignalID', 'HeartRate', 'ECGSignal'")
        st.stop()

    all_signal_ids = df_ecg["SignalID"].astype(int).tolist()

    username = st.session_state.username

    user_display_name = username.title()

    st.sidebar.success(f"Welcome, Dr. {user_display_name}")

    role = ROLES.get(username, "unknown")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    st.title("ECG Signal Classifier")

    # Connect and load data
    classification_sheet = connect_sheets()

    if st.session_state.ecg_signals is None:
        st.warning("Please, load the ECG file to continue.")
        st.stop()
    
    if not {"SignalID", "ECGSignal", "HeartRate"}.issubset(df_ecg.columns):
        st.error("The file should contain the columns: SignalID, ECGSignal, HeartRate")
        st.stop()

    all_signal_ids = df_ecg["SignalID"].astype(int).tolist()
    
    # Load all classification records here
    records = classification_sheet.get_all_records()

    df_ecg = df_ecg.reset_index(drop=True)
    df_ecg["index_id"] = df_ecg.index + 1

    A = range(1, 501)
    B = range(501, 1001)
    C = range(1001, 1501)

    if username == "user1":
        assigned_indices = list(A) + list(B)
    elif username == "user2":
        assigned_indices = list(B) + list(C)
    elif username == "user3":
        assigned_indices = list(A) + list(C)
    else:
        st.error("Unknown user. Please contact administrator.")
        st.stop()
    
    assigned_df = df_ecg[df_ecg["index_id"].isin(assigned_indices)]
    assigned_signal_ids = assigned_df["SignalID"].astype(int).tolist()

    # Select signals based on user role
    if role == "classifier":
        already_classified_ids = {r['SignalID'] for r in records if r['cardiologist'] == username}
        available_signals = [sid for sid in assigned_signal_ids if sid not in already_classified_ids]
        total_signals = len(assigned_signal_ids)
        num_classified = len(already_classified_ids)
        st.info(f"Signals classified: {num_classified} / {total_signals}")
    
    elif role == "reviewer":
        conflicts = {}
        for r in records:
            sid = r["SignalID"]
            doctor = r["cardiologist"]
            label = r["classification"]
            if sid not in conflicts:
                conflicts[sid] = {}
            conflicts[sid][doctor] = label
        conflicting_signals = [
            sid for sid, votes in conflicts.items()
            if "user1" in votes and "user2" in votes and votes["user1"] != votes["user2"]
        ]
        already_classified_ids = {r['SignalID'] for r in records if r['cardiologist'] == username}
        num_reviewed = len([sid for sid in conflicting_signals if sid in already_classified_ids])
        total_conflicts = len(conflicting_signals)
        st.info(f"Conflict signals reviewed: {num_reviewed} / {total_conflicts}")
        available_signals = [k for k in conflicting_signals if k not in already_classified_ids]

    else:
        st.error("Unknown user role. Please contact administrator.")
        st.stop()

    # Show signal to classify
    if available_signals:
        
        signal_id = available_signals[0]

        try:
            signal_data, heart_rate = get_signal_by_id(signal_id, df_ecg)
            show_ecg_plot(signal_data, sampling_frequency=300, signal_id=signal_id)
            row_info = df_ecg[df_ecg["SignalID"] == signal_id].iloc[0]
            
        except Exception as e:
            st.error(f"Error loading ECG signal {signal_id}: {e}")
            st.stop()

        col1, col2, col3 = st.columns(3)
        
        def select_label(label):
            st.session_state.temp_label = label

        if "temp_label" not in st.session_state:
            st.session_state.temp_label = None
        if "temp_comment" not in st.session_state:
            st.session_state.temp_comment = ""
        
        with col1:
            if st.button("Atrial Fibrillation"):
               select_label("Atrial Fibrillation")
        with col2:
            if st.button("Sinus Rhythm"):
                select_label("Sinus Rhythm")
        with col3:
            if st.button("Inconclusive"):
                select_label("Inconclusive")

        if st.session_state.temp_label:
            
            st.write(f"You selected: **{st.session_state.temp_label}**")
            st.session_state.temp_comment = st.text_input("Comment (optional):", value=st.session_state.temp_comment)

            if st.button("Confirm classification"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                classification_sheet.append_row([
                    signal_id,
                    username,
                    st.session_state.temp_label,
                    now,
                    st.session_state.temp_comment
                ])
                st.success(f"Signal {signal_id} classified as '{st.session_state.temp_label}'!")
                st.session_state.temp_label = None
                st.session_state.temp_comment = ""
                st.rerun()
    else:
        
        st.info("You have classified all available signals! Thank you!")