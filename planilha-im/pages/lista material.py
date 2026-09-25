import io
import json
import re
from github import Github, GithubException
import openpyxl
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Planilha Interativa", layout="wide")

# ==========================================
# CONFIGURAÇÃO DO GITHUB
# ==========================================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "catorrita/configurador-im")

# Alterado para buscar a chave específica da lista de material nos secrets
FILE_PATH = st.secrets.get(
    "FILE_PATH_LISTA", "planilha-im/dados/Lista_material.json"
)

@st.cache_resource
def obter_repositorio_github():
  if GITHUB_TOKEN and GITHUB_REPO:
    try:
      g = Github(GITHUB_TOKEN)
      return g.get_repo(GITHUB_REPO)
    except Exception as e:
      st.error(f"Erro na conexão com o GitHub: {e}")
  return None


repo = obter_repositorio_github()


# 1. Função para carregar os dados salvos do GitHub ao iniciar
def carregar_dados_github():
  if repo:
    try:
      content = repo.get_contents(FILE_PATH)
      dados = json.loads(content.decoded_content.decode("utf-8"))
      for key, val in dados.items():
        if str(val).strip().lower() in ["none", "nan", "null"]:
          dados[key] = ""
      return dados
    except GithubException as e:
      if e.status == 404:
        st.warning(
            "⚠️ Arquivo de dados não encontrado no GitHub. Criando matriz em"
            " branco."
        )
      else:
        st.error(f"Erro ao carregar dados do GitHub: {e}")

  return {
      f"{col}{lin}": ""
      for lin in range(1, 31)
      for col in [chr(i) for i in range(ord("A"), ord("U"))]
  }


# 2. Função acionada pelo Botão de Salvar
def salvar_dados_github():
  if not repo:
    st.error(
        "❌ Erro: GITHUB_TOKEN não configurado no st.secrets do Streamlit"
        " Cloud!"
    )
    return False

  conteudo_json = json.dumps(
      st.session_state.matriz_raw, ensure_ascii=False, indent=2
  )

  try:
    with st.spinner("💾 Gravando alterações no GitHub..."):
      try:
        content = repo.get_contents(FILE_PATH)
        repo.update_file(
            path=FILE_PATH,
            message="Atualização da planilha via Streamlit",
            content=conteudo_json,
            sha=content.sha,
        )
      except GithubException as e:
        if e.status == 404:
          repo.create_file(
              path=FILE_PATH,
              message="Criação inicial do arquivo da planilha",
              content=conteudo_json,
          )
        else:
          raise e

    st.session_state.alteracoes_pendentes = False
    st.success("✅ Planilha salva com sucesso no GitHub!")
    return True
  except Exception as e:
    st.error(f"Erro ao salvar no GitHub: {e}")
    return False


# Inicialização de Session States
COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("Z"))]  # A até T
TOTAL_LINHAS = 1000

if "matriz_raw" not in st.session_state:
  st.session_state.matriz_raw = carregar_dados_github()

if "alteracoes_pendentes" not in st.session_state:
  st.session_state.alteracoes_pendentes = False

# ==========================================
# 1. BARRA SUPERIOR E NAVEGAÇÃO
# ==========================================
col_voltar, col_status, col_salvar, col_exportar = st.columns([2, 3, 2, 2])

with col_voltar:
  if st.button("← Ir ao Início", use_container_width=True):
    st.switch_page("app.py")

with col_status:
  if st.session_state.alteracoes_pendentes:
    st.warning("⚠️ Existem alterações não salvas!")
  else:
    st.caption("✔️ Tudo sincronizado com o GitHub.")

with col_salvar:
  if st.button(
      "💾 Salvar no GitHub", use_container_width=True, type="primary"
  ):
    salvar_dados_github()


# Funções de Parsing e Avaliação de Fórmulas
def parse_celula(ref):
  match = re.match(r"([A-Z]+)(\d+)", ref.strip().upper())
  if match:
    col_str, lin_str = match.groups()
    if col_str in COLUNAS_EXCEL:
      return COLUNAS_EXCEL.index(col_str), int(lin_str)
  return None, None


def obter_valor_celula(ref, mapa_dados, historico_visitados=None):
  if historico_visitados is None:
    historico_visitados = set()

  if ref in historico_visitados:
    return 0.0

  historico_visitados.add(ref)
  conteudo = str(mapa_dados.get(ref, "")).strip()

  if not conteudo or conteudo.lower() in ["none", "nan", "null"]:
    return ""

  if conteudo.startswith("="):
    res = avaliar_formula(conteudo, mapa_dados, historico_visitados)
    return res if res != "#ERRO!" else ""

  return conteudo


def obter_valor_numerico(ref, mapa_dados, historico_visitados=None):
  val = obter_valor_celula(ref, mapa_dados, historico_visitados)
  try:
    return float(str(val).replace(",", "."))
  except ValueError:
    return 0.0


def dividir_argumentos(args_str):
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


def avaliar_formula(formula_str, mapa_dados, historico_visitados=None):
  if historico_visitados is None:
    historico_visitados = set()

  try:
    expressao = formula_str[1:].strip()
    expressao_upper = expressao.upper()

    # --- SOMA ---
    match_soma = re.match(r"^SOMA\((.+)\)$", expressao_upper)
    if match_soma:
      arg = match_soma.group(1)
      total = 0.0
      if ":" in arg:
        ini, fim = arg.split(":")
        c_ini, l_ini = parse_celula(ini)
        c_fim, l_fim = parse_celula(fim)
        for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
          for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
            ref = f"{COLUNAS_EXCEL[c]}{l}"
            total += obter_valor_numerico(
                ref, mapa_dados, historico_visitados.copy()
            )
      else:
        total = obter_valor_numerico(
            arg, mapa_dados, historico_visitados.copy()
        )

      return int(total) if total.is_integer() else round(total, 4)

    # --- SOMASE ---
    match_somase = re.match(r"^SOMASE\((.+)\)$", expressao_upper)
    if match_somase:
      args = dividir_argumentos(match_somase.group(1))
      if len(args) >= 2:
        interv_crit_str = args[0]
        criterio_raw = args[1].strip().strip('"\'')
        interv_soma_str = args[2] if len(args) >= 3 else interv_crit_str

        if ":" in interv_crit_str:
          c_ini_crit, l_ini_crit = parse_celula(interv_crit_str.split(":")[0])
          c_fim_crit, l_fim_crit = parse_celula(interv_crit_str.split(":")[1])
        else:
          c_ini_crit, l_ini_crit = parse_celula(interv_crit_str)
          c_fim_crit, l_fim_crit = parse_celula(interv_crit_str)

        if ":" in interv_soma_str:
          c_ini_soma, l_ini_soma = parse_celula(interv_soma_str.split(":")[0])
        else:
          c_ini_soma, l_ini_soma = parse_celula(interv_soma_str)

        total = 0.0

        for c in range(
            min(c_ini_crit, c_fim_crit), max(c_ini_crit, c_fim_crit) + 1
        ):
          for l in range(
              min(l_ini_crit, l_fim_crit), max(l_ini_crit, l_fim_crit) + 1
          ):
            c_crit_ref = f"{COLUNAS_EXCEL[c]}{l}"
            v_crit = str(
                obter_valor_celula(
                    c_crit_ref, mapa_dados, historico_visitados.copy()
                )
            ).strip()

            if re.match(r"^[A-Z]+\d+$", criterio_raw):
              criterio_val = str(
                  obter_valor_celula(
                      criterio_raw, mapa_dados, historico_visitados.copy()
                  )
              ).strip()
            else:
              criterio_val = criterio_raw

            if v_crit.upper() == criterio_val.upper():
              delta_col = c - min(c_ini_crit, c_fim_crit)
              delta_lin = l - min(l_ini_crit, l_fim_crit)

              target_c = c_ini_soma + delta_col
              target_l = l_ini_soma + delta_lin

              if (
                  0 <= target_c < len(COLUNAS_EXCEL)
                  and 1 <= target_l <= TOTAL_LINHAS
              ):
                c_soma_ref = f"{COLUNAS_EXCEL[target_c]}{target_l}"
                v_soma = obter_valor_numerico(
                    c_soma_ref, mapa_dados, historico_visitados.copy()
                )
                total += v_soma

        return int(total) if total.is_integer() else round(total, 4)

    # --- CONT.SE / CONTSE ---
    match_contse = re.match(r"^CONT\.?SE\((.+)\)$", expressao_upper)
    if match_contse:
      args = dividir_argumentos(match_contse.group(1))
      if len(args) == 2:
        interv_str = args[0]
        criterio_raw = args[1].strip().strip('"\'')

        if ":" in interv_str:
          c_ini, l_ini = parse_celula(interv_str.split(":")[0])
          c_fim, l_fim = parse_celula(interv_str.split(":")[1])
        else:
          c_ini, l_ini = parse_celula(interv_str)
          c_fim, l_fim = parse_celula(interv_str)

        count = 0
        for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
          for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
            c_ref = f"{COLUNAS_EXCEL[c]}{l}"
            v_crit = str(
                obter_valor_celula(
                    c_ref, mapa_dados, historico_visitados.copy()
                )
            ).strip()

            if re.match(r"^[A-Z]+\d+$", criterio_raw):
              criterio_val = str(
                  obter_valor_celula(
                      criterio_raw, mapa_dados, historico_visitados.copy()
                  )
              ).strip()
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
          v_busca = str(
              obter_valor_celula(
                  v_busca_raw, mapa_dados, historico_visitados.copy()
              )
          ).strip()
        else:
          v_busca = v_busca_raw

        inicio, fim = matriz_str.split(":")
        c_ini, l_ini = parse_celula(inicio)
        c_fim, l_fim = parse_celula(fim)

        for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
          celula_chave = f"{COLUNAS_EXCEL[c_ini]}{l}"
          v_chave = str(
              obter_valor_celula(
                  celula_chave, mapa_dados, historico_visitados.copy()
              )
          ).strip()

          if v_chave.upper() == v_busca.upper():
            target_c = c_ini + col_idx - 1
            if target_c <= c_fim:
              celula_alvo = f"{COLUNAS_EXCEL[target_c]}{l}"
              return obter_valor_celula(
                  celula_alvo, mapa_dados, historico_visitados.copy()
              )

        return "#N/A"

    # Avaliação Matemática Padrão (Substituição de Referências ex: B2+C2)
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


# Função que monta a grade exibida no Streamlit
def gerar_dataframe_calculado():
  dados_grid = []
  mapa_raw = st.session_state.matriz_raw

  for lin in range(1, TOTAL_LINHAS + 1):
    linha_vals = []
    for col in COLUNAS_EXCEL:
      celula_ref = f"{col}{lin}"
      conteudo = str(mapa_raw.get(celula_ref, "")).strip()

      if not conteudo or conteudo.lower() in ["none", "nan", "null"]:
        linha_vals.append("")
      elif conteudo.startswith("="):
        res = avaliar_formula(conteudo, mapa_raw)
        if res is None or str(res).lower() in ["none", "nan", "null"]:
          linha_vals.append("")
        else:
          linha_vals.append(str(res))
      else:
        linha_vals.append(conteudo)
    dados_grid.append(linha_vals)

  df = pd.DataFrame(
      dados_grid,
      columns=COLUNAS_EXCEL,
      index=[f"{i}" for i in range(1, TOTAL_LINHAS + 1)],
  )
  return df


# Exportar Excel
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

      if not val or val.lower() in ["none", "nan", "null"]:
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
      label="📥 Exportar Excel",
      data=excel_file,
      file_name="planilha.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
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

val_atual = str(st.session_state.matriz_raw.get(celula_selecionada, "")).strip()
if val_atual.lower() in ["none", "nan", "null"]:
  val_atual = ""


def atualizar_barra_fx():
  chave_input = f"input_fx_{celula_selecionada}"
  if chave_input in st.session_state:
    novo_texto = st.session_state[chave_input].strip()
    if novo_texto.lower() in ["none", "nan", "null"]:
      novo_texto = ""

    if st.session_state.matriz_raw.get(celula_selecionada, "") != novo_texto:
      st.session_state.matriz_raw[celula_selecionada] = novo_texto
      st.session_state.alteracoes_pendentes = True


with col_fx:
  st.text_input(
      "Barra de Fórmulas (fx)",
      value=val_atual,
      key=f"input_fx_{celula_selecionada}",
      on_change=atualizar_barra_fx,
      placeholder=(
          "Digite um valor ou fórmula (ex: =B2+C2 ou =CONT.SE(E3:E9;\"a\")) e"
          " pressione Enter"
      ),
  )

# ==========================================
# 3. GRADE INTERATIVA
# ==========================================
df_exibicao = gerar_dataframe_calculado()

df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_excel_v8",
)

# Comparação Inteligente (apenas altera quando o usuário digita algo diferente do resultado exibido)
houve_alteracao = False
for lin_idx, lin in enumerate(range(1, TOTAL_LINHAS + 1)):
  for col_idx, col in enumerate(COLUNAS_EXCEL):
    celula_ref = f"{col}{lin}"
    val_digitado = df_editado.iat[lin_idx, col_idx]

    if (
        pd.isna(val_digitado)
        or val_digitado is None
        or str(val_digitado).strip().lower() in ["none", "nan", "null"]
    ):
      val_final = ""
    else:
      val_final = str(val_digitado).strip()

    val_calculado_exibido = str(df_exibicao.iat[lin_idx, col_idx]).strip()

    # Se o valor digitado na grade for diferente do resultado calculado, atualiza o valor bruto
    if val_final != val_calculado_exibido:
      st.session_state.matriz_raw[celula_ref] = val_final
      houve_alteracao = True

if houve_alteracao:
  st.session_state.alteracoes_pendentes = True
  st.rerun()
