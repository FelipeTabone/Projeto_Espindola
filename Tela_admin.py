import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import os
import csv
from tkinter import ttk

# Caminho para o arquivo CSV onde os usuários são armazenados
caminho_arquivo = './Base/usuarios.csv'


# Função para garantir que o diretório e o arquivo CSV existam
def garantir_arquivo():
    if not os.path.exists('./Base'):
        os.makedirs('./Base')  # Cria o diretório Base, se não existir
    
    # Se o arquivo não existir, cria um novo
    if not os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "nome", "senha"])  # Cabeçalhos


# Função para carregar os usuários do arquivo CSV
def carregar_usuarios():
    usuarios = []
    try:
        with open(caminho_arquivo, mode='r', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                usuarios.append(f"{row[0]},{row[1]},{row[2]}")  # Formato "id,nome,senha"
    except FileNotFoundError:
        pass  # Se o arquivo não for encontrado, retorna uma lista vazia
    return usuarios


# Função para salvar os usuários no arquivo CSV
def salvar_usuarios():
    with open(caminho_arquivo, mode='w', newline='') as f:
        writer = csv.writer(f)
        for usuario in usuarios:
            usuario_id, nome, senha = usuario.split(',')
            writer.writerow([usuario_id, nome, senha])  # Escreve no formato CSV


# Função para verificar o login
def verificar_login():
    nome_usuario = entry_nome_login.get()
    senha_usuario = entry_senha_login.get()

    # Verifica se as credenciais inseridas correspondem ao pré-definido
    if nome_usuario == "admin" and senha_usuario == "senha123":
        login_window.destroy()  # Fecha a janela de login
        exibir_tela_admin()  # Exibe a tela principal de administração
    else:
        messagebox.showerror("Erro", "Nome de usuário ou senha inválidos.")


# Função para exibir a tela de administração
def exibir_tela_admin():
    global root
    root = ctk.CTk()  # Cria a janela principal
    root.title("Administração de Usuários")
    root.geometry("600x400")

    # Carregar os usuários do arquivo CSV
    global usuarios
    usuarios = carregar_usuarios()

    # Frame para lista de usuários
    frame_lista = ctk.CTkFrame(root)
    frame_lista.pack(pady=10, padx=20, fill="x")

    # Treeview para exibição de usuários (sem a coluna "Senha")
    global treeview_usuarios
    treeview_usuarios = ttk.Treeview(frame_lista, columns=("ID", "Nome"), show="headings", height=10)
    treeview_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurar as colunas
    treeview_usuarios.heading("ID", text="ID")
    treeview_usuarios.heading("Nome", text="Usuário")

    # Barra de rolagem para a treeview
    scrollbar = tk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=treeview_usuarios.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    treeview_usuarios.config(yscrollcommand=scrollbar.set)

    # Campo de entrada para nome de usuário e senha
    global entry_nome, entry_senha
    entry_nome = ctk.CTkEntry(root, placeholder_text="Nome do Usuário", width=300)
    entry_nome.pack(pady=5)

    entry_senha = ctk.CTkEntry(root, placeholder_text="Senha do Usuário", width=300, show="*")
    entry_senha.pack(pady=5)

    # Botões para adicionar, editar e excluir
    frame_botoes = ctk.CTkFrame(root)
    frame_botoes.pack(pady=10)

    btn_adicionar = ctk.CTkButton(frame_botoes, text="Adicionar", command=adicionar_usuario, fg_color="green", text_color="white", hover_color="darkgreen")
    btn_adicionar.pack(side=tk.LEFT, padx=10)

    btn_editar = ctk.CTkButton(frame_botoes, text="Editar", command=editar_usuario)
    btn_editar.pack(side=tk.LEFT, padx=10)

    # Botão Excluir com vermelho escuro e cor de hover igual ao fundo
    btn_excluir = ctk.CTkButton(frame_botoes, text="Excluir", command=excluir_usuario, fg_color="#B22222", text_color="white", hover_color="#8B0000")
    btn_excluir.pack(side=tk.LEFT, padx=10)

    # Inicializa a lista de usuários (se houver algum)
    atualizar_lista_usuarios()

    # Iniciar a aplicação
    root.mainloop()


# Função para adicionar um novo usuário
def adicionar_usuario():
    nome = entry_nome.get()
    senha = entry_senha.get()
    
    if nome and senha:
        # Gerando um id único (incrementando o id com base no tamanho da lista)
        novo_id = len(usuarios) + 1
        novo_usuario = f"{novo_id},{nome},{senha}"
        
        usuarios.append(novo_usuario)
        salvar_usuarios()  # Salva no arquivo
        atualizar_lista_usuarios()
        
        # Limpar campos de entrada
        entry_nome.delete(0, tk.END)
        entry_senha.delete(0, tk.END)
    else:
        messagebox.showwarning("Campos vazios", "Nome e Senha não podem ser vazios.")


def editar_usuario():
    selected_user_index = treeview_usuarios.selection()
    if selected_user_index:
        usuario_selecionado = treeview_usuarios.item(selected_user_index)["values"]
        usuario_id, nome_atual = usuario_selecionado  # Agora só acessamos dois valores (ID e Nome)
        
        # Buscar a senha do usuário a partir do ID na lista de usuários
        senha_atual = ""
        for usuario in usuarios:
            u_id, nome, senha = usuario.split(',')
            if u_id == usuario_id:
                senha_atual = senha
                break
        
        # Chama a função para abrir a tela de edição, passando o ID, nome e senha
        abrir_edicao(usuario_id, nome_atual, senha_atual)
    else:
        messagebox.showwarning("Seleção inválida", "Selecione um usuário para editar.")


# Função para abrir a tela de edição em uma nova janela (Toplevel)
def abrir_edicao(usuario_id, nome_atual, senha_atual):
    # Nova janela de edição
    edit_window = ctk.CTkToplevel(root)
    edit_window.title(f"Editar Usuário - ID {usuario_id}")
    edit_window.geometry("400x300")
    
    # Labels e campos de entrada
    ctk.CTkLabel(edit_window, text="Nome do Usuário").pack(pady=5)
    entry_nome_edicao = ctk.CTkEntry(edit_window, width=300)
    entry_nome_edicao.insert(0, nome_atual)
    entry_nome_edicao.pack(pady=5)
    
    ctk.CTkLabel(edit_window, text="Senha do Usuário").pack(pady=5)
    entry_senha_edicao = ctk.CTkEntry(edit_window, width=300, show="*")
    entry_senha_edicao.insert(0, senha_atual)
    entry_senha_edicao.pack(pady=5)
    
    # Função para salvar as edições
    def salvar_edicao():
        novo_nome = entry_nome_edicao.get()
        nova_senha = entry_senha_edicao.get()
        
        if novo_nome and nova_senha:
            # Atualiza o usuário na lista
            usuarios[int(usuario_id) - 1] = f"{usuario_id},{novo_nome},{nova_senha}"
            salvar_usuarios()  # Salva no arquivo
            atualizar_lista_usuarios()
            edit_window.destroy()  # Fecha a janela de edição
        else:
            messagebox.showwarning("Campos vazios", "Nome e Senha não podem ser vazios.")
    
    # Botão para salvar a edição
    btn_salvar = ctk.CTkButton(edit_window, text="Salvar", command=salvar_edicao)
    btn_salvar.pack(pady=20)


# Função para excluir um usuário selecionado
def excluir_usuario():
    try:
        selected_user_index = treeview_usuarios.selection()
        if selected_user_index:
            usuario_selecionado = treeview_usuarios.item(selected_user_index)["values"]
            usuario_id = usuario_selecionado[0]
            
            usuarios.pop(int(usuario_id)-1)  # Exclui o usuário da lista
            salvar_usuarios()  # Salva no arquivo
            atualizar_lista_usuarios()
        else:
            messagebox.showwarning("Seleção inválida", "Selecione um usuário para excluir.")
    except IndexError:
        messagebox.showwarning("Erro", "Selecione um usuário válido para excluir.")


# Função para atualizar a lista de usuários na interface
def atualizar_lista_usuarios():
    # Limpar a treeview antes de atualizar
    for item in treeview_usuarios.get_children():
        treeview_usuarios.delete(item)
    
    # Inserir novos dados, agora sem a senha
    for usuario in usuarios:
        usuario_id, nome, _ = usuario.split(',')
        treeview_usuarios.insert("", "end", values=(usuario_id, nome))


# Garantir que o diretório e o arquivo CSV existam
garantir_arquivo()

# Iniciar a tela de login
login_window = ctk.CTk()
login_window.title("Login")
login_window.geometry("400x300")

# Labels e campos de entrada
ctk.CTkLabel(login_window, text="Nome de Usuário").pack(pady=5)
entry_nome_login = ctk.CTkEntry(login_window, width=300)
entry_nome_login.pack(pady=5)

ctk.CTkLabel(login_window, text="Senha").pack(pady=5)
entry_senha_login = ctk.CTkEntry(login_window, width=300, show="*")
entry_senha_login.pack(pady=5)

# Botão de login
btn_login = ctk.CTkButton(login_window, text="Entrar", command=verificar_login)
btn_login.pack(pady=20)

login_window.mainloop()
