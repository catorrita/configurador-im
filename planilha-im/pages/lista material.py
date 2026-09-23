import io
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

# Criamos a estrutura de colunas do Excel (A até T)
COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))]  # A até T

# Inicializa no session_state com índice de 1 a 30 (como no Excel)
if "df_formulas" not in st.session_state:
  dados_vazios = [["" for _ in COLUNAS_EXCEL] for _ in range(30)]
  df_init = pd.DataFrame(dados_vazios, columns=COLUNAS_EXCEL)
  df_init.index = range(1, 31)  # Define linhas começando em 1
  st.session_state.df_formulas = df_init


# Função de cálculo de fórmulas em tempo real
def calcular_planilha(df_origem):
  df_calc = df_origem.copy()

  for r_idx in range(len(df_calc)):
    for c_idx, col in enumerate(df_calc.columns):
      val = str(df_calc.iat[r_idx, c_idx]).strip()

      if val.startswith("="):
        try:
          expressao = val[1:].upper()

          # Substitui referências de células (ex: A1, B1, A2) pelos valores das células
          for row in range(1, len(df_calc) + 1):
            for col_letter_idx, col_letter in enumerate(df_calc.columns):
              celula_ref = f"{col_letter}{row}"
              if celula_ref in expressao:
                val_celula = str(
                    df_origem.iat[row - 1, col_letter_idx]
                ).strip()

                # Se a célula referenciada for outra fórmula, calcula ela primeiro
                if val_celula.startswith("="):
                  val_celula = str(
                      calcular_planilha(df_origem).iat[row - 1, col_letter_idx]
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


# Gerador de arquivo Excel .xlsx
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
      file_name="planilha.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA ESTILO EXCEL
# ==========================================
st.title("📊 Planilha")

# Calcula os resultados mantendo o índice numérico nativo de 1 a N
df_exibicao = calcular_planilha(st.session_state.df_formulas)

# Renderiza a tabela usando o índice de linhas nativo
df_editado = st.data_editor(
    df_exibicao,
    num_rows="dynamic",
    use_container_width=True,
    height=600,
    key="excel_grid_v2",
)

# Atualiza as fórmulas e valores na sessão se houver alteração
if not df_editado.equals(df_exibicao):
  # Mantém o índice ajustado caso linhas sejam inseridas/deletadas
  df_editado.index = range(1, len(df_editado) + 1)

  if len(df_editado) != len(st.session_state.df_formulas):
    novos_dados = [
        ["" for _ in COLUNAS_EXCEL] for _ in range(len(df_editado))
    ]
    st.session_state.df_formulas = pd.DataFrame(
        novos_dados, columns=COLUNAS_EXCEL, index=range(1, len(df_editado) + 1)
    )

  for r_idx in range(len(df_editado)):
    for c_idx in range(len(df_editado.columns)):
      val_antigo = str(
          st.session_state.df_formulas.iat[r_idx, c_idx]
      ).strip()
      val_novo = str(df_editado.iat[r_idx, c_idx]).strip()

      if not val_antigo.startswith("="):
        st.session_state.df_formulas.iat[r_idx, c_idx] = val_novo
      elif val_novo.startswith("="):
        st.session_state.df_formulas.iat[r_idx, c_idx] = val_novo

  st.rerun()
