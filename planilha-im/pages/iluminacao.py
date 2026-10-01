import os
import streamlit as st

col1, col2, col_imagem = st.columns(3)

with col_imagem:
    st.image(os.path.join(os.path.dirname(__file__), "imagem_menu.png"), use_container_width=True)
