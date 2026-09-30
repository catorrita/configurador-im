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

# Captura do e-mail do usuário
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
    """Carrega os dados da tabela do Supabase com tratamento de erros detalhado"""
    try:
        # Busca os registros da tabela exatamente como está no seu painel
        response = supabase.table("Base de Dados").select("*").limit(1000).execute()
        dados = response.data
        
        if dados and len(dados) > 0:
            return pd.DataFrame(dados)
        else:
            st.warning("⚠️ A tabela retornou vazia. Dica: Verifique se o RLS (Row Level Security) está ativo no Supabase bloqueando a leitura.")
            return pd.DataFrame(columns=["COD_SAP", "COD_SGE", "DESC_ITEM", "MODIF_POR"])
            
    except Exception as e:
        st.error(f"❌ Erro detalhado ao carregar do Supabase: {e}")
        return pd.DataFrame(columns=["COD_SAP", "COD_SGE", "DESC_ITEM", "MODIF_POR"])

def salvar_alteracoes_no_supabase(df_alterado):
    """Salva/Atualiza as alterações feitas na tabela de volta para o Supabase"""
    try:
        with st.spinner("💾 Salvando alterações no Supabase..."):
            registros = df_alterado.to_dict(orient="records")
            
            # Garante que o e-mail do usuário atualizador seja mantido nas linhas modificadas
            for reg in registros:
                if not reg.get("MODIF_POR"):
                    reg["MODIF_POR"] = USER_EMAIL

            # O .upsert atualiza se já existir (baseado na chave primária) ou insere se for novo
            supabase.table("Base de Dados").upsert(registros).execute()
            
        st.success("✅ Dados salvos com sucesso no Supabase!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar no Supabase: {e}")
        return False

# Inicializa os dados na sessão se não existirem
if "df_dados" not in st.session_state:
    st.session_state["df_dados"] = carregar_dados_do_supabase()

# ==========================================
# 4. INTERFACE DO USUÁRIO (UI)
# ==========================================

# Barra superior com botões de navegação e ações
col_voltar, col_status, col_salvar, col_atualizar = st.columns([2, 4, 2, 2])

with col_voltar:
    if st.button("← Ir ao Início", use_container_width=True):
        st.switch_page("app.py")  # Altere para o nome do arquivo inicial se necessário

with col_status:
    st.caption(f"✔️ Conectado ao Supabase | Usuário: {USER_EMAIL}")

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
st.info("💡 Você pode editar os campos diretamente na tabela abaixo e clicar em 'Salvar Alterações' no topo.")

# Exibe a tabela interativa do Streamlit
if not st.session_state["df_dados"].empty:
    st.session_state["df_editado"] = st.data_editor(
        st.session_state["df_dados"],
        use_container_width=True,
        height=600,
        key="editor_base_dados",
        num_rows="dynamic"
    )
else:
    st.warning("Nenhum dado encontrado para exibir na tabela.")
