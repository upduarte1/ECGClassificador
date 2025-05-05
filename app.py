import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np

# Authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Authorized users
USERS = {
    "user1": "1234",
    "user2": "1234",
    "user3": "1234"
}

# User roles
ROLES = {
    "user1": "classifier",
    "user2": "classifier",
    "user3": "reviewer"
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
    
    username = st.session_state.username
    user_display_name = username.title()
    st.sidebar.success(f"Welcome, Dr. {user_display_name}")
    role = ROLES.get(username, "unknown")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    st.title("ECG Signal Classifier")

    # Connect to Google Sheets
    def connect_sheets():
        
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scopes)
        client = gspread.authorize(credentials)

        classification_sheet = client.open("ECG Classificações").worksheet("Folha1")
        signal_sheet = client.open("ECG Dados").worksheet("Folha1")
        return classification_sheet, signal_sheet

    # Load signals from spreadsheet
    def load_signals(sheet):
        
        records = sheet.get_all_records()
        ecgs = {}
        heart_rates = {}
        
        for row in records:
            try:
                signal_id = int(row["signal_id"])
                heart_rate = float(row["heart_rate"])
                ecg_str = row["ecg_signal"]
                values = [float(v.strip()) for v in ecg_str.split(",") if v.strip()]
                ecgs[signal_id] = values
                heart_rates[signal_id] = heart_rate
            except Exception as e:
                st.warning(f"Erro ao processar o sinal {row.get('signal_id', '?')}: {e}")
                
        return ecgs, heart_rates

    # Connect and load data
    classification_sheet, signal_sheet = connect_sheets()
    ecgs, heart_rates = load_signals(signal_sheet)
    
    # Load all classification records here
    records = classification_sheet.get_all_records()
    
    # Select signals based on user role
    if role == "classifier":
        
        already_classified_ids = {r['signal_id'] for r in records if r['cardiologist'] == username}
        available_signals = [k for k in ecgs if k not in already_classified_ids]
    
        total_signals = len(ecgs)
        num_classified = len(already_classified_ids)
        st.info(f"📈 Signals classified: {num_classified} / {total_signals}")
    
    elif role == "reviewer":
        
        conflicts = {}
        for r in records:
            sid = r["signal_id"]
            doctor = r["cardiologist"]
            label = r["classification"]
    
            if sid not in conflicts:
                conflicts[sid] = {}
            conflicts[sid][doctor] = label
    
        conflicting_signals = [
            sid for sid, votes in conflicts.items()
            if "user1" in votes and "user2" in votes and votes["user1"] != votes["user2"]
        ]
    
        already_classified_ids = {r['signal_id'] for r in records if r['cardiologist'] == username}
        num_reviewed = len([sid for sid in conflicting_signals if sid in already_classified_ids])
        total_conflicts = len(conflicting_signals)
        st.info(f"📈 Conflict signals reviewed: {num_reviewed} / {total_conflicts}")
    
        available_signals = [k for k in conflicting_signals if k not in already_classified_ids]

    else:
        st.error("Unknown user role. Please contact administrator.")
        st.stop()

    # Show signal to classify
    if available_signals:
        
        signal_id = available_signals[0]
        st.subheader(f"Signal ID: {signal_id}")
        # st.line_chart(ecgs[signal_id])


        def plot_ecg_scaled(ecg_signal, sampling_rate=300, signal_id=""):

            duration = len(ecg_signal) / sampling_rate
            time_sec = np.linspace(0, duration, len(ecg_signal))  # Tempo real em segundos
        
            fig, ax = plt.subplots(figsize=(15, 5), dpi=100)
        
            # Grade fina (1 mm = 0.04 s)
            minor_x = np.arange(0, duration, 0.04)
            minor_y = np.arange(-500, 1500, 0.1)
            ax.set_xticks(minor_x, minor=True)
            ax.set_yticks(minor_y, minor=True)
            ax.grid(which='minor', color='red', linestyle='-', linewidth=0.2)
        
            # Grade grossa (5 mm = 0.2 s)
            major_x = np.arange(0, duration, 0.2)
            major_y = np.arange(-500, 1500, 0.5)
            ax.set_xticks(major_x)
            ax.set_yticks(major_y)
            ax.grid(which='major', color='red', linestyle='-', linewidth=0.6)
        
            # ECG plot
            ax.plot(time_sec, ecg_signal, color='black', linewidth=1)
            ax.set_xlim([0, duration])
            ax.set_ylim([-1.5, 1.5])  # ou ajusta conforme tua amplitude real
        
            ax.set_title(f"ECG Signal ID {signal_id} ({duration:.0f}s)")
            ax.set_xlabel("Tempo (segundos)")
            ax.set_ylabel("Amplitude (mV)\n[10 mm = 1 mV]")
        
            st.pyplot(fig)



        plot_ecg(ecgs[signal_id], sampling_rate=300, signal_id=signal_id)
    
        
        st.write(f"Heart Rate: {heart_rates[signal_id]} bpm")

        # st.write("Classify this signal:")
        col1, col2, col3, col4 = st.columns(4)

        # Classification buttons
        def select_label(label):
            st.session_state.temp_label = label

        if "temp_label" not in st.session_state:
            st.session_state.temp_label = None
        if "temp_comment" not in st.session_state:
            st.session_state.temp_comment = ""

        with col1:
            if st.button("⚠️ Fibrillation"):
                select_label("Fibrillation")
        with col2:
            if st.button("✅ Normal"):
                select_label("Normal")
        with col3:
            if st.button("⚡ Noisy"):
                select_label("Noisy")
        with col4:
            if st.button("❓ Other"):
                select_label("Other")

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
        st.info("🎉 You have classified all available signals! Thank you!")
        
