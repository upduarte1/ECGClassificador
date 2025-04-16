import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
# 🔐 Configurar acesso ao Google Sheets
def conectar_planilha():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Carregar as credenciais dos Secrets da Streamlit Cloud
    credenciais = json.loads(st.secrets["GOOGLE_CREDENTIALS"])

    # Criar as credenciais a partir do dicionário JSON
    credenciais = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, escopos)

    # Autenticar e acessar a planilha
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
    # ⚠️ Pegar IDs já classificados
    registros = sheet.get_all_records()
    ids_classificados = {r['signal_id'] for r in registros if r['cardiologista'] == nome}
    
    # Filtrar apenas sinais ainda não classificados por esse médico
    sinais_disponiveis = [k for k in ecgs if k not in ids_classificados]
    
    if sinais_disponiveis:
        sinal_id = sinais_disponiveis[0]
        st.subheader(f"Sinal ID: {sinal_id}")
        st.line_chart(ecgs[sinal_id])
        
        st.write("Classifique o sinal:")
        col1, col2, col3, col4 = st.columns(4)
        
        def classificar(rotulo):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([sinal_id, nome, rotulo, agora])
            st.success(f"Sinal {sinal_id} classificado como '{rotulo}'!")
            st.rerun()
        
        # Estado temporário: rótulo e comentário
    if "rotulo_temp" not in st.session_state:
        st.session_state.rotulo_temp = None
    if "comentario_temp" not in st.session_state:
        st.session_state.comentario_temp = ""
    
    # Função para registrar escolha temporária
    def selecionar_rotulo(rotulo):
        st.session_state.rotulo_temp = rotulo
    
    # Botões de escolha
    with col1:
        if st.button("✅ Normal"):
            selecionar_rotulo("Normal")
    with col2:
        if st.button("⚠️ Arritmia"):
            selecionar_rotulo("Arritmia")
    with col3:
        if st.button("🔥 Fibrilação"):
            selecionar_rotulo("Fibrilação")
    with col4:
        if st.button("❓ Outro"):
            selecionar_rotulo("Outro")
    
    # Se o médico escolheu um rótulo
    if st.session_state.rotulo_temp:
        st.write(f"Você selecionou: **{st.session_state.rotulo_temp}**")
        st.session_state.comentario_temp = st.text_input("Comentário (opcional):", value=st.session_state.comentario_temp)
        
        if st.button("✅ Confirmar classificação"):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([
                sinal_id,
                nome,
                st.session_state.rotulo_temp,
                agora,
                st.session_state.comentario_temp
            ])
            st.success(f"Sinal {sinal_id} classificado como '{st.session_state.rotulo_temp}'!")
            
            # Limpar variáveis temporárias
            st.session_state.rotulo_temp = None
            st.session_state.comentario_temp = ""
            
            st.rerun()

    else:
        st.info("🎉 Você já classificou todos os sinais disponíveis!")
