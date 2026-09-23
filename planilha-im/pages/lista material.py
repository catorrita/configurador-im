import io
import re
import openpyxl
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Planilha Interativa", layout="wide")

# ==========================================
# 1. BARRA SUPERIOR E NAVEGAÇÃO
# ==========================================
col_voltar, col_espaco, col_exportar = st.columns([2, 5, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")

COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))]  # Colunas A até T
TOTAL_LINHAS = 30

# Estrutura principal: guarda o que o usuário digita (valores ou fórmulas)
if "matriz_raw" not in st.session_state:
  st.session_state.matriz_raw = {
      f"{col}{lin}": ""
      for lin in range(1, TOTAL_LINHAS + 1)
      for col in COLUNAS_EXCEL
  }


# Função auxiliar para obter valor numérico de uma referência de célula
def obter_valor_numerico(ref, mapa_dados, historico_visitados=None):
  if historico_visitados is None:
    historico_visitados = set()

  if ref in historico_visitados:  # Previne referência circular
    return 0.0

  historico_visitados.add(ref)
  conteudo = str(mapa_dados.get(ref, "")).strip()

  if not conteudo:
    return 0.0

  if conteudo.startswith("="):
    return avaliar_formula(conteudo, mapa_dados, historico_visitados)

  try:
    return float(conteudo.replace(",", "."))
  except ValueError:
    return 0.0


# Avaliador matemático de fórmulas (ex: =A1+B1, =A1*2, =A1-B1)
def avaliar_formula(formula_str, mapa_dados, historico_visitados=None):
  try:
    expressao = formula_str[1:].upper().strip()

    # Identifica todas as referências de células (ex: A1, B12, C3)
    refs = re.findall(r"\b[A-Z]+\d+\b", expressao)

    # Substitui cada referência pelo seu valor numérico correspondente
    for ref in refs:
      val = obter_valor_numerico(ref, mapa_dados, historico_visitados)
      expressao = re.sub(r"\b" + ref + r"\b", str(val), expressao)

    # Trata operadores comuns
    expressao = expressao.replace("^", "**")

    # Avalia a expressão matemática tratada
    resultado = eval(expressao, {"__builtins__": None}, {})

    if isinstance(resultado, float):
      return (
          int(resultado) if resultado.is_integer() else round(resultado, 4)
      )
    return resultado
  except Exception:
    return "#ERRO!"


# Função que constrói o DataFrame visual para exibição
def gerar_dataframe_calculado():
  dados_grid = []
  mapa_raw = st.session_state.matriz_raw

  for lin in range(1, TOTAL_LINHAS + 1):
    linha_vals = []
    for col in COLUNAS_EXCEL:
      celula_ref = f"{col}{lin}"
      conteudo = str(mapa_raw.get(celula_ref, "")).strip()

      if conteudo.startswith("="):
        res = avaliar_formula(conteudo, mapa_raw)
        linha_vals.append("" if res is None else str(res))
      else:
        linha_vals.append(conteudo)
    dados_grid.append(linha_vals)

  df = pd.DataFrame(
      dados_grid,
      columns=COLUNAS_EXCEL,
      index=[f"{i}" for i in range(1, TOTAL_LINHAS + 1)],
  )
  return df


# Função para exportar arquivo Excel (.xlsx) preservando as fórmulas
def gerar_excel():
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(COLUNAS_EXCEL)

  for lin in range(1, TOTAL_LINHAS + 1):
    linha = []
    for col in COLUNAS_EXCEL:
      celula_ref = f"{col}{lin}"
      val = str(st.session_state.matriz_raw.get(celula_ref, "")).strip()

      if not val:
        linha.append("")
      elif (
          val.replace(".", "", 1).replace("-", "", 1).isdigit()
          and not val.startswith("=")
      ):
        linha.append(float(val) if "." in val else int(val))
      else:
        linha.append(val)
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
st.title("📊 Planilha Interativa")

opcoes_celulas = [
    f"{col}{lin}" for lin in range(1, TOTAL_LINHAS + 1) for col in COLUNAS_EXCEL
]

col_celula, col_fx = st.columns([2, 8])

with col_celula:
  celula_selecionada = st.selectbox("Célula", opcoes_celulas, index=0)

# Recupera o valor/fórmula armazenado na célula selecionada
val_atual = st.session_state.matriz_raw.get(celula_selecionada, "")

# Callback chamado ao pressionar Enter na Barra de Fórmulas
def atualizar_barra_fx():
  novo_texto = st.session_state[f"input_fx_{celula_selecionada}"]
  st.session_state.matriz_raw[celula_selecionada] = novo_texto.strip()


with col_fx:
  st.text_input(
      "Barra de Fórmulas (fx)",
      value=val_atual,
      key=f"input_fx_{celula_selecionada}",
      on_change=atualizar_barra_fx,
      placeholder="Digite um valor ou fórmula (ex: =A1+B1) e pressione Enter",
  )

# ==========================================
# 3. GRADE INTERATIVA
# ==========================================
df_exibicao = gerar_dataframe_calculado()

df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_excel_v5",
)

# Detecta alterações feitas diretamente nas células do Data Editor
houve_alteracao = False
for lin_idx, lin in enumerate(range(1, TOTAL_LINHAS + 1)):
  for col_idx, col in enumerate(COLUNAS_EXCEL):
    celula_ref = f"{col}{lin}"
    val_digitado_grid = str(df_editado.iat[lin_idx, col_idx]).strip()
    val_calculado_grid = str(df_exibicao.iat[lin_idx, col_idx]).strip()

    # Se o usuário alterou a célula na tabela diretamente
    if val_digitado_grid != val_calculado_grid:
      st.session_state.matriz_raw[celula_ref] = val_digitado_grid
      houve_alteracao = True

if houve_alteracao:
  st.rerun()
