import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Base de Dados", layout="wide")

# Conexão simples lendo do secrets.toml
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]  # <-- TEM QUE SER A CHAVE 'anon' / 'public' (eyJ...)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📋 Base de Dados Geral")

# Busca os dados diretamente da tabela
try:
    response = supabase.table("Base de Dados").select("*").execute()
    dados = response.data
    
    if dados:
        df = pd.DataFrame(dados)
        
        # Exibe a tabela editável
        df_editado = st.data_editor(df, use_container_width=True, height=500, key="editor_simples")
        
        if st.button("💾 Salvar Alterações", type="primary"):
            # Salva de volta no Supabase
            registros = df_editado.to_dict(orient="records")
            supabase.table("Base de Dados").upsert(registros).execute()
            st.success("Salvo com sucesso!")
            st.rerun()
    else:
        st.warning("A tabela está vazia ou a chave incorreta.")

except Exception as e:
    st.error(f"Erro: {e}")
