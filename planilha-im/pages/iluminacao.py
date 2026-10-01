# --- COLUNA 3: Imagem ---
with col_imagem:
    caminho_imagem = "pages/imagem_menu.png"
    if os.path.exists(caminho_imagem):
        st.image(caminho_imagem, use_container_width=True)
    else:
        # Tenta verificar se está na raiz ou caminho relativo ajustado
        caminho_alternativo = r"planilha-im/pages/imagem_menu.png"