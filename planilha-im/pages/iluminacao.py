import io
import re
import openpyxl
import pandas as pd
from supabase import create_client
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Iluminação de Emergência", layout="wide")

# ==========================================
# CONFIGURAÇÃO DO SUPABASE
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
NOME_TABELA = "ILUMINACAO_EMERGENCIA"


@st.cache_resource
def init_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            st.error(f"Erro ao inicializar Supabase: {e}")
    return None


supabase = init_supabase()


# 1. Carregamento robusto do Supabase
@st.cache_data(ttl=1)
def carregar_dados_supabase():
    if not supabase:
        return {}, ["A", "B", "C"]

    try:
        response = supabase.table(NOME_TABELA).select("*").execute()
        registros = response.data

        if not registros:
            return {}, ["A", "B", "C"]

        primeiro_registro = registros[0]
        # Identifica as colunas ignorando LINHA e metadados
        colunas_disponiveis = [
            c.upper()
            for c in primeiro_registro.keys()
            if c.upper() != "LINHA" and not c.startswith("_")
        ]
        
        # Se a primeira coluna veio como 'UM', normalizamos para 'A' para manter compatibilidade com fórmulas
        if "UM" in colunas_disponiveis and "A" not in colunas_disponiveis:
            colunas_disponiveis = ["A" if c == "UM" else c for c in colunas_disponiveis]

        colunas_disponiveis = sorted(list(set(colunas_disponiveis)))
        if not colunas_disponiveis:
            colunas_disponiveis = ["A", "B", "C"]

        mapa_dados = {}
        for reg in registros:
            val_linha = reg.get("LINHA") or reg.get("linha")
            try:
                lin_num = int(val_linha)
            except (TypeError, ValueError):
                continue

            for col in colunas_disponiveis:
                # Busca a chave correspondente (tentando a letra original ou 'UM' se aplicável)
                chave_busca = "UM" if col == "A" and "UM" in [k.upper() for k in reg.keys()] else col
                val = reg.get(chave_busca, reg.get(col.lower(), ""))
                if val is None or str(val).strip().lower() in ["none", "nan", "null"]:
                    val = ""
                mapa_dados[f"{col}{lin_num}"] = str(val)

        return mapa_dados, colunas_disponiveis
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return {}, ["A", "B", "C"]


if "matriz_raw" not in st.session_state or "COLUNAS_EXCEL" not in st.session_state:
    matriz_carregada, cols_carregadas = carregar_dados_supabase()
    st.session_state.matriz_raw = matriz_carregada
    st.session_state.COLUNAS_EXCEL = cols_carregadas

if "alteracoes_pendentes" not in st.session_state:
    st.session_state.alteracoes_pendentes = False

COLUNAS_EXCEL = st.session_state.COLUNAS_EXCEL


# 2. Função de Salvamento Inteligente
def salvar_dados_supabase():
    if not supabase:
        st.error("❌ Erro: Supabase não configurado!")
        return False

    try:
        with st.spinner("💾 Gravando alterações no Supabase..."):
            linhas_dict = {}
            for ref, val in st.session_state.matriz_raw.items():
                match = re.match(r"([A-Z]+)(\d+)", ref.upper())
                if match:
                    col, lin = match.groups()
                    lin_int = int(lin)
                    if lin_int not in linhas_dict:
                        linhas_dict[lin_int] = {"LINHA": lin_int}
                    
                    # Se a coluna A mapeia para 'UM' no seu banco atual, ajustamos o envio
                    col_envio = "UM" if col == "A" else col
                    linhas_dict[lin_int][col_envio] = val if val != "" else None

            for lin_int, dados_linha in linhas_dict.items():
                supabase.table(NOME_TABELA).upsert(
                    dados_linha, on_conflict="LINHA"
                ).execute()

        st.session_state.alteracoes_pendentes = False
        st.success("✅ Dados salvos com sucesso no Supabase!")
        st.cache_data.clear()
        st.rerun()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False


# ==========================================
# BARRA SUPERIOR E NAVEGAÇÃO
# ==========================================
col_voltar, col_status, col_salvar, col_exportar = st.columns([2, 3, 2, 2])

with col_voltar:
    if st.button("Voltar ao Menu", use_container_width=True):
        try:
            st.switch_page("pages/menu.py")
        except Exception:
            pass

with col_status:
    if st.session_state.alteracoes_pendentes:
        st.warning("⚠️️ Alterações não salvas!")
    else:
        st.caption("✔️ Sincronizado.")

with col_salvar:
    if st.button("💾 Salvar no Supabase", use_container_width=True, type="primary"):
        salvar_dados_supabase()


# ==========================================
# MOTOR DE FÓRMULAS E CÁLCULOS
# ==========================================
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


def avaliar_formula(formula_str, mapa_dados, historico_visitados=None):
    if historico_visitados is None:
        historico_visitados = set()
    try:
        expressao = formula_str[1:].strip()
        expressao_upper = expressao.upper()

        # Suporte a SOMA básica ou intervalo (ex: SOMA(A5:B5) ou SOMA(A5))
        match_soma = re.match(r"^SOMA\((.+)\)$", expressao_upper)
        if match_soma:
            arg = match_soma.group(1)
            total = 0.0
            if ":" in arg:
                ini, fim = arg.split(":")
                c_ini, l_ini = parse_celula(ini)
                c_fim, l_fim = parse_celula(fim)
                if c_ini is not None and c_fim is not None and l_ini is not None and l_fim is not None:
                    for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
                        for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                            ref = f"{COLUNAS_EXCEL[c]}{l}"
                            total += obter_valor_numerico(ref, mapa_dados, historico_visitados.copy())
            else:
                total = obter_valor_numerico(arg, mapa_dados, historico_visitados.copy())
            return int(total) if total.is_integer() else round(total, 4)

        # Avaliação Matemática Direta (ex: =a5+b5)
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


def gerar_dataframe_calculado():
    max_lin = 30
    for ref in st.session_state.matriz_raw.keys():
        match = re.search(r"\d+", ref)
        if match:
            max_lin = max(max_lin, int(match.group()))

    dados_grid = []
    mapa_raw = st.session_state.matriz_raw

    for lin in range(1, max_lin + 1):
        linha_vals = []
        for col in COLUNAS_EXCEL:
            celula_ref = f"{col}{lin}"
            conteudo = str(mapa_raw.get(celula_ref, "")).strip()
            if not conteudo or conteudo.lower() in ["none", "nan", "null"]:
                linha_vals.append("")
            elif conteudo.startswith("="):
                res = avaliar_formula(conteudo, mapa_raw)
                linha_vals.append("" if res is None or str(res).lower() in ["none", "nan", "null"] else str(res))
            else:
                linha_vals.append(conteudo)
        dados_grid.append(linha_vals)

    return pd.DataFrame(
        dados_grid,
        columns=COLUNAS_EXCEL,
        index=[f"{i}" for i in range(1, max_lin + 1)],
    )


# Exportar Excel
def gerar_excel():
    buffer = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Iluminação"
    ws.append(COLUNAS_EXCEL)
    df_temp = gerar_dataframe_calculado()
    for _, row in df_temp.iterrows():
        ws.append(list(row))
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("ILUMINAÇÃO DE EMERGÊNCIA")

max_linhas_ativas = len(gerar_dataframe_calculado())
opcoes_celulas = [f"{col}{lin}" for lin in range(1, max_linhas_ativas + 1) for col in COLUNAS_EXCEL]

col_celula, col_fx, col_exp = st.columns([2, 6, 2])

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
    )

with col_exp:
    st.write("")
    excel_file = gerar_excel()
    st.download_button(
        label="📥 Exportar Excel",
        data=excel_file,
        file_name="iluminacao_emergencia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.divider()

# Grade Interativa (st.data_editor)
df_exibicao = gerar_dataframe_calculado()
df_editado = st.data_editor(
    df_exibicao, use_container_width=True, height=550, key="grid_supabase"
)

# Sincronização imediata das edições feitas diretamente na tabela
houve_alteracao = False
for lin_idx, lin in enumerate(range(1, len(df_exibicao) + 1)):
    for col_idx, col in enumerate(COLUNAS_EXCEL):
        celula_ref = f"{col}{lin}"
        val_digitado = df_editado.iat[lin_idx, col_idx]
        val_final = (
            ""
            if pd.isna(val_digitado) or val_digitado is None or str(val_digitado).strip().lower() in ["none", "nan", "null"]
            else str(val_digitado).strip()
        )
        
        val_atual_raw = str(st.session_state.matriz_raw.get(celula_ref, "")).strip()
        val_calculado_exibido = str(df_exibicao.iat[lin_idx, col_idx]).strip()

        if val_final != val_calculado_exibido:
            if val_atual_raw.startswith("=") and val_final == val_calculado_exibido:
                continue
            st.session_state.matriz_raw[celula_ref] = val_final
            houve_alteracao = True

if houve_alteracao:
    st.session_state.alteracoes_pendentes = True
    st.rerun()
