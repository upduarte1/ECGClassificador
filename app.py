import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# 👥 Usuários autorizados
USUARIOS = {
    "joao": "1234",
    "maria": "abcd",
    "luisa": "senha123",
    "user5": "1234",
    "dudi": "1234"
}

# 🔐 Estado de autenticação
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""

# 🔑 Login
if not st.session_state.autenticado:
    st.title("Login")

    with st.form("login_form"):
        usuario = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if usuario in USUARIOS and senha == USUARIOS[usuario]:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# 🔁 App principal após login
else:
    nome = st.session_state.usuario
    nome_exibido = nome.title()
    st.sidebar.success(f"Bem vindo, Dr. {nome_exibido}")

    if st.sidebar.button("Logout"):
        st.session_state.autenticado = False
        st.session_state.usuario = ""
        st.rerun()

    st.title(f"Classificador de Sinais ECG")

    # 📂 Conectar às planilhas
    def connect_sheets():
        escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)
        cliente = gspread.authorize(credenciais)

        classificacoes_sheet = cliente.open("ECG Classificações").sheet1
        sinais_sheet = cliente.open("ECG Dados").sheet1
        return classificacoes_sheet, sinais_sheet

    # 📥 Carregar sinais da planilha
    def carregar_sinais(sheet):
        registros = sheet.get_all_records()
        ecgs = {}
        for linha in registros:
            try:
                signal_id = int(linha["signal_id"])
                ecg_str = linha["ecg_signal"]
                valores = [float(v.strip()) for v in ecg_str.split(",") if v.strip()]
                ecgs[signal_id] = valores
            except Exception as e:
                st.warning(f"Erro ao processar sinal {linha}: {e}")
        return ecgs

    # 🔄 Conectar e carregar dados
    classificacoes_sheet, sinais_sheet = connect_sheets()
    ecgs = carregar_sinais(sinais_sheet)

    # 📊 Progresso do usuário
    registros = classificacoes_sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}

    total_sinais = len(ecgs)
    num_classificados = len(ids_classificados)
    st.info(f"📈 Sinais classificados: {num_classificados} / {total_sinais}")

    # 📌 Exibir próximo sinal a classificar
    sinais_disponiveis = [k for k in ecgs if k not in ids_classificados]

    if sinais_disponiveis:
        sinal_id = sinais_disponiveis[0]
        st.subheader(f"Sinal ID: {sinal_id}")
        st.line_chart(ecgs[sinal_id])

        st.write("Classifique o sinal:")
        col1, col2, col3, col4 = st.columns(4)

        # 🔘 Funções de classificação
        def selecionar_rotulo(rotulo):
            st.session_state.rotulo_temp = rotulo

        if "rotulo_temp" not in st.session_state:
            st.session_state.rotulo_temp = None
        if "comentario_temp" not in st.session_state:
            st.session_state.comentario_temp = ""

        with col1:
            if st.button("⚠️ Fibrilhação"):
                selecionar_rotulo("Fibrilhação")
        with col2:
            if st.button("✅ Normal"):
                selecionar_rotulo("Normal")
        with col3:
            if st.button("⚡ Ruidoso"):
                selecionar_rotulo("Ruidoso")
        with col4:
            if st.button("❓ Outro"):
                selecionar_rotulo("Outro")

        if st.session_state.rotulo_temp:
            st.write(f"Você selecionou: **{st.session_state.rotulo_temp}**")
            st.session_state.comentario_temp = st.text_input("Comentário (opcional):", value=st.session_state.comentario_temp)

            if st.button("Confirmar classificação"):
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                classificacoes_sheet.append_row([
                    sinal_id,
                    nome,
                    st.session_state.rotulo_temp,
                    agora,
                    st.session_state.comentario_temp
                ])
                st.success(f"Sinal {sinal_id} classificado como '{st.session_state.rotulo_temp}'!")
                st.session_state.rotulo_temp = None
                st.session_state.comentario_temp = ""
                st.rerun()
    else:
        st.info("🎉 Você já classificou todos os sinais disponíveis! Obrigado!")
