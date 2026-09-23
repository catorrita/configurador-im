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
TOTAL_LINHAS = 30

# Inicializa as estruturas na sessão
if "df_valores" not in st.session_state:
  dados_vazios = [["" for _ in COLUNAS_EXCEL] for _ in range(TOTAL_LINHAS)]
  st.session_state.df_valores = pd.DataFrame(
      dados_vazios,
      columns=COLUNAS_EXCEL,
      index=[f"{i+1}" for i in range(TOTAL_LINHAS)],
  )

if "mapa_formulas" not in st.session_state:
  st.session_state.mapa_formulas = (
      {}
  )  # Guarda as fórmulas de cada célula (ex: 'C1': '=A1+B1')


# Função que calcula e reavalia todas as fórmulas da planilha
def recalcular_planilha():
  # Inicia com os valores manuais/diretos
  df_calc = st.session_state.df_valores.copy()

  # Recalcula as células que possuem fórmula
  for celula_ref, formula in st.session_state.mapa_formulas.items():
    col_letra = re.match(r"([A-Z]+)", celula_ref).group(1)
    lin_num = int(re.search(r"(\d+)", celula_ref).group(1)) - 1

    try:
      expressao = formula[1:].upper()

      # Substitui todas as referências de células (ex: A1, B1) pelos valores atuais
      referencias = re.findall(r"[A-Z]+\d+", expressao)
      for ref in referencias:
        ref_col = re.match(r"([A-Z]+)", ref).group(1)
        ref_lin = int(re.search(r"(\d+)", ref).group(1)) - 1

        if ref_col in COLUNAS_EXCEL and 0 <= ref_lin < TOTAL_LINHAS:
          val_celula = str(
              st.session_state.df_valores.iat[
                  ref_lin, COLUNAS_EXCEL.index(ref_col)
              ]
          ).strip()
          val_num = (
              val_celula
              if val_celula.replace(".", "", 1).replace("-", "", 1).isdigit()
              else "0"
          )
          expressao = expressao.replace(ref, val_num)

      resultado = eval(expressao)
      df_calc.iat[lin_num, COLUNAS_EXCEL.index(col_letra)] = (
          round(resultado, 4) if isinstance(resultado, float) else resultado
      )
    except Exception:
      df_calc.iat[lin_num, COLUNAS_EXCEL.index(col_letra)] = "#ERRO!"

  return df_calc


# Exportação em Excel
def gerar_excel():
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(COLUNAS_EXCEL)

  df_export = st.session_state.df_valores.copy()
  for celula_ref, formula in st.session_state.mapa_formulas.items():
    col_letra = re.match(r"([A-Z]+)", celula_ref).group(1)
    lin_num = int(re.search(r"(\d+)", celula_ref).group(1)) - 1
    df_export.iat[lin_num, COLUNAS_EXCEL.index(col_letra)] = formula

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
# 2. BARRA DE FÓRMULAS ESTILO EXCEL (fx)
# ==========================================
st.title("Planilha Interativa")

# Lista de todas as células possíveis para o Seletor (A1, B1, C1...)
opcoes_celulas = [
    f"{col}{lin}" for lin in range(1, TOTAL_LINHAS + 1) for col in COLUNAS_EXCEL
]

col_celula, col_fx, col_aplicar = st.columns([1.5, 6, 2.5])

with col_celula:
  celula_selecionada = st.selectbox(
      "Célula", opcoes_celulas, index=opcoes_celulas.index("C1")
  )

# Obtém o conteúdo atual da célula selecionada (fórmula ou valor)
conteudo_atual = st.session_state.mapa_formulas.get(
    celula_selecionada,
    str(
        st.session_state.df_valores.iat[
            int(re.search(r"(\d+)", celula_selecionada).group(1)) - 1,
            COLUNAS_EXCEL.index(
                re.match(r"([A-Z]+)", celula_selecionada).group(1)
            ),
        ]
    ),
)

with col_fx:
  entrada_formula = st.text_input(
      "Barra de Fórmulas (fx)",
      value=conteudo_atual,
      key=f"input_{celula_selecionada}",
      placeholder="Digite um valor ou formula ex: =A1+B1",
  )

with col_aplicar:
  st.write("")  # Alinhamento
  st.write("")
  if st.button(
      "📌 Inserir / Atualizar", use_container_width=True, type="primary"
  ):
    col_letra = re.match(r"([A-Z]+)", celula_selecionada).group(1)
    lin_num = int(re.search(r"(\d+)", celula_selecionada).group(1)) - 1
    val_digitado = entrada_formula.strip()

    if val_digitado.startswith("="):
      st.session_state.mapa_formulas[celula_selecionada] = val_digitado
    else:
      st.session_state.mapa_formulas.pop(celula_selecionada, None)
      st.session_state.df_valores.iat[
          lin_num, COLUNAS_EXCEL.index(col_letra)
      ] = val_digitado

    st.rerun()

# ==========================================
# 3. TABELA COM RESULTADOS E EDIÇÃO RÁPIDA
# ==========================================
df_visualizacao = recalcular_planilha()

df_editado = st.data_editor(
    df_visualizacao,
    use_container_width=True,
    height=500,
    key="grid_excel_fx",
)

# Sincroniza edições diretas feitas na tabela
alterou_grade = False
for r_idx in range(TOTAL_LINHAS):
  for c_idx in range(len(COLUNAS_EXCEL)):
    val_tela = str(df_editado.iat[r_idx, c_idx]).strip()
    val_original = str(df_visualizacao.iat[r_idx, c_idx]).strip()

    if val_tela != val_original:
      celula_nome = f"{COLUNAS_EXCEL[c_idx]}{r_idx+1}"
      alterou_grade = True
      if val_tela.startswith("="):
        st.session_state.mapa_formulas[celula_nome] = val_tela
      else:
        st.session_state.mapa_formulas.pop(celula_nome, None)
        st.session_state.df_valores.iat[r_idx, c_idx] = val_tela

if alterou_grade:
  st.rerun()
