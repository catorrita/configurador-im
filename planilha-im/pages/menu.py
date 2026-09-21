import streamlit as st

st.set_page_config(page_title="Menu", page_icon="📋", layout="wide")

st.markdown(
    """
    <style>
        .titulo-menu {
            text-align: center;
            font-size: 36px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 30px;
            color: black;
        }
    </style>
    <div class="titulo-menu">
        Menu Principal
    </div>
    """,
    unsafe_allow_html=True
)

# Caminho da sua imagem
caminho_imagem = r"C:\Users\felipe.binsfeld\python\planilha-im\pages\imagem_menu.png"

# Criando 3 colunas para centralizar a imagem no meio (coluna 2)
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    try:
        st.image(caminho_imagem, use_container_width=True)
    except Exception as e:
        st.error(f"Não foi possível carregar a imagem. Verifique se o caminho está correto: {e}")

# Botão na barra lateral para voltar à tela inicial
if st.sidebar.button("← Voltar para o Início"):
    st.switch_page("app.py")