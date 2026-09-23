import customtkinter as ctk
import pandas as pd
from tkinter import ttk

# Configuração visual do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class TabelaApp(ctk.CTk):

  def __init__(self):
    super().__init__()

    self.title("Consulta de Itens")
    self.geometry("900x600")

    # 1. Botão "VOLTAR" (como na imagem)
    self.btn_voltar = ctk.CTkButton(
        self, text="← VOLTAR", width=120, height=35, command=self.acao_voltar
    )
    self.btn_voltar.pack(anchor="nw", padx=20, pady=15)

    # 2. Campo de Busca (facilita navegar entre muitos itens)
    self.entry_busca = ctk.CTkEntry(
        self, placeholder_text="Pesquisar por código ou descrição..."
    )
    self.entry_busca.pack(fill="x", padx=20, pady=(0, 10))
    self.entry_busca.bind("<KeyRelease>", self.filtrar_dados)

    # 3. Tabela (Treeview)
    self.container_tabela = ctk.CTkFrame(self)
    self.container_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    self.colunas = ("CÓDIGO SGE", "CÓDIGO SAP", "DESC_ITEM")
    self.tabela = ttk.Treeview(
        self.container_tabela, columns=self.colunas, show="headings"
    )

    for col in self.colunas:
      self.tabela.heading(col, text=col)

    # Ajuste de largura das colunas
    self.tabela.column("CÓDIGO SGE", width=120, anchor="center")
    self.tabela.column("CÓDIGO SAP", width=120, anchor="center")
    self.tabela.column("DESC_ITEM", width=550, anchor="w")

    # Barra de Rolagem (Scrollbar)
    scrollbar = ttk.Scrollbar(
        self.container_tabela, orient="vertical", command=self.tabela.yview
    )
    self.tabela.configure(yscroll=scrollbar.set)

    self.tabela.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Carregar dados
    self.carregar_dados()

  def carregar_dados(self):
    try:
      # Lê a planilha Excel
      self.df = pd.read_excel("dados.xlsx", dtype=str)
      self.atualizar_tabela(self.df)
    except Exception as e:
      print(f"Erro ao carregar o arquivo excel: {e}")

  def atualizar_tabela(self, dataframe):
    # Limpa linhas atuais
    for item in self.tabela.get_children():
      self.tabela.delete(item)

    # Insere as novas linhas
    for _, row in dataframe.iterrows():
      self.tabela.insert(
          "",
          "end",
          values=(row["CÓDIGO SGE"], row["CÓDIGO SAP"], row["DESC_ITEM"]),
      )

  def filtrar_dados(self, event):
    termo = self.entry_busca.get().lower()
    if not termo:
      self.atualizar_tabela(self.df)
      return

    # Filtra por qualquer uma das colunas
    df_filtrado = self.df[
        self.df["CÓDIGO SGE"].str.lower().str.contains(termo, na=False)
        | self.df["CÓDIGO SAP"].str.lower().str.contains(termo, na=False)
        | self.df["DESC_ITEM"].str.lower().str.contains(termo, na=False)
    ]
    self.atualizar_tabela(df_filtrado)

  def acao_voltar(self):
    print("Ação do botão Voltar executada.")


if __name__ == "__main__":
  app = TabelaApp()
  app.mainloop()