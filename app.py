import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

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
        

        import matplotlib.pyplot as plt
        import numpy as np
        import streamlit as st
        
        # Parâmetros de amostragem e duração
        sampling_rate = 300  # Hz
        signal_duration_sec = 30  # duração do sinal (30 segundos)
        num_samples = sampling_rate * signal_duration_sec  # 9000 amostras
        
        # Gerando os dados do ECG (substitua por seus dados reais)
        ecg_values = ecgs[signal_id][:num_samples]
        time_axis = np.linspace(0, signal_duration_sec, num_samples)
        
        # Escala para 25 mm/s no eixo do tempo (300 Hz => 25 mm/s)
        # Para um gráfico de 30 segundos, a escala será ajustada para 25 mm/s
        time_axis_scaled = time_axis * 25  # 25 mm por segundo
        
        # Escala de amplitude para 10 mm = 1 mV
        ecg_values_scaled = np.array(ecg_values)  # Aqui você pode multiplicar por um fator para ajustar a amplitude (se necessário)
        
        # Criando o gráfico com Matplotlib
        fig, ax = plt.subplots(figsize=(15, 5))  # Tamanho do gráfico ajustado para 30s
        ax.plot(time_axis_scaled, ecg_values_scaled)
        
        # Ajustando a escala do gráfico
        ax.set_title(f"ECG Signal ID {signal_id} (30s)")
        ax.set_xlabel("Tempo (mm) [25 mm/s] - 30 segundos")
        ax.set_ylabel("Amplitude (mV) [10 mm = 1 mV]")
        
        # Adicionando a grade para simular papel milimétrico
        # Linhas no eixo X a cada 25 unidades (representando 25 mm/s, ou seja, 1 segundo)
        ax.grid(which='both', axis='x', linestyle='-', color='gray', linewidth=0.5)
        
        # Linhas no eixo Y a cada 10 unidades (representando 10 mm = 1 mV)
        ax.grid(which='both', axis='y', linestyle='-', color='gray', linewidth=0.5)
        
        # Adicionando linhas horizontais e verticais para simular a "grade" do papel milimétrico
        # Eixo X - Linhas verticais a cada 25 unidades (representando 25 mm/s, ou seja, cada segundo)
        for x in range(0, int(time_axis_scaled[-1]), 25):  # Cada 25 mm no eixo X
            ax.axvline(x=x, color='gray', linestyle='-', linewidth=0.5)
        
        # Eixo Y - Linhas horizontais a cada 10 unidades (representando 1 mV)
        for y in range(-2, 2, 1):  # Cada 1 mV no eixo Y (10mm)
            ax.axhline(y=y * 10, color='gray', linestyle='-', linewidth=0.5)
        
        # Exibindo o gráfico com o efeito de "papel milimétrico"
        st.markdown("<div style='overflow-x: auto;'>", unsafe_allow_html=True)
        st.pyplot(fig)  # Exibindo o gráfico Matplotlib
        st.markdown("</div>", unsafe_allow_html=True)




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
        
