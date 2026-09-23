import io
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Lista de Material", layout="wide")

# ==========================================
# 1. CABEÇALHO E NAVEGAÇÃO
# ==========================================
col_voltar, col_titulo = st.columns([1, 6])

with col_voltar:
  if st.button("← Voltar ao Início", use_container_width=True):
    # Direciona para o arquivo principal da raiz (ajuste para app.py se necessário)
    st.switch_page("app.py")

with col_titulo:
  st.title("📋 Lista de Material Interativa")

st.markdown(
    "Preencha ou altere os dados abaixo na tabela. Os totais serão"
    " atualizados automaticamente."
)
st.divider()


# ==========================================
# 2. CARREGAMENTO DOS DADOS (BASE / SESSÃO)
# ==========================================
@st.cache_data
def carregar_dados_base():
  try:
    # Tenta carregar os itens da base de dados existente
    df = pd.read_excel("dados.xlsx", dtype=str)
    # Garante que tenhamos colunas padrão para cálculo
    if "QUANTIDADE" not in df.columns:
      df["QUANTIDADE"] = 1
    if "VALOR_UNITARIO" not in df.columns:
      df["VALOR_UNITARIO"] = 0.0
  except Exception:
    # Caso o arquivo não exista ou dê erro, cria uma estrutura básica
    df = pd.DataFrame({
        "CÓDIGO SGE": ["397696", "397781"],
        "CÓDIGO SAP": ["2000043119", "2000043183"],
        "DESC_ITEM": [
            "PORTA DE AÇO CARBONO CAF 1000X 600MM 397696",
            "KIT PSI 15CV",
        ],
        "QUANTIDADE": [2, 1],
        "VALOR_UNITARIO": [150.00, 450.00],
    })

  # Garante tipos numéricos para cálculos na tela
  df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(1)
  df["VALOR_UNITARIO"] = pd.to_numeric(
      df["VALOR_UNITARIO"], errors="coerce"
  ).fillna(0.0)
  return df


# Mantém os dados editados no estado da sessão do Streamlit
if "df_lista_material" not in st.session_state:
  st.session_state.df_lista_material = carregar_dados_base()

# ==========================================
# 3. TABELA INTERATIVA (EDITOR EXCEL-LIKE)
# ==========================================
df_atual = st.session_state.df_lista_material.copy()

# Calcula a coluna 'TOTAL' dinamicamente para exibição na tela
df_atual["TOTAL"] = df_atual["QUANTIDADE"] * df_atual["VALOR_UNITARIO"]

# Configuração e exibição do editor de dados
df_editado = st.data_editor(
    df_atual,
    num_rows="dynamic",  # Permite adicionar e remover linhas como no Excel
    column_config={
        "CÓDIGO SGE": st.column_config.TextColumn(
            "CÓDIGO SGE", width="medium"
        ),
        "CÓDIGO SAP": st.column_config.TextColumn(
            "CÓDIGO SAP", width="medium"
        ),
        "DESC_ITEM": st.column_config.TextColumn("DESC_ITEM", width="large"),
        "QUANTIDADE": st.column_config.NumberColumn(
            "QUANTIDADE", min_value=1, step=1, format="%d"
        ),
        "VALOR_UNITARIO": st.column_config.NumberColumn(
            "VALOR UNITÁRIO (R$)", min_value=0.0, step=0.5, format="R$ %.2f"
        ),
        "TOTAL": st.column_config.NumberColumn(
            "TOTAL (R$)", format="R$ %.2f", disabled=True
        ),
    },
    hide_index=True,
    use_container_width=True,
)

# Atualiza a sessão
st.session_state.df_lista_material = df_editado

# ==========================================
# 4. RESUMO / DASHBOARD DE TOTAIS
# ==========================================
total_geral = df_editado["TOTAL"].sum()
total_itens = df_editado["QUANTIDADE"].sum()

c1, c2, c3 = st.columns(3)
c1.metric("Total de Linhas", len(df_editado))
c2.metric("Quantidade Total de Peças", f"{int(total_itens)}")
c3.metric("Valor Total da Lista", f"R$ {total_geral:,.2f}")

st.divider()


# ==========================================
# 5. GERADOR DE EXCEL COM FÓRMULAS
# ==========================================
def gerar_excel_com_formulas(df):
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Lista de Material"

  # Estilos do Excel
  header_fill = PatternFill(
      start_color="1F4E78", end_color="1F4E78", fill_type="solid"
  )
  header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
  bold_font = Font(name="Calibri", size=11, bold=True)
  center_align = Alignment(horizontal="center", vertical="center")

  # Cabeçalhos
  headers = [
      "CÓDIGO SGE",
      "CÓDIGO SAP",
      "DESC_ITEM",
      "QUANTIDADE",
      "VALOR UNITÁRIO",
      "TOTAL",
  ]
  ws.append(headers)

  for col_num in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = center_align

  # Preenchimento de dados e inclusão da FÓRMULA do Excel (=D*E)
  for idx, row in df.iterrows():
    row_num = idx + 2  # Linha do Excel (1 é o cabeçalho)
    sge = str(row.get("CÓDIGO SGE", ""))
    sap = str(row.get("CÓDIGO SAP", ""))
    desc = str(row.get("DESC_ITEM", ""))
    qtd = row.get("QUANTIDADE", 1)
    v_unit = row.get("VALOR_UNITARIO", 0.0)

    # Fórmula nativa do Excel para a coluna TOTAL
    formula_total = f"=D{row_num}*E{row_num}"

    ws.append([sge, sap, desc, qtd, v_unit, formula_total])

    # Formatação das células
    ws[f"D{row_num}"].number_format = "#,##0"
    ws[f"E{row_num}"].number_format = '"R$"#,##0.00'
    ws[f"F{row_num}"].number_format = '"R$"#,##0.00'

  # Linha de TOTAL GERAL com a fórmula =SOMA(...)
  ultima_linha = len(df) + 1
  linha_total = ultima_linha + 1

  ws.cell(row=linha_total, column=3, value="TOTAL GERAL").font = bold_font
  ws.cell(
      row=linha_total, column=4, value=f"=SUM(D2:D{ultima_linha})"
  ).font = bold_font
  ws.cell(
      row=linha_total, column=6, value=f"=SUM(F2:F{ultima_linha})"
  ).font = bold_font

  ws[f"D{linha_total}"].number_format = "#,##0"
  ws[f"F{linha_total}"].number_format = '"R$"#,##0.00'

  # Ajuste de largura das colunas no Excel
  ws.column_dimensions["A"].width = 15
  ws.column_dimensions["B"].width = 15
  ws.column_dimensions["C"].width = 50
  ws.column_dimensions["D"].width = 15
  ws.column_dimensions["E"].width = 18
  ws.column_dimensions["F"].width = 20

  # Salva o arquivo em memória
  buffer = io.BytesIO()
  wb.save(buffer)
  buffer.seek(0)
  return buffer


# ==========================================
# 6. BOTÃO DE DOWNLOAD
# ==========================================
excel_bytes = gerar_excel_com_formulas(df_editado)

st.download_button(
    label="📥 Baixar Planilha em Excel (.xlsx)",
    data=excel_bytes,
    file_name="lista_de_material.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    use_container_width=True,
)