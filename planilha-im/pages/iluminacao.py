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

# Colunas padrão caso a tabela esteja vazia ou sem registros
COLUNAS_PADRAO = ["A", "B", "C", "D", "E"]


@st.cache_resource
def init_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            st.error(f"Erro ao inicializar cliente Supabase: {e}")
    return None


supabase = init_supabase()


# 1. Carregamento dinâmico da base de dados Supabase
@st.cache_data(ttl=1)
def carregar_dados_supabase():
    if not supabase:
        st.warning(
            "⚠️ Credenciais do Supabase não configuradas. Usando modo local temporário."
        )
        return {}, COLUNAS_PADRAO

    try:
        response = supabase.table(NOME_TABELA).select("*").execute()
        registros = response.data

        if not registros:
            return {}, COLUNAS_PADRAO

        # Identificar colunas disponíveis (excluindo LINHA e metadados)
        primeiro_registro = registros[0]
        colunas_disponiveis = [
            c.upper()
            for c in primeiro_registro.keys()
            if c.upper() != "LINHA" and not c.startswith("_")
        ]
        
        if not colunas_disponiveis:
            colunas_disponiveis = COLUNAS_PADRAO
        else:
            colunas_disponiveis = sorted(list(set(colunas_disponiveis)))

        mapa_dados = {}
        for reg in registros:
            val_linha = reg.get("LINHA") or reg.get("linha")
            try:
                lin_num = int(val_linha)
            except (TypeError, ValueError):
                continue

            for col in colunas_disponiveis:
                # Tenta buscar a chave em maiúsculo ou minúsculo no registro do Supabase
                val = reg.get(col, reg.get(col.lower(), ""))
                if val is None or str(val).strip().lower() in ["none", "nan", "null"]:
                    val = ""
                mapa_dados[f"{col.upper()}{lin_num}"] = str(val)

        return mapa_dados, colunas_disponiveis
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return {}, COLUNAS_PADRAO


if "matriz_raw" not in st.session_state or "colunas_excel" not in st.session_state:
    matriz_carregada, cols_carregadas = carregar_dados_supabase()
    st.session_state.matriz_raw = matriz_carregada
    st.session_state.COLUNAS_EXCEL = cols_carregadas

if "alteracoes_pendentes" not in st.session_state:
    st.session_state.alteracoes_pendentes = False

COLUNAS_EXCEL = st.session_state.COLUNAS_EXCEL


# 2. Função acionada pelo Botão de Salvar no Supabase
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
                    # Salva a coluna em maiúsculo conforme o padrão da tabela
                    linhas_dict[lin_int][col.upper()] = val if val != "" else None

            for lin_int, dados_linha in linhas_dict.items():
                supabase.table(NOME_TABELA).upsert(
                    dados_linha, on_conflict="LINHA"
                ).execute()

        st.session_state.alteracoes_pendentes = False
        st.success("✅ Dados salvos com sucesso no Supabase!")
        st.cache_data.clear()
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
            st.info("Menu indisponível neste contexto.")

with col_status:
    if st.session_state.alteracoes_pendentes:
        st.warning("⚠️ Existem alterações não salvas!")
    else:
        st.caption("✔️ Sincronizado com o Supabase.")

with col_salvar:
    if st.button(
        "💾 Salvar no Supabase", use_container_width=True, type="primary"
    ):
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
    partes, atual, em_aspas, caractere_aspas = [], [], False, None
    for char in args_str:
        if char in ('"', "'"):
            if not em_aspas:
                em_aspas, caractere_aspas = True, char
            elif char == caractere_aspas:
                em_aspas, caractere_aspas = False, None
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
                if c_ini is not None and c_fim is not None and l_ini is not None and l_fim is not None:
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
                c_ini_crit, l_ini_crit = parse_celula(interv_crit_str.split(":")[0])
                c_fim_crit, l_fim_crit = parse_celula(
                    interv_crit_str.split(":")[-1]
                    if ":" in interv_crit_str
                    else interv_crit_str
                )
                c_ini_soma, l_ini_soma = parse_celula(interv_soma_str.split(":")[0])
                total = 0.0
                if c_ini_crit is not None and c_fim_crit is not None and l_ini_crit is not None and l_fim_crit is not None:
                    for c in range(
                        min(c_ini_crit, c_fim_crit), max(c_ini_crit, c_fim_crit) + 1
                    ):
                        for l in range(
                            min(l_ini_crit, l_fim_crit), max(l_ini_crit, l_fim_crit) + 1
                        ):
                            v_crit = str(
                                obter_valor_celula(
                                    f"{COLUNAS_EXCEL[c]}{l}",
                                    mapa_dados,
                                    historico_visitados.copy(),
                                )
                            ).strip()
                            criterio_val = (
                                str(
                                    obter_valor_celula(
                                        criterio_raw, mapa_dados, historico_visitados.copy()
                                    )
                                ).strip()
                                if re.match(r"^[A-Z]+\d+$", criterio_raw)
                                else criterio_raw
                            )
                            if v_crit.upper() == criterio_val.upper():
                                target_c = c_ini_soma + (c - min(c_ini_crit, c_fim_crit))
                                target_l = l_ini_soma + (l - min(l_ini_crit, l_fim_crit))
                                if 0 <= target_c < len(COLUNAS_EXCEL):
                                    total += obter_valor_numerico(
                                        f"{COLUNAS_EXCEL[target_c]}{target_l}",
                                        mapa_dados,
                                        historico_visitados.copy(),
                                    )
                return int(total) if total.is_integer() else round(total, 4)

        # --- CONT.SE ---
        match_contse = re.match(r"^CONT\.?SE\((.+)\)$", expressao_upper)
        if match_contse:
            args = dividir_argumentos(match_contse.group(1))
            if len(args) == 2:
                interv_str = args[0]
                criterio_raw = args[1].strip().strip('"\'')
                c_ini, l_ini = parse_celula(interv_str.split(":")[0])
                c_fim, l_fim = parse_celula(
                    interv_str.split(":")[-1] if ":" in interv_str else interv_str
                )
                count = 0
                if c_ini is not None and c_fim is not None and l_ini is not None and l_fim is not None:
                    for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
                        for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                            v_crit = str(
                                obter_valor_celula(
                                    f"{COLUNAS_EXCEL[c]}{l}",
                                    mapa_dados,
                                    historico_visitados.copy(),
                                )
                            ).strip()
                            criterio_val = (
                                str(
                                    obter_valor_celula(
                                        criterio_raw, mapa_dados, historico_visitados.copy()
                                    )
                                ).strip()
                                if re.match(r"^[A-Z]+\d+$", criterio_raw)
                                else criterio_raw
                            )
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
                v_busca = (
                    str(
                        obter_valor_celula(
                            v_busca_raw, mapa_dados, historico_visitados.copy()
                        )
                    ).strip()
                    if re.match(r"^[A-Z]+\d+$", v_busca_raw)
                    else v_busca_raw
                )
                inicio, fim = matriz_str.split(":")
                c_ini, l_ini = parse_celula(inicio)
                c_fim, l_fim = parse_celula(fim)
                if c_ini is not None and c_fim is not None and l_ini is not None and l_fim is not None:
                    for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                        if (
                            str(
                                obter_valor_celula(
                                    f"{COLUNAS_EXCEL[c_ini]}{l}",
                                    mapa_dados,
                                    historico_visitados.copy(),
                                )
                            ).strip().upper()
                            == v_busca.upper()
                        ):
                            target_c = c_ini + col_idx - 1
                            if target_c <= c_fim:
                                return obter_valor_celula(
                                    f"{COLUNAS_EXCEL[target_c]}{l}",
                                    mapa_dados,
                                    historico_visitados.copy(),
                                )
                return "#N/A"

        # Avaliação Matemática Padrão
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
                linha_vals.append(
                    ""
                    if res is None or str(res).lower() in ["none", "nan", "null"]
                    else str(res)
                )
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
    for idx, row in df_temp.iterrows():
        ws.append(list(row))

    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("ILUMINAÇÃO DE EMERGÊNCIA")

max_linhas_ativas = len(gerar_dataframe_calculado())
opcoes_celulas = [
    f"{col}{lin}" for lin in range(1, max_linhas_ativas + 1) for col in COLUNAS_EXCEL
]

col_celula, col_fx, col_exp = st.columns([2, 6, 2])

with col_celula:
    celula_selecionada = st.selectbox("Célula", opcoes_celulas, index=0)

val_atual = str(
    st.session_state.matriz_raw.get(celula_selecionada, "")
).strip()
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
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )

st.divider()

# Grade Interativa
df_exibicao = gerar_dataframe_calculado()
df_editado = st.data_editor(
    df_exibicao, use_container_width=True, height=550, key="grid_supabase"
)

# Sincronização inteligente das edições na grid
houve_alteracao = False
for lin_idx, lin in enumerate(range(1, len(df_exibicao) + 1)):
    for col_idx, col in enumerate(COLUNAS_EXCEL):
        celula_ref = f"{col}{lin}"
        val_digitado = df_editado.iat[lin_idx, col_idx]
        val_final = (
            ""
            if pd.isna(val_digitado)
            or val_digitado is None
            or str(val_digitado).strip().lower() in ["none", "nan", "null"]
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
