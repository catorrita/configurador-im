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

# Criamos a estrutura de colunas A até T
COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))]

# Inicializa o estado da planilha
if "matriz_dados" not in st.session_state:
  # Matriz para guardar exatamente o que o usuário digita (inclusive =a1+b1)
  st.session_state.matriz_dados = [
      ["" for _ in COLUNAS_EXCEL] for _ in range(30)
  ]


# Função de cálculo
def processar_calculos(matriz_entrada):
  # Cria DataFrame com índices numéricos visíveis de 1 a 30
  df_calc = pd.DataFrame(
      matriz_entrada,
      columns=COLUNAS_EXCEL,
      index=[f"Linha {i+1}" for i in range(len(matriz_entrada))],
  )

  for r_idx in range(len(matriz_entrada)):
    for c_idx in range(len(COLUNAS_EXCEL)):
      val = str(matriz_entrada[r_idx][c_idx]).strip()

      if val.startswith("="):
        try:
          expressao = val[1:].upper()

          # Substitui referências de células (ex: A1, B1) pelos valores
          for row in range(1, len(matriz_entrada) + 1):
            for col_letter_idx, col_letter in enumerate(COLUNAS_EXCEL):
              celula_ref = f"{col_letter}{row}"
              if celula_ref in expressao:
                val_celula = str(
                    matriz_entrada[row - 1][col_letter_idx]
                ).strip()

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
  excel_file = gerar_excel(st.session_state.matriz_dados)
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
# 2. PLANILHA
# ==========================================
st.title("📊 Planilha Interativa")

col_info, col_btn = st.columns([7, 2])
with col_info:
  st.caption(
      "Digite os dados ou fórmulas (ex: `=A1+B1`). Pressione **Calcular /"
      " Atualizar** abaixo para processar os resultados."
  )
with col_btn:
  btn_calcular = st.button(
      "🔄 Calcular / Atualizar", type="primary", use_container_width=True
  )

# Gera a visualização atual
df_exibicao = processar_calculos(st.session_state.matriz_dados)

# Renderiza a tabela com o rótulo da linha visível na extrema esquerda
df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_matriz_v3",
)

# Atualiza a matriz ao clicar no botão ou alterar a tabela
if btn_calcular:
  for r_idx in range(len(st.session_state.matriz_dados)):
    for c_idx in range(len(COLUNAS_EXCEL)):
      val_novo = str(df_editado.iat[r_idx, c_idx]).strip()
      st.session_state.matriz_dados[r_idx][c_idx] = val_novo
  st.rerun()
