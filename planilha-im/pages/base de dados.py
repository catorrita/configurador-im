import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Base de Dados", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📋 Base de Dados Geral")

try:
    # Tenta buscar os dados
    response = supabase.table("Base de Dados").select("*").execute()
    dados = response.data
    
    if dados and len(dados) > 0:
        df = pd.DataFrame(dados)
        df_editado = st.data_editor(df, use_container_width=True, height=500, key="editor_simples")
        
        if st.button("💾 Salvar Alterações", type="primary"):
            registros = df_editado.to_dict(orient="records")
            supabase.table("Base de Dados").upsert(registros).execute()
            st.success("Salvo com sucesso!")
            st.rerun()
    else:
        st.error("⚠️ A API conectou, mas retornou 0 linhas. **Motivo:** O RLS (Row Level Security) está ativo na tabela do Supabase. Vá no painel do Supabase -> tabela 'Base de Dados' -> desative o RLS ou clique em 'Add RLS policy' para permitir leitura pública (`SELECT`).")

except Exception as e:
    st.error(f"❌ Erro na consulta: {e}")
