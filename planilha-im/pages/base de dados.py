import io
import json
import re
import openpyxl
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# Configuração da página
st.set_page_config(
    page_title="Base de Dados - Planilha Interativa", layout="wide"
)

# ==========================================
# CONFIGURAÇÃO DO SUPABASE
# ==========================================
SUPABASE_URL = st.secrets["connections.supabase"]["url"]
SUPABASE_KEY = st.secrets["connections.supabase"]["key"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# E-mail do usuário logado
USER_EMAIL = "felipe.binsfeld@fockind.ind.br"

# Chaves dinâmicas baseadas na sessão
CHAVE_MATRIZ = f"matriz_raw_{USER_EMAIL}"
CHAVE_ALTERACOES = f"alteracoes_pendentes_{USER_EMAIL}"

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (SUPABASE)
# ==========================================
def carregar_dados_supabase():
    try:
        # Puxa os dados do Supabase isolados por usuário com paginação segura para grandes volumes
        response = (
            supabase.table("Base de dados Configurador IM")
            .select("*")
            .eq("MODIF_POR", USER_EMAIL)
            .order("COD_SAP", desc=False)
            .range(0, 999) # Carrega os primeiros 1000 registros para a grade interativa
            .execute()
        )
        dados_tabela = response.data
        
        matriz_vazia = {
            f"{col}{lin}": ""
            for lin in range(1, 1001)
            for col in [chr(i) for i in range(ord("A"), ord("U"))]
        }
        
        if dados_tabela:
            for idx, row in enumerate(dados_tabela, start=1):
                if idx > 1000: 
                    break
                matriz_vazia[f"A{idx}"] = str(row.get("COD_SAP", "") or "")
                matriz_vazia[f"B{idx}"] = str(row.get("COD_SGE", "") or "")
                matriz_vazia[f"C{idx}"] = str(row.get("DESC_ITEM", "") or "")
                
        return matriz_vazia

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return {
            f"{col}{lin}": ""
            for lin in range(1, 1001)
            for col in [chr(i) for i in range(ord("A"), ord("U"))]
        }

def salvar_dados_supabase():
    try:
        with st.spinner("💾 Gravando alterações no Supabase..."):
            for lin in range(1, 1001):
                cod_sap = str(st.session_state[CHAVE_MATRIZ].get(f"A{lin}", "")).strip()
                cod_sge = str(st.session_state[CHAVE_MATRIZ].get(f"B{lin}", "")).strip()
                desc_item = str(st.session_state[CHAVE_MATRIZ].get(f"C{lin}", "")).strip()
                
                if cod_sap or cod_sge or desc_item:
                    registro = {
                        "MODIF_POR": USER_EMAIL,
                        "COD_SAP": cod_sap,
                        "COD_SGE": cod_sge,
                        "DESC_ITEM": desc_item
                    }
                    supabase.table("Base de dados Configurador IM").upsert(registro, on_conflict="MODIF_POR,COD_SAP").execute()

        st.session_state[CHAVE_ALTERACOES] = False
        st.success("✅ Dados salvos com sucesso no Supabase!")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False

# Inicialização de Session States
COLUNAS_EXCEL = [chr(i) for i in range(ord("A"), ord("U"))] # A até U
TOTAL_LINHAS = 1000

if CHAVE_MATRIZ not in st.session_state:
    st.session_state[CHAVE_MATRIZ] = carregar_dados_supabase()

if CHAVE_ALTERACOES not in st.session_state:
    st.session_state[CHAVE_ALTERACOES] = False

# ==========================================
# 1. BARRA SUPERIOR E NAVEGAÇÃO
# ==========================================
col_voltar, col_status, col_salvar, col_exportar = st.columns([2, 3, 2, 2])

with col_voltar:
    if st.button("← Ir ao Início", use_container_width=True):
        st.switch_page("app.py")

with col_status:
    if st.session_state[CHAVE_ALTERACOES]:
        st.warning("⚠️ Existem alterações não salvas!")
    else:
        st.caption(f"✔️ Sincronizado com Supabase ({USER_EMAIL}).")

with col_salvar:
    if st.button("💾 Salvar no Supabase", use_container_width=True, type="primary"):
        salvar_dados_supabase()

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
                        total += obter_valor_numerico(ref, mapa_dados, historico_visitados.copy())
            else:
                total = obter_valor_numerico(arg, mapa_dados, historico_visitados.copy())

            return int(total) if total.is_integer() else round(total, 4)

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
    dados_grid = []
    mapa_raw = st.session_state[CHAVE_MATRIZ]

    for lin in range(1, TOTAL_LINHAS + 1):
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
        index=[f"{i}" for i in range(1, TOTAL_LINHAS + 1)],
    )

def gerar_excel():
    buffer = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Planilha"
    ws.append(COLUNAS_EXCEL)

    for lin in range(1, TOTAL_LINHAS + 1):
        linha = []
        for col in COLUNAS_EXCEL:
            val = str(st.session_state[CHAVE_MATRIZ].get(f"{col}{lin}", "")).strip()
            if not val or val.lower() in ["none", "nan", "null"]:
                linha.append("")
            elif val.replace(".", "", 1).replace("-", "", 1).isdigit() and not val.startswith("="):
                linha.append(float(val) if "." in val else int(val))
            else:
                linha.append(val)
        ws.append(linha)

    wb.save(buffer)
    buffer.seek(0)
    return buffer

with col_exportar:
    st.download_button(
        label="📥 Exportar Excel",
        data=gerar_excel(),
        file_name="planilha.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.divider()

# ==========================================
# 2. BARRA DE FÓRMULAS ESTILO EXCEL (fx)
# ==========================================
opcoes_celulas = [f"{col}{lin}" for lin in range(1, TOTAL_LINHAS + 1) for col in COLUNAS_EXCEL]
col_celula, col_fx = st.columns([2, 8])

with col_celula:
    celula_selecionada = st.selectbox("Célula", opcoes_celulas, index=0)

val_atual = str(st.session_state[CHAVE_MATRIZ].get(celula_selecionada, "")).strip()
if val_atual.lower() in ["none", "nan", "null"]:
    val_atual = ""

def atualizar_barra_fx():
    chave_input = f"input_fx_{celula_selecionada}"
    if chave_input in st.session_state:
        novo_texto = str(st.session_state[chave_input]).strip()
        if novo_texto.lower() in ["none", "nan", "null"]:
            novo_texto = ""
        if st.session_state[CHAVE_MATRIZ].get(celula_selecionada, "") != novo_texto:
            st.session_state[CHAVE_MATRIZ][celula_selecionada] = novo_texto
            st.session_state[CHAVE_ALTERACOES] = True

with col_fx:
    st.text_input(
        "Barra de Fórmulas (fx)",
        value=val_atual,
        key=f"input_fx_{celula_selecionada}",
        on_change=atualizar_barra_fx,
        placeholder="Digite um valor ou fórmula e pressione Enter",
    )

# ==========================================
# 3. GRADE INTERATIVA
# ==========================================
df_exibicao = gerar_dataframe_calculado()

df_editado = st.data_editor(
    df_exibicao,
    use_container_width=True,
    height=550,
    key="grid_excel_supabase",
)

houve_alteracao = False
for lin_idx, lin in enumerate(range(1, TOTAL_LINHAS + 1)):
    for col_idx, col in enumerate(COLUNAS_EXCEL):
        celula_ref = f"{col}{lin}"
        val_digitado = df_editado.iat[lin_idx, col_idx]

        val_final = "" if pd.isna(val_digitado) or val_digitado is None or str(val_digitado).strip().lower() in ["none", "nan", "null"] else str(val_digitado).strip()
        val_calculado_exibido = str(df_exibicao.iat[lin_idx, col_idx]).strip()

        if val_final != val_calculado_exibido:
            st.session_state[CHAVE_MATRIZ][celula_ref] = val_final
            houve_alteracao = True

if houve_alteracao:
    st.session_state[CHAVE_ALTERACOES] = True
    st.rerun()
