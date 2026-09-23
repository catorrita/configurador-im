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


# Função auxiliar para expandir intervalos (ex: "A1:A5" ou "E3:F9")
def expandir_intervalo(intervalo_str):
  intervalo_str = intervalo_str.strip().upper()
  if ":" not in intervalo_str:
    return [intervalo_str]

  inicio, fim = intervalo_str.split(":")
  col_ini, lin_ini = re.match(r"([A-Z]+)(\d+)", inicio).groups()
  col_fim, lin_fim = re.match(r"([A-Z]+)(\d+)", fim).groups()

  idx_col_ini = COLUNAS_EXCEL.index(col_ini)
  idx_col_fim = COLUNAS_EXCEL.index(col_fim)

  celulas = []
  for l in range(min(int(lin_ini), int(lin_fim)), max(int(lin_ini), int(lin_fim)) + 1):
    for c in range(min(idx_col_ini, idx_col_fim), max(idx_col_ini, idx_col_fim) + 1):
      celulas.append(f"{COLUNAS_EXCEL[c]}{l}")
  return celulas


# Função auxiliar para obter valor exato/resolvido de uma célula
def obter_valor_celula(ref, mapa_dados, historico_visitados=None):
  if historico_visitados is None:
    historico_visitados = set()

  if ref in historico_visitados:
    return 0.0

  historico_visitados.add(ref)
  conteudo = str(mapa_dados.get(ref, "")).strip()

  if not conteudo or conteudo.lower() == "none":
    return ""

  if conteudo.startswith("="):
    res = avaliar_formula(conteudo, mapa_dados, historico_visitados)
    return res if res != "#ERRO!" else ""

  return conteudo


# Função auxiliar para obter valor numérico
def obter_valor_numerico(ref, mapa_dados, historico_visitados=None):
  val = obter_valor_celula(ref, mapa_dados, historico_visitados)
  try:
    return float(str(val).replace(",", "."))
  except ValueError:
    return 0.0


# Função para dividir argumentos por vírgula ou ponto e vírgula respeitando aspas
def dividir_argumentos(args_str):
  # Normaliza delimitadores fora de aspas
  partes = []
  atual = []
  em_aspas = False
  caractere_aspas = None

  for char in args_str:
    if char in ('"', "'"):
      if not em_aspas:
        em_aspas = True
        caractere_aspas = char
      elif char == caractere_aspas:
        em_aspas = False
        caractere_aspas = None
      atual.append(char)
    elif char in (",", ";") and not em_aspas:
      partes.append("".join(atual).strip())
      atual = []
    else:
      atual.append(char)

  if atual:
    partes.append("".join(atual).strip())

  return partes


# Avaliador de fórmulas com suporte a SOMA, SOMASE, CONTSE, PROCV
def avaliar_formula(formula_str, mapa_dados, historico_visitados=None):
  if historico_visitados is None:
    historico_visitados = set()

  try:
    expressao = formula_str[1:].strip()
    expressao_upper = expressao.upper()

    # ------------------------------------------
    # 1. TRATAMENTO DE FUNÇÕES DO EXCEL
    # ------------------------------------------

    # --- SOMA ---
    match_soma = re.match(r"^SOMA\((.+)\)$", expressao_upper)
    if match_soma:
      arg = match_soma.group(1)
      celulas = expandir_intervalo(arg)
      total = sum(obter_valor_numerico(c, mapa_dados, historico_visitados.copy()) for c in celulas)
      return int(total) if total.is_integer() else round(total, 4)

    # --- SOMASE ---
    match_somase = re.match(r"^SOMASE\((.+)\)$", expressao_upper)
    if match_somase:
      args = dividir_argumentos(match_somase.group(1))
      if len(args) >= 2:
        interv_crit = expandir_intervalo(args[0])
        criterio_raw = args[1].strip().strip('"\'')
        interv_soma = expandir_intervalo(args[2]) if len(args) >= 3 else interv_crit

        total = 0.0
        for idx, c_crit in enumerate(interv_crit):
          v_crit = str(obter_valor_celula(c_crit, mapa_dados, historico_visitados.copy())).strip()

          if re.match(r"^[A-Z]+\d+$", criterio_raw):
            criterio_val = str(obter_valor_celula(criterio_raw, mapa_dados, historico_visitados.copy())).strip()
          else:
            criterio_val = criterio_raw

          if v_crit.upper() == criterio_val.upper():
            if idx < len(interv_soma):
              v_soma = obter_valor_numerico(interv_soma[idx], mapa_dados, historico_visitados.copy())
              total += v_soma

        return int(total) if total.is_integer() else round(total, 4)

    # --- CONTSE ---
    match_contse = re.match(r"^CONTSE\((.+)\)$", expressao_upper)
    if match_contse:
      args = dividir_argumentos(match_contse.group(1))
      if len(args) == 2:
        interv = expandir_intervalo(args[0])
        criterio_raw = args[1].strip().strip('"\'')

        count = 0
        for c_crit in interv:
          v_crit = str(obter_valor_celula(c_crit, mapa_dados, historico_visitados.copy())).strip()

          if re.match(r"^[A-Z]+\d+$", criterio_raw):
            criterio_val = str(obter_valor_celula(criterio_raw, mapa_dados, historico_visitados.copy())).strip()
          else:
            criterio_val = criterio_raw

          if v_crit.upper() == criterio_val.upper():
            count += 1

        return count

    # --- PROCV ---
    match_procv = re.match(r"^PROCV\((.+)\)$", expressao_upper)
    if match_procv:
      args = dividir_argumentos(match_procv.group(1))
      if len(args) >= 3:
        v_busca_raw = args[0].strip().strip('"\'')
        matriz_str = args[1].strip()
        col_idx = int(args[2])

        if re.match(r"^[A-Z]+\d+$", v_busca_raw):
          v_busca = str(obter_valor_celula(v_busca_raw, mapa_dados, historico_visitados.copy())).strip()
        else:
          v_busca = v_busca_raw

        inicio, fim = matriz_str.split(":")
        col_ini, lin_ini = re.match(r"([A-Z]+)(\d+)", inicio).groups()
        col_fim, lin_fim = re.match(r"([A-Z]+)(\d+)", fim).groups()

        idx_c_ini = COLUNAS_EXCEL.index(col_ini)
        idx_c_fim = COLUNAS_EXCEL.index(col_fim)

        for l in range(int(lin_ini), int(lin_fim) + 1):
          celula_chave = f"{COLUNAS_EXCEL[idx_c_ini]}{l}"
          v_chave = str(obter_valor_celula(celula_chave, mapa_dados, historico_visitados.copy())).strip()

          if v_chave.upper() == v_busca.upper():
            target_col_idx = idx_c_ini + col_idx - 1
            if target_col_idx <= idx_c_fim:
              celula_alvo = f"{COLUNAS_EXCEL[target_col_idx]}{l}"
              return obter_valor_celula(celula_alvo, mapa_dados, historico_visitados.copy())

        return "#N/A"

    # ------------------------------------------
    # 2. AVALIAÇÃO MATEMÁTICA PADRÃO (A1+B1, etc)
    # ------------------------------------------
    refs = re.findall(r"\b[A-Z]+\d+\b", expressao_upper)
    for ref in refs:
      val = obter_valor_numerico(ref, mapa_dados, historico_visitados.copy())
      expressao_upper = re.sub(r"\b" + ref + r"\b", str(val), expressao_upper)

    expressao_upper = expressao_upper.replace("^", "**")
    resultado = eval(expressao_upper, {"__builtins__": None}, {})

    if isinstance(resultado, float):
      return int(resultado) if resultado.is_integer() else round(resultado, 4)
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
        linha_vals.append("" if res is None or res == "None" else str(res))
      else:
        linha_vals.append("" if conteudo == "None" else conteudo)
    dados_grid.append(linha_vals)

  df = pd.DataFrame(
      dados_grid,
      columns=COLUNAS_EXCEL,
      index=[f"{i}" for i in range(1, TOTAL_LINHAS + 1)],
  )
  return df


# Função para exportar arquivo Excel (.xlsx)
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

      if not val or val == "None":
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
st.title("Planilha Interativa")

opcoes_celulas = [
    f"{col}{lin}" for lin in range(1, TOTAL_LINHAS + 1) for col in COLUNAS_EXCEL
]

col_celula, col_fx = st.columns([2, 8])

with col_celula:
  celula_selecionada = st.selectbox("Célula", opcoes_celulas, index=0)

val_atual = st.session_state.matriz_raw.get(celula_selecionada, "")
if val_atual == "None":
  val_atual = ""


def atualizar_barra_fx():
  novo_texto = st.session_state[f"input_fx_{celula_selecionada}"]
  st.session_state.matriz_raw[celula_selecionada] = novo_texto.strip()


with col_fx:
  st.text_input(
      "Barra de Fórmulas (fx)",
      value=val_atual,
      key=f"input_fx_{celula_selecionada}",
      on_change=atualizar_barra_fx,
      placeholder="Digite um valor ou fórmula (ex: =SOMASE(E3:F9;\"a\";F3:F9)) e pressione Enter",
  )

# ==========================================
# 3. GRADE INTERATIVA
# ==========================================
df_exibicao = gerar_dataframe_calculado()

df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_excel_v6",
)

houve_alteracao = False
for lin_idx, lin in enumerate(range(1, TOTAL_LINHAS + 1)):
  for col_idx, col in enumerate(COLUNAS_EXCEL):
    celula_ref = f"{col}{lin}"
    val_digitado_grid = str(df_editado.iat[lin_idx, col_idx]).strip()
    val_calculado_grid = str(df_exibicao.iat[lin_idx, col_idx]).strip()

    if val_digitado_grid != val_calculado_grid:
      st.session_state.matriz_raw[celula_ref] = val_digitado_grid
      houve_alteracao = True

if houve_alteracao:
  st.rerun()
