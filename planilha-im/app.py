import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Configurador Instalações Mecânicas Fockink", layout="wide")

# Conexão com o Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inicializa o estado de login
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_email"] = ""

# --- BLOQUEIO DE SEGURANÇA E OCULTAÇÃO DO MENU SE NÃO LOGADO ---
if not st.session_state["autenticado"]:
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>CONFIGURADOR INSTALAÇÕES MECÂNICAS FOCKINK</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Acesso ao Sistema")
        with st.form("form_login"):
            email_input = st.text_input("E-mail")
            senha_input = st.text_input("Senha", type="password")
            
            botao_entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            
            if botao_entrar:
                if not email_input or not senha_input:
                    st.warning("Por favor, preencha o e-mail e a senha.")
                else:
                    try:
                        email_limpo = email_input.strip().lower()
                        # Consulta na tabela de LOGIN do Supabase
                        response = supabase.table("LOGIN").select("*").execute()
                        todos_usuarios = response.data
                        
                        usuario_encontrado = None
                        for u in todos_usuarios:
                            if u["EMAIL"].strip().lower() == email_limpo:
                                usuario_encontrado = u
                                break
                        
                        if not usuario_encontrado:
                            st.error("E-mail não cadastrado, procure o administrador.")
                        else:
                            if senha_input == str(usuario_encontrado["SENHA"]):
                                st.session_state["autenticado"] = True
                                st.session_state["usuario_email"] = email_limpo
                                st.success("Login realizado com sucesso!")
                                
                                # Redireciona imediatamente para a tela de menu
                                st.switch_page("pages/menu.py")
                            else:
                                st.error("Senha incorreta.")
                    except Exception as e:
                        st.error(f"Erro ao conectar com o banco de dados: {e}")
                        
    st.stop()

# Se por acaso já estiver autenticado e abrir o app.py, vai direto para o menu também
st.switch_page("pages/menu.py")
