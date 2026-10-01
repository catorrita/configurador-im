import streamlit as st

st.set_page_config(page_title="Configurador Instalações Mecânicas Fockink", layout="wide")

# Inicializa o estado de login
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_email"] = ""

# --- TELA DE LOGIN ---
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
                        from supabase import create_client
                        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                        
                        email_limpo = email_input.strip().lower()
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
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                    except Exception as e:
                        st.error(f"Erro ao conectar com o banco de dados: {e}")
                        
    st.stop()

# --- TELA DE MENU PRINCIPAL (Onde o usuário cai ao logar) ---
st.sidebar.title("Menu do Sistema")
st.sidebar.write(f"Logado como: **{st.session_state['usuario_email']}**")

if st.sidebar.button("🚪 Sair / Logout"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_email"] = ""
    st.rerun()
    
st.sidebar.markdown("---")

# Conteúdo da Página Inicial / Menu
st.title("🏠 Bem-vindo ao Configurador Fockink")
st.write("Utilize o menu lateral para navegar entre as opções disponíveis (Base de Dados, Lista de Material, etc.).")

# Se você quiser colocar atalhos visuais em botões na tela principal:
col1, col2 = st.columns(2)
with col1:
    st.info("📊 **Base de Dados**\n\nGerencie os códigos, SAPs e descrições dos itens.")
with col2:
    st.info("📦 **Lista de Material**\n\nConsulte e monte os materiais necessários.")
