import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# 🔐 Configurar acesso ao Google Sheets
def conectar_planilha():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open("ECG Classificações")
    return planilha.sheet1

sheet = conectar_planilha()

# Simulação de sinais (substituir depois)
ecgs = {
    101: [0.01, 0.03, 0.05, 0.02],
    102: [0.04, 0.02, 0.03, 0.01],
    103: [0.05, 0.06, 0.04, 0.03]
}

# 🔑 Nome do cardiologista
st.title("Classificador de Sinais ECG")
nome = st.text_input("Identifique-se:", max_chars=50)

if nome:
    st.session_state["nome"] = nome  # salvar no estado
    registros = sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}
    sinais_disponiveis = [k for k in ecgs if k not in ids_classificados]

    if sinais_disponiveis:
        # Se não tiver já salvo um sinal, salva o primeiro disponível
        if "sinal_id" not in st.session_state or st.session_state["sinal_id"] not in sinais_disponiveis:
            st.session_state["sinal_id"] = sinais_disponiveis[0]

        sinal_id = st.session_state["sinal_id"]

        st.subheader(f"Sinal ID: {sinal_id}")
        st.line_chart(ecgs[sinal_id])

        st.write("Classifique o sinal:")
        col1, col2, col3, col4 = st.columns(4)

        def classificar(rotulo):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([
                st.session_state["sinal_id"],
                st.session_state["nome"],
                rotulo,
                agora
            ])
            st.session_state["mensagem"] = f"Sinal {st.session_state['sinal_id']} classificado como '{rotulo}'!"
            del st.session_state["sinal_id"]  # limpa para pegar o próximo
            st.experimental_rerun()

        with col1:
            if st.button("✅ Normal"):
                classificar("Normal")
        with col2:
            if st.button("⚠️ Arritmia"):
                classificar("Arritmia")
        with col3:
            if st.button("🔥 Fibrilação"):
                classificar("Fibrilação")
        with col4:
            if st.button("❓ Outro"):
                classificar("Outro")

    else:
        st.info("🎉 Você já classificou todos os sinais disponíveis!")

if "mensagem" in st.session_state:
    st.success(st.session_state["mensagem"])
    del st.session_state["mensagem"]
