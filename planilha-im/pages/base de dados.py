import pandas as pd
import streamlit as st

# Configuração da página no Streamlit
st.set_page_config(page_title="Consulta de Itens", layout="wide")

# 1. Botão "VOLTAR" (redireciona para a página principal se usar multipáginas)
col_voltar, _ = st.columns([1, 5])
with col_voltar:
  if st.button("← VOLTAR", use_container_width=True):
    # Altere "Home.py" ou "app.py" para o nome do seu arquivo principal na raiz
    st.switch_page("app.py")


# 2. Carregamento e Tratamento dos Dados
@st.cache_data
def carregar_dados():
  try:
    # Lê a planilha Excel mantendo tudo como texto (string)
    df = pd.read_excel("dados.xlsx", dtype=str)
    return df
  except Exception as e:
    st.error(f"Erro ao carregar o arquivo excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO SGE", "CÓDIGO SAP", "DESC_ITEM"])


df = carregar_dados()

st.title("Consulta de Itens")

# 3. Campo de Busca
termo_busca = st.text_input(
    "Pesquisar", placeholder="Pesquisar por código SGE, SAP ou descrição..."
)

# 4. Filtragem dos Dados
if termo_busca:
  termo = termo_busca.lower()
  df_exibir = df[
      df["CÓDIGO SGE"].astype(str).str.lower().str.contains(termo, na=False)
      | df["CÓDIGO SAP"].astype(str).str.lower().str.contains(termo, na=False)
      | df["DESC_ITEM"].astype(str).str.lower().str.contains(termo, na=False)
  ]
else:
  df_exibir = df

# 5. Exibição da Tabela
st.dataframe(
    df_exibir,
    column_config={
        "CÓDIGO SGE": st.column_config.TextColumn("CÓDIGO SGE", width="small"),
        "CÓDIGO SAP": st.column_config.TextColumn("CÓDIGO SAP", width="small"),
        "DESC_ITEM": st.column_config.TextColumn("DESC_ITEM", width="large"),
    },
    hide_index=True,
    use_container_width=True,
)