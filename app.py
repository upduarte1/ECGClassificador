import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
    required_columns = {"signal_id", "ecg_signal", "heart_rate"}
    
    if not required_columns.issubset(df_ecg.columns):
        st.error("Excel file should have the following columns: 'signal_id', 'ecg_signal' e 'heart_rate'")
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
        # signal_sheet = client.open("ecg").worksheet("Folha1")
        return classification_sheet
    
    @st.cache_data(ttl=600)
    def load_signals_from_google_sheets():
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scopes)
        client = gspread.authorize(credentials)
    
        sheet = client.open("ecg").worksheet("Folha1")
        records = sheet.get_all_records()
    
        ecgs = {}
        heart_rates = {}
    
        for row in records:
            try:
                signal_id = int(row["signal_id"])
                heart_rate = float(row["heart_rate"])
                ecg_str = row["ecg_signal"]
    
                values = []
                for v in ecg_str.split(","):
                    v = v.strip()
                    if v == "-" or v == "":
                        continue
                    values.append(float(v))
    
                if values:
                    ecgs[signal_id] = values
                    heart_rates[signal_id] = heart_rate
    
            except Exception as e:
                st.warning(f"Error processing signal {row.get('signal_id', '?')}: {e}")
    
        return ecgs, heart_rates

    # Connect and load data
    classification_sheet = connect_sheets()
    # ecgs, heart_rates = load_signals(signal_sheet)
    # ecgs, heart_rates = load_signals_from_google_sheets()
    # signal_ids_sheet = signal_sheet.get_all_records()
    # all_signal_ids = [int(row["signal_id"]) for row in signal_ids_sheet]

    if st.session_state.ecg_signals is None:
        st.warning("Por favor, carregue o arquivo com os sinais ECG para continuar.")
        st.stop()
    
    df_ecg = st.session_state.ecg_signals
    if "signal_id" not in df_ecg.columns or "ecg_signal" not in df_ecg.columns or "heart_rate" not in df_ecg.columns:
        st.error("O arquivo CSV deve conter as colunas: signal_id, ecg_signal, heart_rate")
        st.stop()
    
    all_signal_ids = df_ecg["signal_id"].astype(int).tolist()

    
    # Load all classification records here
    records = classification_sheet.get_all_records()

    # if st.sidebar.checkbox("📄 See my previous classifications"):
    #    user_classifications = [r for r in records if r['cardiologist'] == username]
    #    if user_classifications:
    #        import pandas as pd
    #        df_user = pd.DataFrame(user_classifications)
    #        st.subheader("📄 My classifications")
    #        st.dataframe(df_user)
    #    else:
    #       st.info("You haven't done any classification.")
    
    # Select signals based on user role
    if role == "classifier":
        
        already_classified_ids = {r['signal_id'] for r in records if r['cardiologist'] == username}
        # available_signals = [k for k in ecgs if k not in already_classified_ids]
        # total_signals = len(ecgs)

        available_signals = [sid for sid in all_signal_ids if sid not in already_classified_ids]
        total_signals = len(all_signal_ids)
        
        num_classified = len(already_classified_ids)
        st.info(f"📈 Signals classified: {num_classified} / {total_signals}")
      
        progress_ratio = num_classified / total_signals
        st.progress(progress_ratio)
    
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

       
        def show_ecg_plot(signal, sampling_frequency=300, signal_id=None):
            import matplotlib.pyplot as plt
            import numpy as np
        
            signal = np.array(signal, dtype=float)
            signal = signal[np.isfinite(signal)]
        
            if len(signal) == 0:
                st.warning(f"ECG signal ID {signal_id} is empty or invalid.")
                return
        
            t = np.arange(len(signal)) / sampling_frequency
            duration = 30
            samples_to_show = int(duration * sampling_frequency)
            t = t[:samples_to_show]
            signal = signal[:samples_to_show]
        
            # Criar figura e eixos
            fig, ax = plt.subplots(figsize=(16, 6), dpi=100)
            ax.set_facecolor("white")
        
            # Limites e rótulos
            ax.set_xlim([0, 30])
            ax.set_ylim([-200, 500])
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("ECG (μV)")
            ax.set_title(f"ECG Signal ID {signal_id}" if signal_id else "ECG Signal")
        
            # Grade vermelha vertical (tempo)
            for i in np.arange(0, 30, 0.2):  # 5 mm = 0.2s
                ax.axvline(i, color='red', linewidth=0.5, alpha=0.3)
            for i in np.arange(0, 30, 0.04):  # 1 mm = 0.04s
                ax.axvline(i, color='red', linewidth=0.5, alpha=0.1)
        
            # Grade vermelha horizontal (amplitude)
            for i in np.arange(-200, 500, 50):  # 5 mm = 0.5mV ~ 50μV
                ax.axhline(i, color='red', linewidth=0.5, alpha=0.3)
            for i in np.arange(-200, 500, 10):  # 1 mm = 0.1mV ~ 10μV
                ax.axhline(i, color='red', linewidth=0.5, alpha=0.1)
        
            # Plotar sinal
            ax.plot(t, signal, color='black', linewidth=0.8)
        
            # Ticks
            ax.set_xticks(np.arange(0, 30.1, 2.5))
            ax.set_yticks(np.arange(-200, 550, 100))
        
            # Layout e exibição
            plt.tight_layout()
            st.pyplot(fig)

        try:
            signal_data, heart_rate = get_signal_by_id(signal_id)
            show_ecg_plot(signal_data, sampling_frequency=300, signal_id=signal_id)
            st.write(f"Heart Rate: {heart_rate} bpm")
        except Exception as e:
            st.error(f"Erro ao carregar sinal {signal_id}: {e}")
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
        st.info("🎉 You have classified all available signals! Thank you!")
        
