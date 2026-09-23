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

COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))]  # A até T

# 1. Inicializa o estado das FÓRMULAS ORIGINAIS (o que você digita)
if "matriz_formulas" not in st.session_state:
  st.session_state.matriz_formulas = [
      ["" for _ in COLUNAS_EXCEL] for _ in range(30)
  ]


# Función de cálculo en tiempo real
def calcular_matriz(matriz):
  df_calc = pd.DataFrame(
      "",
      index=[f"Linha {i+1}" for i in range(len(matriz))],
      columns=COLUNAS_EXCEL,
  )

  for r_idx in range(len(matriz)):
    for c_idx in range(len(COLUNAS_EXCEL)):
      val = str(matriz[r_idx][c_idx]).strip()

      if val.startswith("="):
        try:
          expressao = val[1:].upper()

          # Substitui referências de células (ex: A1, B1) pelos valores reais das células
          for row in range(1, len(matriz) + 1):
            for col_letter_idx, col_letter in enumerate(COLUNAS_EXCEL):
              celula_ref = f"{col_letter}{row}"
              if celula_ref in expressao:
                # Obtém o valor da célula referenciada
                val_celula = str(matriz[row - 1][col_letter_idx]).strip()

                # Se a célula referenciada for número, substitui, se não for, usa 0
                val_num = (
                    val_celula
                    if val_celula.replace(".", "", 1)
                    .replace("-", "", 1)
                    .isdigit()
                    else "0"
                )
                expressao = expressao.replace(celula_ref, val_num)

          # Executa o cálculo da expressão matemática
          resultado = eval(expressao)
          df_calc.iat[r_idx, c_idx] = (
              str(round(resultado, 4))
              if isinstance(resultado, float)
              else str(resultado)
          )
        except Exception:
          df_calc.iat[r_idx, c_idx] = "#ERRO!"
      else:
        df_calc.iat[r_idx, c_idx] = val

  return df_calc


# Gerador do arquivo .xlsx mantendo as fórmulas para o Excel
def gerar_excel(matriz):
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(COLUNAS_EXCEL)

  for row in matriz:
    linha = []
    for val in row:
      if val is None or val == "":
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
  excel_file = gerar_excel(st.session_state.matriz_formulas)
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
# 2. PLANILHA INTERATIVA E CÁLCULO
# ==========================================
st.title("📊 Planilha Interativa")
st.caption(
    "Digite valores ou fórmulas como `=A1+B1` e pressione **Enter**. O valor será"
    " calculado na hora!"
)

# Calcula os resultados atuais com base nas fórmulas armazenadas
df_exibicao = calcular_matriz(st.session_state.matriz_formulas)

# Renderiza a tabela e captura as edições diretamente
df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_editor_sincrono",
)

# Detecta alterações célula por célula e atualiza o estado
alterado = False
for r_idx in range(len(st.session_state.matriz_formulas)):
  for c_idx in range(len(COLUNAS_EXCEL)):
    val_tela = str(df_editado.iat[r_idx, c_idx]).strip()
    val_calculado = str(df_exibicao.iat[r_idx, c_idx]).strip()
    val_formula_orig = str(
        st.session_state.matriz_formulas[r_idx][c_idx]
    ).strip()

    # Se a pessoa alterou a célula na tela
    if val_tela != val_calculado:
      st.session_state.matriz_formulas[r_idx][c_idx] = val_tela
      alterado = True

if alterado:
  st.rerun()
