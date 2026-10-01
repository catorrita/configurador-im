import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Base de Dados", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📋 Base de Dados Geral")

try:
    response = supabase.table("Base de Dados").select("*").execute()
    dados = response.data
    
    if dados and len(dados) > 0:
        df = pd.DataFrame(dados)
        
        # Garante a ordem correta exata das colunas para evitar mistura
        colunas_desejadas = ["COD_SAI", "COD_SGE", "DESC_ITEM", "MODIF_POR"]
        # Mantém apenas as colunas que existem no DataFrame
        colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
        df = df[colunas_existentes]
        
        df_editado = st.data_editor(df, use_container_width=True, height=500, key="editor_simples")
        
        if st.button("💾 Salvar Alterações", type="primary"):
            registros = df_editado.to_dict(orient="records")
            supabase.table("Base de Dados").upsert(registros).execute()
            st.success("Salvo com sucesso!")
            st.rerun()
    else:
        st.warning("A tabela está vazia.")

except Exception as e:
    st.error(f"Erro: {e}")
