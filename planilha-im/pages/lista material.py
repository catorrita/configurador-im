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

# Inicializa matriz em branco se não existir na sessão (Guarda as FÓRMULAS ORIGINAIS)
if "df_formulas" not in st.session_state:
  colunas = ["A", "B", "C", "D", "E", "F", "G", "H"]
  dados_vazios = [["" for _ in colunas] for _ in range(20)]
  st.session_state.df_formulas = pd.DataFrame(dados_vazios, columns=colunas)


# Função que reavalia todas as fórmulas com base nos dados mais recentes
def calcular_planilha(df_origem):
  df_calc = df_origem.copy()

  for r_idx in range(len(df_calc)):
    for c_idx, col in enumerate(df_calc.columns):
      val = str(df_calc.iat[r_idx, c_idx]).strip()

      if val.startswith("="):
        try:
          expressao = val[1:].upper()

          # Substitui as referências de células (ex: A1, A2) pelos valores numéricos atuais
          for row in range(1, len(df_calc) + 1):
            for col_letter_idx, col_letter in enumerate(df_calc.columns):
              celula_ref = f"{col_letter}{row}"
              if celula_ref in expressao:
                val_celula = str(
                    df_origem.iat[row - 1, col_letter_idx]
                ).strip()

                # Se a célula referenciada também for uma fórmula, calcula recursivamente
                if val_celula.startswith("="):
                  val_celula = str(
                      calcular_planilha(df_origem).iat[
                          row - 1, col_letter_idx
                      ]
                  )

                val_num = (
                    val_celula
                    if val_celula.replace(".", "", 1)
                    .replace("-", "", 1)
                    .isdigit()
                    else "0"
                )
                expressao = expressao.replace(celula_ref, val_num)

          resultado = eval(expressao)
          df_calc.iat[r_idx, c_idx] = (
              round(resultado, 4) if isinstance(resultado, float) else resultado
          )
        except Exception:
          df_calc.iat[r_idx, c_idx] = "#ERRO!"

  return df_calc


# Função para exportar para o Excel sem a coluna visual de índice
def gerar_excel(df_formulas):
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(list(df_formulas.columns))

  for _, row in df_formulas.iterrows():
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
  excel_file = gerar_excel(st.session_state.df_formulas)
  st.download_button(
      label="📥 Exportar Planilha",
      data=excel_file,
      file_name="planilha_dinamica.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA DINÂMICA COM NUMERAÇÃO DE LINHAS
# ==========================================
st.title("📊 Planilha Dinâmica")
st.caption(
    "Altere qualquer valor e as fórmulas serão recalculadas automaticamente em"
    " tempo real!"
)

# Calcula a visualização atual das fórmulas
df_exibicao = calcular_planilha(st.session_state.df_formulas)

# Insere a coluna visual do número de linhas no início (1, 2, 3...)
df_exibicao_com_linhas = df_exibicao.copy()
df_exibicao_com_linhas.insert(
    0, "Linha", range(1, len(df_exibicao_com_linhas) + 1)
)

# Renderiza a tabela no Streamlit
df_editado = st.data_editor(
    df_exibicao_com_linhas,
    num_rows="dynamic",
    use_container_width=True,
    height=550,
    key="grid_dinamico_linhas",
    disabled=["Linha"],  # Bloqueia a edição da coluna de número de linha
)

# Remove a coluna de indicação 'Linha' para processar apenas os dados das colunas A, B, C...
df_editado_dados = df_editado.drop(columns=["Linha"], errors="ignore")

# Detecta alterações efetuadas pelo usuário e atualiza a matriz principal
if not df_editado_dados.equals(df_exibicao):
  # Ajusta o tamanho caso linhas tenham sido adicionadas/removidas
  if len(df_editado_dados) != len(st.session_state.df_formulas):
    novos_dados = [
        ["" for _ in st.session_state.df_formulas.columns]
        for _ in range(len(df_editado_dados))
    ]
    st.session_state.df_formulas = pd.DataFrame(
        novos_dados, columns=st.session_state.df_formulas.columns
    )

  for r_idx in range(len(df_editado_dados)):
    for c_idx in range(len(df_editado_dados.columns)):
      val_antigo = str(
          st.session_state.df_formulas.iat[r_idx, c_idx]
      ).strip()
      val_novo = str(df_editado_dados.iat[r_idx, c_idx]).strip()

      if not val_antigo.startswith("="):
        st.session_state.df_formulas.iat[r_idx, c_idx] = val_novo
      elif val_novo.startswith("="):
        st.session_state.df_formulas.iat[r_idx, c_idx] = val_novo

  st.rerun()
