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

# Inicializa matriz em branco (20 linhas x 8 colunas)
if "df_planilha" not in st.session_state:
  colunas = ["A", "B", "C", "D", "E", "F", "G", "H"]
  dados_vazios = [["" for _ in colunas] for _ in range(20)]
  st.session_state.df_planilha = pd.DataFrame(dados_vazios, columns=colunas)


# Função para calcular expressões simples digitadas (=A1+A2, =SUM(A1:A5), etc.)
def avaliar_grid(df):
  df_calculado = df.copy()

  # Processa células com fórmulas simples
  for r_idx in range(len(df_calculado)):
    for c_idx, col in enumerate(df_calculado.columns):
      val = str(df_calculado.iat[r_idx, c_idx]).strip()
      if val.startswith("="):
        try:
          # Trata fórmulas simples de adição/subtração/multiplicação/divisão
          expressao = val[1:].upper()

          # Substitui referências de células (ex: A1, A2) pelos seus valores numéricos reais
          for row in range(1, len(df_calculado) + 1):
            for col_letter_idx, col_letter in enumerate(df_calculado.columns):
              celula_ref = f"{col_letter}{row}"
              if celula_ref in expressao:
                val_celula = str(
                    df_calculado.iat[row - 1, col_letter_idx]
                ).strip()
                val_num = (
                    val_celula
                    if val_celula.replace(".", "", 1)
                    .replace("-", "", 1)
                    .isdigit()
                    else "0"
                )
                expressao = expressao.replace(celula_ref, val_num)

          # Avalia o resultado matemático
          resultado = eval(expressao)
          df_calculado.iat[r_idx, c_idx] = str(resultado)
        except Exception:
          # Mantém o texto da fórmula se ainda não puder ser calculada
          pass
  return df_calculado


# Função para exportar para o Excel
def gerar_excel(df):
  buffer = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Planilha"

  ws.append(list(df.columns))

  for _, row in df.iterrows():
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
  excel_file = gerar_excel(st.session_state.df_planilha)
  st.download_button(
      label="📥 Exportar Planilha",
      data=excel_file,
      file_name="planilha_material.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
      type="primary",
  )

st.divider()

# ==========================================
# 2. PLANILHA INTERATIVA
# ==========================================
st.title("📊 Planilha com Cálculo de Fórmulas")
st.caption(
    "Digite valores nas células. Para somar ou calcular, digite expressões"
    " como `=A1+A2` ou `=B1*2`. O resultado será processado automaticamente ao"
    " confirmar a célula."
)

# Renderiza o editor de dados
df_editado = st.data_editor(
    st.session_state.df_planilha,
    num_rows="dynamic",
    use_container_width=True,
    height=550,
    key="grid_editor_formulas",
)

# Processa e atualiza as fórmulas
if not df_editado.equals(st.session_state.df_planilha):
  st.session_state.df_planilha = avaliar_grid(df_editado)
  st.rerun()
