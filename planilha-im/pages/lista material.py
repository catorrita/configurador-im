import io
import openpyxl
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Planilha Interativa", layout="wide")

# ==========================================
# 1. BARRA SUPERIOR (BOTÕES NO TOPO)
# ==========================================
col_voltar, col_espaco, col_exportar = st.columns([2, 5, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")

# Inicializa matriz em branco se não existir na sessão
if "df_planilha" not in st.session_state:
  colunas = ["A", "B", "C", "D", "E", "F", "G", "H"]
  dados_vazios = [["" for _ in colunas] for _ in range(20)]
  st.session_state.df_planilha = pd.DataFrame(dados_vazios, columns=colunas)


# Função para exportar salvando todas as fórmulas e textos para o Excel
def gerar_excel(df):
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  # Escreve cabeçalho
  ws.append(list(df.columns))

  # Escreve dados preservando fórmulas como =A1+B1 ou =SUM(...)
  for _, row in df.iterrows():
    linha = []
    for val in row:
      if pd.isna(val) or val is None:
        linha.append("")
      else:
        val_str = str(val).strip()
        if (
            val_str.replace(".", "", 1).replace("-", "", 1).isdigit()
            and not val_str.startswith("=")
        ):
          linha.append(float(val_str) if "." in val_str else int(val_str))
        else:
          linha.append(val_str)
    ws.append(linha)

  wb.save(buffer)
  buffer.seek(0)
  return buffer


with col_exportar:
  excel_file = gerar_excel(st.session_state.df_planilha)
  st.download_button(
      label="📥 Exportar Planilha",
      data=excel_file,
      file_name="planilha_material.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA INTERATIVA
# ==========================================
st.title("📊 Planilha de Materiais")
st.caption(
    "Insira os dados livremente. Ao digitar fórmulas do Excel (como `=B1+C1` ou"
    " `=SUM(A1:A10)`), elas serão gravadas e ativadas no arquivo Excel ao"
    " baixar."
)

# Editor nativo do Streamlit (Sem erros de instalação no servidor)
df_editado = st.data_editor(
    st.session_state.df_planilha,
    num_rows="dynamic",  # Permite adicionar/remover linhas
    use_container_width=True,
    height=550,
    key="grid_editor_principal",
)

st.session_state.df_planilha = df_editado