import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# Conectar à planilha
def conectar_planilha():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open("ECG Classificações")
    return planilha.sheet1

sheet = conectar_planilha()

# Simular sinais
ecgs = {
    101: [0.01, 0.03, 0.05, 0.02],
    102: [0.04, 0.02, 0.03, 0.01],
    103: [0.05, 0.06, 0.04, 0.03]
}

# Nome do médico
st.title("Classificador de Sinais ECG")
nome = st.text_input("Identifique-se:", max_chars=50)

if nome:
    registros = sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}
    sinais_disponiveis = [k for k in ecgs if k not in ids_classificados]

    if sinais_disponiveis:
        # Garantir que o estado está inicializado
        if "rotulo_escolhido" not in st.session_state:
            st.session_state.rotulo_escolhido = None

        sinal_id = sinais_disponiveis[0]
        st.subheader(f"Sinal ID: {sinal_id}")
        st.line_chart(ecgs[sinal_id])

        rotulo = st.radio(
            "Classificação:",
            ["Normal", "Arritmia", "Fibrilação", "Outro"],
            index=None,
            key="rotulo_escolhido"
        )

        if st.button("➡️ Seguinte"):
            if st.session_state.rotulo_escolhido:
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([sinal_id, nome, st.session_state.rotulo_escolhido, agora])
                # Reset do estado e forçar rerun
                st.session_state.pop("rotulo_escolhido", None)
                st.experimental_rerun()
            else:
                st.warning("⚠️ Escolha uma classificação antes de continuar.")
    else:
        st.info("🎉 Todos os sinais já foram classificados!")
