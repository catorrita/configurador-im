import io
import openpyxl
import pandas as pd
import streamlit as st
from streamlit_handsontable import st_handsontable

# Configuração da página
st.set_page_config(page_title="Planilha Interativa", layout="wide")

# ==========================================
# 1. BOTÕES NO TOPO
# ==========================================
col_voltar, col_espaco, col_exportar = st.columns([2, 5, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")

# Inicializa matriz de dados em branco (15 linhas x 8 colunas)
if "dados_planilha" not in st.session_state:
  st.session_state.dados_planilha = [["" for _ in range(8)] for _ in range(15)]


# Função para exportar para .xlsx
def exportar_para_excel(matriz_dados):
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  colunas = ["A", "B", "C", "D", "E", "F", "G", "H"]
  ws.append(colunas)

  for linha in matriz_dados:
    linha_convertida = []
    for cell in linha:
      if cell is None:
        linha_convertida.append("")
      else:
        cell_str = str(cell).strip()
        if cell_str.replace(".", "", 1).replace("-", "", 1).isdigit():
          linha_convertida.append(
              float(cell_str) if "." in cell_str else int(cell_str)
          )
        else:
          linha_convertida.append(cell)
    ws.append(linha_convertida)

  buffer = io.BytesIO()
  wb.save(buffer)
  buffer.seek(0)
  return buffer


with col_exportar:
  excel_bytes = exportar_para_excel(st.session_state.dados_planilha)
  st.download_button(
      label="📥 Exportar Planilha",
      data=excel_bytes,
      file_name="planilha_calculada.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA COM FÓRMULAS INTERATIVAS
# ==========================================
st.title("📊 Planilha Interativa")
st.caption(
    "Digite fórmulas diretamente nas células como `=B1+C1`, `=SUM(B1:C5)`,"
    " `=AVERAGE(...)` etc."
)

# Envolva o componente em um container fixo com chave única para evitar erro no DOM
container_grid = st.container()

with container_grid:
  resultado = st_handsontable(
      st.session_state.dados_planilha,
      colHeaders=["A", "B", "C", "D", "E", "F", "G", "H"],
      rowHeaders=True,
      formulas=True,  # Habilita fórmulas no navegador
      contextMenu=True,
      height=500,
      licenseKey="non-commercial-and-evaluation",
      key="handsontable_grid_main",  # Chave única para evitar conflitos de renderização
  )

# Atualiza a sessão silenciosamente
if resultado and isinstance(resultado, dict) and "data" in resultado:
  st.session_state.dados_planilha = resultado["data"]