import io
import re
import openpyxl
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Planilha Interativa", layout="wide")

# ==========================================
# 1. BARRA SUPERIOR
# ==========================================
col_voltar, col_espaco, col_exportar = st.columns([2, 5, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")

COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))]  # Colunas A até T

# Guardamos o DataFrame visível e o dicionário com as fórmulas originais
if "df_dados" not in st.session_state:
  dados_vazios = [["" for _ in COLUNAS_EXCEL] for _ in range(30)]
  st.session_state.df_dados = pd.DataFrame(
      dados_vazios,
      columns=COLUNAS_EXCEL,
      index=[f"Linha {i+1}" for i in range(30)],
  )

if "mapa_formulas" not in st.session_state:
  st.session_state.mapa_formulas = {}


# Função para recalcular dinamicamente todas as fórmulas ativas
def recalcular_planilha():
  df = st.session_state.df_dados.copy()

  for (r_idx, col_idx), formula in list(st.session_state.mapa_formulas.items()):
    try:
      expressao = formula[1:].upper()

      # Encontra referências de células como A1, B2, C10
      referencias = re.findall(r"[A-Z]+\d+", expressao)

      for ref in referencias:
        col_letra = re.match(r"([A-Z]+)", ref).group(1)
        lin_num = int(re.search(r"(\d+)", ref).group(1)) - 1

        if col_letra in COLUNAS_EXCEL and 0 <= lin_num < len(df):
          val_celula = str(df.iat[lin_num, COLUNAS_EXCEL.index(col_letra)]).strip()
          val_num = (
              val_celula
              if val_celula.replace(".", "", 1).replace("-", "", 1).isdigit()
              else "0"
          )
          expressao = expressao.replace(ref, val_num)

      resultado = eval(expressao)
      df.iat[r_idx, col_idx] = (
          round(resultado, 4) if isinstance(resultado, float) else resultado
      )
    except Exception:
      df.iat[r_idx, col_idx] = "#ERRO!"

  st.session_state.df_dados = df


# Gerador do arquivo Excel salvando as Fórmulas Reais (.xlsx)
def gerar_excel():
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(COLUNAS_EXCEL)

  df_export = st.session_state.df_dados.copy()

  for (r_idx, c_idx), formula in st.session_state.mapa_formulas.items():
    df_export.iat[r_idx, c_idx] = formula

  for _, row in df_export.iterrows():
    linha = []
    for val in row:
      val_str = str(val).strip()
      if not val_str:
        linha.append("")
      elif (
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
  excel_file = gerar_excel()
  st.download_button(
      label="📥 Exportar Planilha",
      data=excel_file,
      file_name="planilha.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA INTERATIVA
# ==========================================
st.title("Planilha Interativa")
st.caption(
    "Digite valores ou fórmulas como `=A1+B1` e pressione **Enter**. Se alterar"
    " A1 ou B1, o resultado atualiza automaticamente!"
)

# Renderiza a planilha na tela
df_editado = st.data_editor(
    st.session_state.df_dados,
    use_container_width=True,
    height=550,
    key="editor_dinamico_v4",
)

# Detecta o que o utilizador digitou de novo
precisa_recalcular = False

for r_idx in range(len(df_editado)):
  for c_idx in range(len(COLUNAS_EXCEL)):
    val_novo = str(df_editado.iat[r_idx, c_idx]).strip()
    val_antigo = str(st.session_state.df_dados.iat[r_idx, c_idx]).strip()

    if val_novo != val_antigo:
      precisa_recalcular = True
      if val_novo.startswith("="):
        # Registra a fórmula na célula
        st.session_state.mapa_formulas[(r_idx, c_idx)] = val_novo
      else:
        # Se digitou um número/texto comum, remove qualquer fórmula anterior dessa célula
        st.session_state.mapa_formulas.pop((r_idx, c_idx), None)
        st.session_state.df_dados.iat[r_idx, c_idx] = val_novo

if precisa_recalcular:
  recalcular_planilha()
  st.rerun()
