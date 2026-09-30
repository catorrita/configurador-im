import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gerenciador Base de Dados - Supabase", 
    layout="wide"
)

# ==========================================
# 2. CONEXÃO COM O SUPABASE
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or st.secrets.get("connections", {}).get("supabase", {}).get("url", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or st.secrets.get("connections", {}).get("supabase", {}).get("key", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ As credenciais do Supabase não foram encontradas nos Secrets do Streamlit Cloud.")
    st.stop()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

USER_EMAIL = (
    st.session_state.get("user_email") 
    or st.session_state.get("email") 
    or getattr(st, "user", {}).get("email", None)
    or st.secrets.get("DEFAULT_USER_EMAIL", "felipe.binsfeld@fockind.ind.br")
)

# ==========================================
# 3. FUNÇÕES DE BANCO DE DADOS
# ==========================================
def carregar_dados_do_supabase():
    """Carrega os dados da tabela correta do Supabase"""
    try:
        # Puxa os dados da tabela exata do painel
        response = supabase.table("Base de Dados").select("*").limit(1000).execute()
        dados = response.data
        
        if dados and len(dados) > 0:
            return pd.DataFrame(dados)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar no Supabase: {e}")
        return pd.DataFrame()

def salvar_alteracoes_no_supabase(df_alterado):
    try:
        with st.spinner("💾 Salvando alterações no Supabase..."):
            registros = df_alterado.to_dict(orient="records")
            for reg in registros:
                if not reg.get("MODIF_POR"):
                    reg["MODIF_POR"] = USER_EMAIL
            
            # Upsert atualiza se já existir (baseado na chave primária) ou insere se for novo
            supabase.table("Base de Dados").upsert(registros).execute()
            
        st.success("✅ Dados salvos com sucesso no Supabase!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar no Supabase: {e}")
        return False

if "df_dados" not in st.session_state:
    st.session_state["df_dados"] = carregar_dados_do_supabase()

# ==========================================
# 4. INTERFACE DO USUÁRIO (UI)
# ==========================================

col_voltar, col_status, col_salvar, col_atualizar = st.columns([2, 4, 2, 2])

with col_voltar:
    if st.button("← Ir ao Início", use_container_width=True):
        st.switch_page("app.py")

with col_status:
    st.caption(f"✔️ Usuário: {USER_EMAIL}")

with col_salvar:
    if st.button("💾 Salvar Alterações", use_container_width=True, type="primary"):
        if "df_editado" in st.session_state:
            salvar_alteracoes_no_supabase(st.session_state["df_editado"])
            st.session_state["df_dados"] = carregar_dados_do_supabase()
            st.rerun()

with col_atualizar:
    if st.button("🔄 Recarregar Dados", use_container_width=True):
        st.session_state["df_dados"] = carregar_dados_do_supabase()
        st.rerun()

st.divider()

# ==========================================
# 5. GRADE INTERATIVA PARA EDIÇÃO
# ==========================================
st.subheader("📋 Base de Dados Geral")

if not st.session_state["df_dados"].empty:
    st.info("💡 Você pode editar os campos diretamente na tabela abaixo e clicar em 'Salvar Alterações' no topo.")
    st.session_state["df_editado"] = st.data_editor(
        st.session_state["df_dados"],
        use_container_width=True,
        height=600,
        key="editor_base_dados",
        num_rows="dynamic"
    )
else:
    st.warning("⚠️ Nenhum registro encontrado. Verifique se os Secrets do Streamlit Cloud estão configurados com as chaves corretas do projeto do Supabase.")
