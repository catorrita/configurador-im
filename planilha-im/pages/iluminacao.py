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
        return {}, ["A", "B", "C", "D"]

    try:
        response = supabase.table(NOME_TABELA).select("*").execute()
        registros = response.data

        if not registros:
            return {}, ["A", "B", "C", "D"]

        primeiro_registro = registros[0]
        colunas_disponiveis = [
            c.upper()
            for c in primeiro_registro.keys()
            if c.upper() != "LINHA" and not c.startswith("_")
        ]
        
        colunas_disponiveis = sorted(list(set(colunas_disponiveis)))
        if not colunas_disponiveis:
            colunas_disponiveis = ["A", "B", "C", "D"]

        mapa_dados = {}
        for reg in registros:
            val_linha = reg.get("LINHA") or reg.get("linha")
            try:
                lin_num = int(val_linha)
            except (TypeError, ValueError):
                continue

            for col in colunas_disponiveis:
                val = reg.get(col, reg.get(col.lower(), ""))
                if val is None or str(val).strip().lower() in ["none", "nan", "null"]:
                    val = ""
                mapa_dados[f"{col}{lin_num}"] = str(val)

        return mapa_dados, colunas_disponiveis
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return {}, ["A", "B", "C", "D"]


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
                    
                    if col in COLUNAS_EXCEL:
                        linhas_dict[lin_int][col] = val if val != "" else None

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
# MOTOR DE FÓRMULAS E CÁLCULOS AVANÇADO
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
    ref = ref.strip().upper()
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


def extrair_argumentos(args_str):
    args = []
    atual = ""
    dentro_aspas = False
    parenteses = 0
    for char in args_str:
        if char == '"' or char == "'":
            dentro_aspas = not dentro_aspas
            atual += char
        elif char == '(' and not dentro_aspas:
            parenteses += 1
            atual += char
        elif char == ')' and not dentro_aspas:
            parenteses -= 1
            atual += char
        elif (char == ';' or char == ',') and not dentro_aspas and parenteses == 0:
            args.append(atual.strip())
            atual = ""
        else:
            atual += char
    if atual.strip():
        args.append(atual.strip())
    return args


def avaliar_formula(formula_str, mapa_dados, historico_visitados=None):
    if historico_visitados is None:
        historico_visitados = set()
    try:
        expressao = formula_str[1:].strip()
        expressao_upper = expressao.upper()

        # 1. Função SOMASE(intervalo; critério; [intervalo_soma])
        if expressao_upper.startswith("SOMASE("):
            match_func = re.match(r"^SOMASE\((.+)\)$", expressao_upper)
            if match_func:
                args = extrair_argumentos(match_func.group(1))
                if len(args) >= 2:
                    intervalo_crit = args[0]
                    criterio = args[1].strip('"\'')
                    intervalo_soma = args[2] if len(args) >= 3 else intervalo_crit

                    total = 0.0
                    if ":" in intervalo_crit and ":" in intervalo_soma:
                        ini_c, fim_c = intervalo_crit.split(":")
                        c_ini_c, l_ini_c = parse_celula(ini_c)
                        c_fim_c, l_fim_c = parse_celula(fim_c)

                        ini_s, fim_s = intervalo_soma.split(":")
                        c_ini_s, l_ini_s = parse_celula(ini_s)
                        c_fim_s, l_fim_s = parse_celula(fim_s)

                        if c_ini_c is not None and c_ini_s is not None:
                            linhas_c = range(min(l_ini_c, l_fim_c), max(l_ini_c, l_fim_c) + 1)
                            linhas_s = range(min(l_ini_s, l_fim_s), max(l_ini_s, l_fim_s) + 1)
                            
                            for idx, l_c in enumerate(linhas_c):
                                if idx < len(linhas_s):
                                    l_s = list(linhas_s)[idx]
                                    ref_c = f"{COLUNAS_EXCEL[c_ini_c]}{l_c}"
                                    ref_s = f"{COLUNAS_EXCEL[c_ini_s]}{l_s}"
                                    val_cel_c = str(obter_valor_celula(ref_c, mapa_dados, historico_visitados.copy())).strip()
                                    
                                    atende = False
                                    if val_cel_c.upper() == criterio.upper():
                                        atende = True
                                    else:
                                        try:
                                            if float(val_cel_c.replace(",", ".")) == float(criterio.replace(",", ".")):
                                                atende = True
                                        except:
                                            pass
                                            
                                    if atende:
                                        total += obter_valor_numerico(ref_s, mapa_dados, historico_visitados.copy())
                    return int(total) if total.is_integer() else round(total, 4)

        # 2. Função SOMA(intervalo ou lista)
        if expressao_upper.startswith("SOMA("):
            match_func = re.match(r"^SOMA\((.+)\)$", expressao_upper)
            if match_func:
                args = extrair_argumentos(match_func.group(1))
                total = 0.0
                for arg in args:
                    if ":" in arg:
                        ini, fim = arg.split(":")
                        c_ini, l_ini = parse_celula(ini)
                        c_fim, l_fim = parse_celula(fim)
                        if c_ini is not None and c_fim is not None:
                            for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
                                for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                                    ref = f"{COLUNAS_EXCEL[c]}{l}"
                                    total += obter_valor_numerico(ref, mapa_dados, historico_visitados.copy())
                    else:
                        if re.match(r"^[A-Z]+\d+$", arg.upper()):
                            total += obter_valor_numerico(arg, mapa_dados, historico_visitados.copy())
                        else:
                            try:
                                total += float(arg.replace(",", "."))
                            except:
                                pass
                return int(total) if total.is_integer() else round(total, 4)

        # 3. Função CORRESP(valor; intervalo; tipo)
        if expressao_upper.startswith("CORRESP("):
            match_func = re.match(r"^CORRESP\((.+)\)$", expressao_upper)
            if match_func:
                args = extrair_argumentos(match_func.group(1))
                if len(args) >= 2:
                    val_busca = args[0].strip('"\'')
                    intervalo = args[1]
                    if ":" in intervalo:
                        ini, fim = intervalo.split(":")
                        c_ini, l_ini = parse_celula(ini)
                        c_fim, l_fim = parse_celula(fim)
                        if c_ini is not None:
                            pos = 1
                            for c in range(min(c_ini, c_fim), max(c_ini, c_fim) + 1):
                                for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                                    ref = f"{COLUNAS_EXCEL[c]}{l}"
                                    val_cel = str(obter_valor_celula(ref, mapa_dados, historico_visitados.copy())).strip()
                                    if val_cel.upper() == val_busca.upper():
                                        return pos
                                    pos += 1
            return "#N/D"

        # 4. Função INDICE(intervalo; linha; [coluna])
        if expressao_upper.startswith("INDICE("):
            match_func = re.match(r"^INDICE\((.+)\)$", expressao_upper)
            if match_func:
                args = extrair_argumentos(match_func.group(1))
                if len(args) >= 2:
                    intervalo = args[0]
                    num_linha = int(float(eval(args[1], {"__builtins__": None}, {})))
                    num_col = int(float(args[2])) if len(args) >= 3 else 1
                    if ":" in intervalo:
                        ini, fim = intervalo.split(":")
                        c_ini, l_ini = parse_celula(ini)
                        c_fim, l_fim = parse_celula(fim)
                        if c_ini is not None:
                            alvo_c = c_ini + num_col - 1
                            alvo_l = l_ini + num_linha - 1
                            if alvo_c < len(COLUNAS_EXCEL):
                                ref_alvo = f"{COLUNAS_EXCEL[alvo_c]}{alvo_l}"
                                return obter_valor_celula(ref_alvo, mapa_dados, historico_visitados.copy())
            return "#REF!"

        # 5. Função PROCV(valor; intervalo; coluna; [falso/verdadeiro])
        if expressao_upper.startswith("PROCV("):
            match_func = re.match(r"^PROCV\((.+)\)$", expressao_upper)
            if match_func:
                args = extrair_argumentos(match_func.group(1))
                if len(args) >= 3:
                    valor_procura = args[0].strip('"\'')
                    intervalo = args[1]
                    col_indice = int(float(args[2])) - 1
                    if ":" in intervalo:
                        ini, fim = intervalo.split(":")
                        c_ini, l_ini = parse_celula(ini)
                        c_fim, l_fim = parse_celula(fim)
                        if c_ini is not None:
                            for l in range(min(l_ini, l_fim), max(l_ini, l_fim) + 1):
                                ref_chave = f"{COLUNAS_EXCEL[c_ini]}{l}"
                                val_celula = str(obter_valor_celula(ref_chave, mapa_dados, historico_visitados.copy())).strip()
                                if val_celula.upper() == valor_procura.upper():
                                    alvo_col_idx = c_ini + col_indice
                                    if alvo_col_idx < len(COLUNAS_EXCEL):
                                        ref_alvo = f"{COLUNAS_EXCEL[alvo_col_idx]}{l}"
                                        return obter_valor_celula(ref_alvo, mapa_dados, historico_visitados.copy())
            return "#N/D"

        # 6. Concatenação com operador & (ex: A1 & " - " & B1)
        if "&" in expressao:
            partes = expressao.split("&")
            resultado_concatenado = ""
            for p in partes:
                p_trim = p.strip()
                if (p_trim.startswith('"') and p_trim.endswith('"')) or (p_trim.startswith("'") and p_trim.endswith("'")):
                    resultado_concatenado += p_trim[1:-1]
                elif re.match(r"^[A-Z]+\d+$", p_trim.upper()):
                    resultado_concatenado += str(obter_valor_celula(p_trim, mapa_dados, historico_visitados.copy()))
                else:
                    resultado_concatenado += p_trim
            return resultado_concatenado

        # 7. Operações Matemáticas Padrão (+, -, *, /, ^)
        expressao_calc = expressao_upper
        refs = re.findall(r"\b[A-Z]+\d+\b", expressao_calc)
        for ref in refs:
            val = obter_valor_numerico(ref, mapa_dados, historico_visitados.copy())
            expressao_calc = re.sub(r"\b" + ref + r"\b", str(val), expressao_calc)

        expressao_calc = expressao_calc.replace("^", "**")
        resultado = eval(expressao_calc, {"__builtins__": None}, {})
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

# Botão de Voltar para a aba menu padrão do Streamlit
if st.button("Voltar", type="primary"):
    st.switch_page("pages/menu.py")

# Botões de Ação Supabase e Excel no topo
col_botoes_topo = st.columns([2, 2, 6])
with col_botoes_topo[0]:
    if st.button("💾 Salvar no Supabase", type="primary", use_container_width=True):
        salvar_dados_supabase()
with col_botoes_topo[1]:
    excel_file = gerar_excel()
    st.download_button(
        label="📥 Exportar Excel",
        data=excel_file,
        file_name="iluminacao_emergencia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.title("ILUMINAÇÃO DE EMERGÊNCIA")

max_linhas_ativas = len(gerar_dataframe_calculado())
opcoes_celulas = [f"{col}{lin}" for lin in range(1, max_linhas_ativas + 1) for col in COLUNAS_EXCEL]

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
    )

st.divider()

# Grade Interativa (st.data_editor)
df_exibicao = gerar_dataframe_calculado()
df_editado = st.data_editor(
    df_exibicao, use_container_width=True, height=520, key="grid_supabase"
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
