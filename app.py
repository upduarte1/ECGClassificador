import streamlit as st
import gspread
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
    
    # Upload manual do Excel de sinais
    if "ecg_signals" not in st.session_state:
        st.session_state.ecg_signals = None
    
    st.subheader("📥 Upload ECGs File")
    uploaded_file = st.file_uploader("Load the ECG signals file (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        
        try:
            df = pd.read_excel(uploaded_file)
            st.session_state.ecg_signals = df
            st.success("File loaded with success!")
            
        except Exception as e:
            st.error(f"Error loading ECG file: {e}")
            st.stop()
            
    if st.session_state.ecg_signals is None:
        st.warning("Please, load the excel file with the ECGs to continue.")
        st.stop()
    
    df_ecg = st.session_state.ecg_signals
    required_columns = {"signal_id", "ecg_signal", "heart_rate", "date", "num_beats", "mean_bpm", "sdnn", "rmssd", "ap_entropy", "snr_index"}
    
    if not required_columns.issubset(df_ecg.columns):
        st.error("Excel file should have the following columns: 'signal_id', 'ecg_signal', 'heart_rate', 'date', 'num_beats', 'mean_bpm', 'sdnn', 'rmssd', 'ap_entropy', 'snr_index'")
        st.stop()
    
    all_signal_ids = df_ecg["signal_id"].astype(int).tolist()
    
    username = st.session_state.username
    user_display_name = username.title()
    st.sidebar.success(f"Welcome, Dr. {user_display_name}")
    role = ROLES.get(username, "unknown")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    st.title("ECG Signal Classifier")

    def get_signal_by_id(signal_id: int):
        row = df_ecg[df_ecg["signal_id"] == signal_id]
        if row.empty:
            raise ValueError(f"Signal with ID {signal_id} not found.")
        ecg_str = row.iloc[0]["ecg_signal"]
        heart_rate = float(row.iloc[0]["heart_rate"])
        values = [float(v.strip()) for v in str(ecg_str).split(",") if v.strip() not in ("", "-")]
        return values, heart_rate

    # Connect to Google Sheets
    def connect_sheets():
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scopes)
        client = gspread.authorize(credentials)
        classification_sheet = client.open("ECG Classificações").worksheet("Folha1")
        return classification_sheet

    # Connect and load data
    classification_sheet = connect_sheets()
    if st.session_state.ecg_signals is None:
        st.warning("Please, load the ECG file to continue.")
        st.stop()
    df_ecg = st.session_state.ecg_signals
    if "signal_id" not in df_ecg.columns or "ecg_signal" not in df_ecg.columns or "heart_rate" not in df_ecg.columns:
        st.error("The file should contain the columns: signal_id, ecg_signal, heart_rate")
        st.stop()
    all_signal_ids = df_ecg["signal_id"].astype(int).tolist()
    
    # Load all classification records here
    records = classification_sheet.get_all_records()
    
    # Select signals based on user role
    if role == "classifier":
        
        already_classified_ids = {r['signal_id'] for r in records if r['cardiologist'] == username}
        available_signals = [sid for sid in all_signal_ids if sid not in already_classified_ids]
        total_signals = len(all_signal_ids)
        num_classified = len(already_classified_ids)
        st.info(f"Signals classified: {num_classified} / {total_signals}")
    
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
        st.info(f"Conflict signals reviewed: {num_reviewed} / {total_conflicts}")
        available_signals = [k for k in conflicting_signals if k not in already_classified_ids]

    else:
        
        st.error("Unknown user role. Please contact administrator.")
        st.stop()

    # Show signal to classify
    if available_signals:
        
        signal_id = available_signals[0]

        def show_ecg_plot(signal, sampling_frequency=300, signal_id=None, duration=30):
            signal = np.array(signal, dtype=float)
            signal = signal[np.isfinite(signal)]
            if len(signal) == 0:
                st.warning(f"ECG signal ID {signal_id} is empty or invalid.")
                return
            samples_to_show = int(duration * sampling_frequency)
            signal = signal[:samples_to_show]
            # Escala: 25 mm/s → ≈ 0.984 inch/s, para 10 segundos → ~9.84 inches
            mm_per_second = 25
            dpi = 300
            inches_per_second = mm_per_second / 25.4
            width_in_inches = 10 * inches_per_second  # Cada faixa = 10s
            height_in_inches = 2  # Altura de cada faixa        
            fig, axs = plt.subplots(3, 1, figsize=(width_in_inches, height_in_inches * 3), dpi=dpi, sharey=True)
            for i in range(3):
                start = i * 10 * sampling_frequency
                end = (i + 1) * 10 * sampling_frequency
                s_segment = signal[start:end]
                t_segment = np.arange(len(s_segment)) / sampling_frequency
                ax = axs[i]
                ax.plot(t_segment + i * 10, s_segment, color='black', linewidth=0.8)
                ax.set_xlim([0, 10])
                ax.set_xlim([i * 10, (i + 1) * 10])
                ax.set_ylim([-1500, 1500])                
                ax.set_facecolor("white")        
                ax.set_xticks(np.arange(i * 10, (i + 1) * 10 + 1, 1))
                ax.set_yticks(np.arange(-1500, 1601, 500))
                ax.set_yticklabels([])
                if i == 2:
                    ax.set_xlabel("Tempo (s)")
                if i == 1:
                    ax.set_ylabel("ECG (μV)")
                for j in np.arange(i * 10, (i + 1) * 10, 0.2):  # vertical grid lines (5mm = 0.2s)
                    ax.axvline(j, color='red', linewidth=0.5, alpha=0.3)
                for j in np.arange(i * 10, (i + 1) * 10, 0.04):  # vertical grid lines (1mm = 0.04s)
                    ax.axvline(j, color='red', linewidth=0.5, alpha=0.1)
                for j in np.arange(-1500, 1600, 500):  # 5 mm = 0.5 mV = 500 μV
                    ax.axhline(j, color='red', linewidth=0.5, alpha=0.3)
                for j in np.arange(-1500, 1600, 100):  # 1 mm = 0.1 mV = 100 μV
                    ax.axhline(j, color='red', linewidth=0.5, alpha=0.1)
            fig.suptitle(f"ECG Signal ID {signal_id}" if signal_id else "ECG Signal", fontsize=14)
            plt.tight_layout()
            # Mostrar imagem com qualidade ideal
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=dpi, bbox_inches='tight')
            buf.seek(0)
            st.image(buf, use_container_width=True)

        try:
            
            signal_data, heart_rate = get_signal_by_id(signal_id)
            show_ecg_plot(signal_data, sampling_frequency=300, signal_id=signal_id)
            row_info = df_ecg[df_ecg["signal_id"] == signal_id].iloc[0]
            st.markdown("### Signal Features")
            
            date_only = row_info["date"]
            if isinstance(date_only, str):
                date_only = date_only.split()[0]
            elif isinstance(date_only, datetime):
                date_only = date_only.date().isoformat()
            
            st.markdown(f"""
                - **Date:** {date_only}
                - **Mean Heart Rate (wearable):** {row_info["heart_rate"]} bpm
                - **Mean Heart Rate (peak detector):** {int(round(row_info["mean_bpm"]))} bpm
                - **Number of Beats:** {row_info["num_beats"]}
                - **SDNN:** {round(row_info["sdnn"] * 1000, 2)} ms
                - **RMSSD:** {round(row_info["rmssd"] * 1000, 2)} ms
                - **Approximation Entropy:** {round(row_info["ap_entropy"], 2)}
                - **SNR Index:** {round(row_info["snr_index"], 2)}
            """)
            
        except Exception as e:
            st.error(f"Error loading ECG signal {signal_id}: {e}")
            st.stop()

        col1, col2, col3, col4 = st.columns(4)
        
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
        
        st.info("You have classified all available signals! Thank you!")
