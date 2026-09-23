import io
import openpyxl
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Lista de Material", layout="wide")


# ==========================================
# 1. BOTÕES NO TOPO DA PÁGINA
# ==========================================
col_voltar, col_espaco, col_exportar = st.columns([2, 5, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")


# Inicializa uma planilha limpa de 15 linhas x 6 colunas na sessão
if "df_planilha" not in st.session_state:
  colunas = ["A", "B", "C", "D", "E", "F"]
  dados_vazios = [["" for _ in colunas] for _ in range(15)]
  st.session_state.df_planilha = pd.DataFrame(dados_vazios, columns=colunas)


# Função para gerar o arquivo .xlsx mantendo texto, números e fórmulas
def gerar_excel(df):
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  # Escreve o cabeçalho
  ws.append(list(df.columns))

  # Escreve cada linha
  for _, row in df.iterrows():
    linha_valores = []
    for val in row:
      if pd.isna(val) or val is None:
        linha_valores.append("")
      else:
        val_str = str(val).strip()
        # Se for número inteiro ou decimal, converte para salvar correto no Excel
        if val_str.replace(".", "", 1).replace("-", "", 1).isdigit():
          if "." in val_str:
            linha_valores.append(float(val_str))
          else:
            linha_valores.append(int(val_str))
        else:
          linha_valores.append(val_str)
    ws.append(linha_valores)

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
# 2. ÁREA DA PLANILHA INTERATIVA
# ==========================================
st.title("📊 Planilha de Materiais")
st.caption(
    "Edite as células abaixo. Você pode adicionar ou remover linhas livremente"
    " no botão '+' ou no ícone da lixeira. Ao digitar fórmulas como `=SUM(A1:A5)`"
    " ou `=A1+B1`, elas serão preservadas ao baixar o Excel."
)

# Editor nativo do Streamlit (funciona perfeitamente na nuvem)
df_editado = st.data_editor(
    st.session_state.df_planilha,
    num_rows="dynamic",  # Permite adicionar/remover linhas
    use_container_width=True,
    height=550,
)

# Atualiza a sessão
st.session_state.df_planilha = df_editado