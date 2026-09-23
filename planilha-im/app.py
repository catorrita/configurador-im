import streamlit as st
import os

# Configuração da página
st.set_page_config(
    page_title="Configurador IM",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS refinada
st.markdown("""
    <style>
    /* Oculta menus padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Faixa Amarela Superior */
    .yellow-header {
        background-color: #FFFF00;
        border: 1px solid #000000;
        padding: 5px 10px;
        font-weight: bold;
        font-size: 13px;
        color: #000000;
        display: inline-block;
        margin-bottom: 20px;
        font-family: Arial, sans-serif;
    }

    /* Ícone (✖ ou ✔) à esquerda do quadrado verde */
    .status-icon-red {
        color: #C00000;
        font-weight: bold;
        font-size: 18px;
        text-align: center;
        line-height: 35px;
        font-family: Arial, sans-serif;
    }
    
    .status-icon-green {
        color: #70AD47;
        font-weight: bold;
        font-size: 18px;
        text-align: center;
        line-height: 35px;
        font-family: Arial, sans-serif;
    }

    /* Quadrado Verde Totalmente Vazio (Botão sem texto) */
    div[data-testid="stColumn"]:nth-child(2) div.stButton > button {
        background-color: #92D050 !important;
        border: 1px solid #595959 !important;
        width: 35px !important;
        height: 35px !important;
        min-width: 35px !important;
        padding: 0px !important;
        margin: 0px !important;
        border-radius: 0px !important;
        box-shadow: none !important;
    }

    /* Texto da Atividade à direita */
    .activity-label {
        font-family: Arial, sans-serif;
        font-size: 13px;
        color: #000000;
        line-height: 35px;
        font-weight: normal;
        white-space: nowrap;
    }

    /* --- ESTILO DOS BOTÕES DE NAVEGAÇÃO --- */
    .btn-container {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }

    .btn-custom {
        display: inline-block;
        width: 150px;
        color: #FFFFFF !important;
        font-weight: bold;
        font-size: 12px;
        text-align: center;
        text-decoration: none !important;
        padding: 10px 4px;
        font-family: Arial, sans-serif;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        box-sizing: border-box;
    }

    .btn-codigos {
        background-color: #4472C4;
        border: 1px solid #2F5597;
        border-radius: 0px 18px 18px 0px;
    }

    .btn-lista {
        background-color: #ED7D31;
        border: 1px solid #C65911;
        border-radius: 0px 12px 0px 0px;
    }

    .btn-calculos {
        background-color: #FF0000;
        border: 1px solid #C00000;
        border-radius: 0px 12px 0px 0px;
    }

    .btn-bd {
        background-color: #7030A0;
        border: 1px solid #4B206B;
        border-radius: 0px 14px 0px 0px;
    }

    .btn-custom:hover {
        opacity: 0.88;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Cabeçalho Amarelo
st.markdown('<div class="yellow-header">CLIQUE NO QUADRADO ABAIXO CASO A OBRA TENHA A ATIVIDADE AO LADO:</div>', unsafe_allow_html=True)

# Layout Principal: [Atividades] | [Botões] | [Imagem]
col_atividades, col_botoes, col_imagem = st.columns([2.5, 1.1, 3.5])

# --- COLUNA 1: Lista de Atividades ---
with col_atividades:
    atividades = [
        "351 / ILUMINAÇÃO EMERGÊNCIA",
        "352 / ALARME INCENDIO",
        "355 / REDE DE HIDRANTES",
        "357 / CASA DE BOMBAS",
        "358 / EXTINTORES",
        "526 / REDE DE AR COMPRIMIDO",
        "532 - REDE DE AGUA INDUSTRIAL",
        "351 / SINALIZAÇÃO DE EMERGENCIA",
        "534 / INSTALAÇÃO REDE DE GÁS GLP"
    ]

    for idx, label in enumerate(atividades):
        # [Ícone (✖/✔)] | [Quadrado Verde Vazio] | [Texto da Atividade]
        c_icon, c_box, c_text = st.columns([0.25, 0.4, 3.3])
        
        state_key = f"active_{idx}"
        if state_key not in st.session_state:
            st.session_state[state_key] = False

        # Coluna do Ícone (à esquerda do quadrado verde)
        with c_icon:
            if st.session_state[state_key]:
                st.markdown('<div class="status-icon-green">✔</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-icon-red">✖</div>', unsafe_allow_html=True)

        # Coluna do Quadrado Verde (Vazio por dentro)
        with c_box:
            if st.button(" ", key=f"btn_toggle_{idx}"):
                st.session_state[state_key] = not st.session_state[state_key]
                st.rerun()

        # Coluna do Texto
        with c_text:
            st.markdown(f'<div class="activity-label">{label}</div>', unsafe_allow_html=True)


# --- COLUNA 2: Botões de Navegação ---
with col_botoes:
    st.write("") # Espaçamento
    st.markdown("""
        <div class="btn-container">
            <a href="codigos" target="_self" class="btn-custom btn-codigos">CÓDIGOS ➔</a>
            <a href="lista_material" target="_self" class="btn-custom btn-lista">LISTA DE<br>MATERIAL</a>
            <a href="calculos" target="_self" class="btn-custom btn-calculos">CÁLCULOS</a>
            <a href="base_de_dados" target="_self" class="btn-custom btn-bd">BASE DE<br>DADOS</a>
        </div>
    """, unsafe_allow_html=True)


# --- COLUNA 3: Imagem ---
with col_imagem:
    caminho_imagem = r"planilha-im/pages/imagem_menu.png"
    if os.path.exists(caminho_imagem):
        st.image(caminho_imagem, use_container_width=True)
    else:
        st.warning(f"Imagem não encontrada em:\n{caminho_imagem}")