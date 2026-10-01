import os
import streamlit as st

# Criação das colunas (ajuste o número de colunas conforme o seu layout)
col1, col2, col_imagem = st.columns(3)

# --- COLUNA 3: Imagem ---
with col_imagem:
    # Pega o diretório onde o arquivo atual (iluminacao.py) está salvo
    diretorio_atual = os.path.dirname(__file__)
    
    # Junta o diretório atual com o nome da imagem
    caminho_imagem = os.path.join(diretorio_atual, "imagem_menu.png")
    
    if os.path.exists(caminho_imagem):
        st.image(caminho_imagem, use_container_width=True)
    else:
        st.error(f"Não foi possível encontrar a imagem em: {caminho_imagem}")
