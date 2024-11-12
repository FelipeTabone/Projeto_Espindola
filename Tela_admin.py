import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import os
import csv


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
        writer.writerow(["id", "nome", "senha"])  # Cabeçalho
        for usuario in usuarios:
            usuario_id, nome, senha = usuario.split(',')
            writer.writerow([usuario_id, nome, senha])  # Escreve no formato CSV


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


# Função para editar um usuário selecionado
def editar_usuario():
    try:
        selected_user_index = lista_usuarios.curselection()
        if selected_user_index:
            usuario_selecionado = usuarios[selected_user_index[0]]
            usuario_id, nome_atual, senha_atual = usuario_selecionado.split(',')
            
            novo_nome = entry_nome.get()
            nova_senha = entry_senha.get()
            
            if novo_nome and nova_senha:
                usuarios[selected_user_index[0]] = f"{usuario_id},{novo_nome},{nova_senha}"
                salvar_usuarios()  # Salva no arquivo
                atualizar_lista_usuarios()
                
                entry_nome.delete(0, tk.END)
                entry_senha.delete(0, tk.END)
            else:
                messagebox.showwarning("Campos vazios", "Nome e Senha não podem ser vazios.")
        else:
            messagebox.showwarning("Seleção inválida", "Selecione um usuário para editar.")
    except IndexError:
        messagebox.showwarning("Erro", "Selecione um usuário válido para editar.")


# Função para excluir um usuário selecionado
def excluir_usuario():
    try:
        selected_user_index = lista_usuarios.curselection()
        if selected_user_index:
            usuarios.pop(selected_user_index[0])
            salvar_usuarios()  # Salva no arquivo
            atualizar_lista_usuarios()
        else:
            messagebox.showwarning("Seleção inválida", "Selecione um usuário para excluir.")
    except IndexError:
        messagebox.showwarning("Erro", "Selecione um usuário válido para excluir.")


# Função para atualizar a lista de usuários na interface
def atualizar_lista_usuarios():
    lista_usuarios.delete(0, tk.END)  # Limpa a lista atual
    
    for usuario in usuarios:
        usuario_id, nome, _ = usuario.split(',')
        lista_usuarios.insert(tk.END, f"{usuario_id} - {nome}")


# Criando a janela principal
root = ctk.CTk()
root.title("Administração de Usuários")
root.geometry("500x350")

# Garantir que o diretório e o arquivo CSV existam
garantir_arquivo()

# Carregar os usuários do arquivo CSV
usuarios = carregar_usuarios()

# Frame para lista de usuários
frame_lista = ctk.CTkFrame(root)
frame_lista.pack(pady=10, padx=20, fill="x")

# Lista de usuários (exemplo)
lista_usuarios = tk.Listbox(frame_lista, height=10, width=50, selectmode=tk.SINGLE)
lista_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Barra de rolagem para a lista
scrollbar = tk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=lista_usuarios.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
lista_usuarios.config(yscrollcommand=scrollbar.set)

# Campo de entrada para nome de usuário e senha
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
