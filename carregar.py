import csv
from tkinter import messagebox

# Função para ler o CSV e retornar os usuários
def carregar_usuarios_csv(caminho_arquivo):
    usuarios = []
    try:
        with open(caminho_arquivo, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 3:  # Verificar se a linha tem 3 campos
                    usuarios.append({
                        'codigo': row[0],
                        'login': row[1],
                        'senha': row[2]
                    })
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar os dados dos usuários.")
    return usuarios


