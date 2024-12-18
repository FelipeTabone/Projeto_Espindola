import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
from datetime import datetime
from tkcalendar import DateEntry
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import red, black
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageTk
import locale
import subprocess
import platform
import csv
import os
import io
import shutil
import threading
import time
import pywhatkit as kit
import customtkinter as ctk
from funcoes import aplicar_desfoque, contar_linhas
from validacoes import validar_cnpj, validar_cpf
from carregar import carregar_usuarios_csv
import logging

# Dicionário para armazenar clientes e serviços
clientes = {}
servicos = []
locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

def sair():
    app.quit()

def limpar_tela():
    for widget in app.winfo_children():
        widget.destroy()

def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    app.attributes("-fullscreen", fullscreen)

def end_fullscreen(event=None):
    global fullscreen
    fullscreen = False
    app.attributes("-fullscreen", False)

def salvar_clientes():
    with open('Base/clientes.csv', mode='w', newline='') as arquivo:
        escritor = csv.writer(arquivo)
        for cpf, dados in clientes.items():
            if len(dados) == 3:
                escritor.writerow([cpf, dados[0], dados[1], dados[2]])  # nome, celular, celular2
            else:
                print(f"Entrada inválida para CPF {cpf}: {dados}")  # Alerta sobre entradas inválidas
                
def salvar_servicos():
    with open('Base/servicos.csv', mode='w', newline='') as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerows(servicos)
        
def carregar_clientes():
    global clientes
    clientes = {}  # Reinicie o dicionário para evitar dados antigos
    if os.path.exists('Base/clientes.csv'):
        with open('Base/clientes.csv', mode='r', newline='') as arquivo:
            leitor = csv.reader(arquivo)
            for linha in leitor:
                if len(linha) == 4:  # Atualizado para 4 campos
                    cpf, nome, celular, celular2 = linha  # Inclui celular2
                    clientes[cpf] = (nome, celular, celular2)  # Armazena os 3 campos
    else:
        print("Arquivo clientes.csv não encontrado.")

# Função para carregar serviços
def carregar_servicos():
    if os.path.exists('Base/servicos.csv'):
        try:
            with open('Base/servicos.csv', mode='r', newline='', encoding='latin1') as arquivo:
                leitor = csv.reader(arquivo)
                for linha in leitor:
                    if len(linha) == 9:  # Espera 9 campos agora, incluindo o campo de garantia
                        codigo, observacao, status, data_hora, cpf_cliente, nome_cliente, equipamento, marca, garantia = linha
                        servicos.append([codigo, observacao, status, data_hora, cpf_cliente, nome_cliente, equipamento, marca, garantia])
                    else:
                        print(f"Linha ignorada (formato incorreto): {linha}")
        except UnicodeDecodeError:
            with open('Base/servicos.csv', mode='r', newline='', encoding='utf-8') as arquivo:
                leitor = csv.reader(arquivo)
                for linha in leitor:
                    if len(linha) == 9:  # Espera 9 campos agora, incluindo o campo de garantia
                        codigo, observacao, status, data_hora, cpf_cliente, nome_cliente, equipamento, marca, garantia = linha
                        servicos.append([codigo, observacao, status, data_hora, cpf_cliente, nome_cliente, equipamento, marca, garantia])
                    else:
                        print(f"Linha ignorada (formato incorreto): {linha}")
    
backup_running = True

def contar_linhas(caminho):
    # Tenta abrir o arquivo com diferentes codificações
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return sum(1 for line in f)
    except UnicodeDecodeError:
        # Se ocorrer erro, tenta com 'ISO-8859-1'
        try:
            with open(caminho, 'r', encoding='ISO-8859-1') as f:
                return sum(1 for line in f)
        except Exception as e:
            print(f"Erro ao ler o arquivo {caminho}: {e}")
            return 0  # Retorna 0 caso não consiga contar as linhas


def realizar_backup(caminhos_db, caminho_backup):
    print("Backup thread iniciada.")
    
    while backup_running:
        for caminho_db in caminhos_db:
            try:
                if not os.path.isfile(caminho_db):
                    print(f"Arquivo de banco de dados não encontrado: {caminho_db}")
                    continue  # Pula para o próximo arquivo

                os.makedirs(caminho_backup, exist_ok=True)

                # Nome do arquivo de backup com timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_backup = f"backup_{timestamp}_{os.path.basename(caminho_db)}"
                caminho_backup_completo = os.path.join(caminho_backup, nome_backup)

                # Verifica se o backup já existe
                linhas_original = contar_linhas(caminho_db)
                linhas_backup = 0

                backups_encontrados = []

                # Verifica se há backups existentes e armazena os caminhos
                for backup_file in os.listdir(caminho_backup):
                    if backup_file.startswith("backup_") and backup_file.endswith(os.path.basename(caminho_db)):
                        caminho_backup_antigo = os.path.join(caminho_backup, backup_file)
                        backups_encontrados.append(caminho_backup_antigo)

                # Se houver backups, ordena-os por nome (timestamp) para pegar o mais recente
                if backups_encontrados:
                    backups_encontrados.sort(reverse=True)  # Ordena do mais recente para o mais antigo
                    caminho_backup_antigo = backups_encontrados[0]
                    linhas_backup = contar_linhas(caminho_backup_antigo)
                    print(f"Backup existente encontrado: {caminho_backup_antigo} com {linhas_backup} linhas.")
                else:
                    print(f"Nenhum backup encontrado para {caminho_db}.")

                # Se a diferença de linhas for menor que 1, não faz backup
                if abs(linhas_original - linhas_backup) < 1:
                    print(f"Não foi necessário realizar backup de {caminho_db}. Diferença de linhas: {abs(linhas_original - linhas_backup)}.")
                    continue  # Continua para o próximo arquivo

                # Realiza o backup
                shutil.copy2(caminho_db, caminho_backup_completo)
                print(f"Backup realizado com sucesso: {caminho_backup_completo}")

            except Exception as e:
                print(f"Erro ao realizar backup de {caminho_db}: {e}")

        time.sleep(3600)  # Aguarda 1 hora antes de fazer novos backups

def iniciar_backup_thread(caminhos_db, caminho_backup):
    print("Iniciando thread de backup...")
    backup_thread = threading.Thread(target=realizar_backup, args=(caminhos_db, caminho_backup), daemon=True)
    backup_thread.start()

def manter_interface():
    # Chama essa função repetidamente para manter a interface responsiva
    if backup_running:
        app.after(1000, manter_interface)  # Chama a função novamente em 1 segundo

# Exemplo de uso
caminhos_db = [
    "Base/clientes.csv", 
    "Base/servicos.csv", 
    "Base/vendas.csv", 
    "Base/estoque.csv" 
]  # Substitua pelos caminhos reais
caminho_backup = "./backup" 

if all(os.path.isfile(caminho) for caminho in caminhos_db):
    print("Iniciando backup...")
    iniciar_backup_thread(caminhos_db, caminho_backup)
else:
    print("Um ou mais arquivos de banco de dados não foram encontrados.")

usuario_logado = None  # Variável global para armazenar o usuário logado

logging.basicConfig(
    filename='Base/usuario_atividade.log',  # Nome do arquivo de log
    level=logging.INFO,                # Nível de severidade do log (INFO, DEBUG, WARNING, etc.)
    format='%(asctime)s - %(message)s', # Formato do log (inclui a data/hora)
)

def registrar_acao(usuario, acao):
    log_msg = f"Usuário: {usuario} realizou a ação: {acao}"
    logging.info(log_msg)  # Registra a ação no log

def tela_login():
    limpar_tela()
    
    def login():
        global usuario_logado
        username = entry_username.get()
        password = entry_password.get()

        # Carregar os usuários do CSV
        usuarios = carregar_usuarios_csv('Base/usuarios.csv')  # Ajuste o caminho do seu arquivo CSV aqui

        # Procurar o usuário no CSV
        usuario_encontrado = None
        for usuario in usuarios:
            if usuario['login'] == username and usuario['senha'] == password:
                usuario_encontrado = usuario
                break

        if usuario_encontrado:
            usuario_logado = usuario_encontrado['login']  # Agora armazenamos o login, e não o código
            messagebox.showinfo("Sucesso", f"Bem-vindo, {usuario_logado}!")
            registrar_acao(usuario_logado, "Login bem-sucedido")
            tela_principal()  # Chama a tela principal
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")
            registrar_acao("Login mal sucedido")

    # Frame principal para o fundo
    frame_fundo = ctk.CTkFrame(app)
    frame_fundo.pack(fill=tk.BOTH, expand=True)

    # Adicionando o wallpaper com desfoque
    try:
        bg_image = Image.open("./Imagens/wallpaper.jpg")
        bg_image = bg_image.resize((1920, 1080), Image.LANCZOS)
        bg_image_borrada = aplicar_desfoque(bg_image)
        bg_photo = ImageTk.PhotoImage(bg_image_borrada)

        label_fundo = tk.Label(frame_fundo, image=bg_photo)
        label_fundo.image = bg_photo
        label_fundo.place(relwidth=1, relheight=1)

    except Exception as e:
        print(f"Erro ao carregar a imagem de fundo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem de fundo.")

    # Frame para a barra superior
    barra_superior = ctk.CTkFrame(frame_fundo, fg_color="#000000")
    barra_superior.pack(fill=tk.X)

    # Frame centralizado para a logo
    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)

    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")
        
    # Frame para o botão de tela cheia, alinhado à direita
    frame_botao = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botao.pack(side=tk.RIGHT)

    fullscreen_button = ctk.CTkButton(frame_botao, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40,font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)

    frame_central = ctk.CTkFrame(app, fg_color="black", width=350, height=210)
    frame_central.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)
    frame_central.pack_propagate(False)

    # Colocar o título abaixo do ícone
    label_title = ctk.CTkLabel(frame_central, text="Logar no sistema", font=("Helvetica", 32, "bold"), fg_color="transparent")
    label_title.pack(pady=(20, 10))  # Espaçamento acima e abaixo

    def create_entry_with_icon(frame, icon_path, placeholder, show_password=False):
        entry_frame = ctk.CTkFrame(frame, fg_color="black")
        entry_frame.pack(pady=(10, 0))

        # Carregar o ícone
        icon = Image.open(icon_path)
        icon = icon.resize((20, 20), Image.LANCZOS)
        icon = ImageTk.PhotoImage(icon)

        # Usar CTkLabel para o ícone
        icon_label = ctk.CTkLabel(entry_frame, image=icon, text="", fg_color="black")
        icon_label.image = icon  # Manter a referência
        icon_label.pack(side=ctk.LEFT, padx=(10, 0))

        # Criar a entrada
        entry = ctk.CTkEntry(entry_frame, placeholder_text=placeholder, show='*' if show_password else '')
        entry.pack(side=ctk.LEFT, padx=(5, 10))

        return entry

    entry_username = create_entry_with_icon(frame_central, "./Imagens/icone_usuario.png", "Digite seu usuário")
    entry_password = create_entry_with_icon(frame_central, "./Imagens/icone_senha.png", "Digite sua senha", show_password=True)

    # Frame para os botões
    frame_botoes = ctk.CTkFrame(frame_central, fg_color="black")
    frame_botoes.pack(pady=(10, 0))

    button_sair = ctk.CTkButton(frame_botoes, text="Sair", command=sair, fg_color="#FF5722", hover_color="#E64A19",font=("Arial", 12, "bold"))
    button_sair.pack(side=ctk.LEFT, padx=(0, 10))

    button_login = ctk.CTkButton(frame_botoes, text="Entrar", command=login, fg_color="#4CAF50", hover_color="#388E3C",font=("Arial", 12, "bold"))
    button_login.pack(side=ctk.LEFT)

tempo_cronometro = 3600  # Tempo do cronômetro em segundos
    
def exibir_cronometro():
    global tempo_cronometro
    if tempo_cronometro > 0:
        tempo_cronometro -= 1
        app.after(1000, exibir_cronometro)  # Chama novamente a função após 1 segundo
    else:
        tela_login()  # Redireciona para a tela de login quando o tempo acabar    

def tela_principal():
    limpar_tela()

    global tempo_cronometro  # Acessar a variável global para poder resetar o cronômetro

    if usuario_logado:
        mensagem_bem_vindo = f"Bem-vindo, {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Bem-vindo, visitante!"

    # Frame principal para o fundo
    frame_fundo = ctk.CTkFrame(app)
    frame_fundo.pack(fill=tk.BOTH, expand=True)

    # Adicionando o wallpaper com desfoque
    try:
        bg_image = Image.open("./Imagens/wallpaper.jpg")
        bg_image = bg_image.resize((1920, 1080), Image.LANCZOS)
        bg_image_borrada = aplicar_desfoque(bg_image)
        bg_photo = ImageTk.PhotoImage(bg_image_borrada)

        label_fundo = tk.Label(frame_fundo, image=bg_photo)
        label_fundo.image = bg_photo
        label_fundo.place(relwidth=1, relheight=1)

    except Exception as e:
        print(f"Erro ao carregar a imagem de fundo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem de fundo.")

    # Frame para a barra superior
    barra_superior = ctk.CTkFrame(frame_fundo, fg_color="#000000")
    barra_superior.pack(fill=tk.X)

    # Frame centralizado para a logo
    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)

    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)

    # Botão de log-usuario
    frame_botao_log = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_log.pack(side=tk.LEFT, padx=5)

    log_button = ctk.CTkButton(frame_botao_log, text="Monitoramento", command=tela_log, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    log_button.pack(padx=5, pady=5)

    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    global tempo_cronometro
    tempo_cronometro = 3600  # Resetando o cronômetro antes de iniciar
    exibir_cronometro()  # Iniciar o cronômetro sem exibi-lo na interface

    # Frame pai para centralizar o content_frame
    frame_pai = ctk.CTkFrame(frame_fundo)
    frame_pai.pack(expand=True)

    # Frame que irá conter os widgets
    content_frame = ctk.CTkFrame(frame_pai, fg_color="black", width=400, height=500)
    content_frame.pack(padx=0, pady=0)  # Define as margens externas
    
    content_frame.pack_propagate(False)  # O frame não muda de tamanho com base no conteúdo
    content_frame.pack(pady=0)

    # Frame para os botões
    frame_botoes = ctk.CTkFrame(content_frame, fg_color="black")
    frame_botoes.pack(pady=10)

    # Organizando os botões
    botoes_clientes = [
        ("Cadastro de Cliente", tela_cadastro),
        ("Listar Clientes", tela_listar),
    ]

    botoes_servicos = [
        ("Cadastro de Serviço", tela_cadastro_servicos),
        ("Listar Serviços", tela_listar_servicos),
    ]

    botoes_estoque = [
        ("Controle de Estoque", tela_controle_estoque),
        ("Controle de Vendas", tela_controle_vendas),
    ]

    # Adicionando os botões de Clientes
    label_clientes = tk.Label(frame_botoes, text="Cliente", font=('Futura', 18, 'bold'), bg="black", fg="white")
    label_clientes.pack(pady=(0, 0))

    for texto, comando in botoes_clientes:
        button = ctk.CTkButton(frame_botoes, text=texto, command=comando, fg_color="#4CAF50", hover_color="#388E3C", width=250, height=40,font=("Arial", 14, "bold"))
        button.pack(pady=5)

    # Adicionando os botões de Serviços
    label_servicos = tk.Label(frame_botoes, text="Serviço", font=('Futura', 18, 'bold'), bg="black", fg="white")
    label_servicos.pack(pady=(10, 0))

    for texto, comando in botoes_servicos:
        button = ctk.CTkButton(frame_botoes, text=texto, command=comando, fg_color="#4CAF50", hover_color="#388E3C", width=250, height=40,font=("Arial", 14, "bold"))
        button.pack(pady=5)

    # Adicionando os botões de Estoque
    label_estoque = tk.Label(frame_botoes, text="Estoque", font=('Futura', 18, 'bold'), bg="black", fg="white")
    label_estoque.pack(pady=(10, 0))

    for texto, comando in botoes_estoque:
        button = ctk.CTkButton(frame_botoes, text=texto, command=comando, fg_color="#4CAF50", hover_color="#388E3C", width=250, height=40,font=("Arial", 14, "bold"))
        button.pack(pady=5)

    # Frame para os botões de sair e deslogar
    frame_sair = ctk.CTkFrame(content_frame, fg_color="black")
    frame_sair.pack(pady=5)

    # Botão Sair
    button_sair = ctk.CTkButton(frame_sair, text="Sair", command=sair, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_sair.pack(side=ctk.LEFT)

    # Centralizando o content_frame no frame_pai
    frame_pai.update_idletasks()
    frame_pai.pack(expand=True)

def deslogar():
    global usuario_logado
    usuario_logado = None  # Limpa o usuário logado
    limpar_tela()  # Limpa a tela atual
    tela_login()  # Chama a tela de login

def tela_log():
    # Função para ler o arquivo de log e atualizar a área de texto com filtro de usuário
    def atualizar_logs(filtro_usuario=""):
        try:
            with open('Base/usuario_atividade.log', 'r') as file:
                logs = file.readlines()

            text_area.delete(1.0, tk.END)  # Limpa a área de texto

            # Filtra logs pelo usuário (se o filtro estiver ativo)
            if filtro_usuario:
                logs = [log for log in logs if filtro_usuario.lower() in log.lower()]

            # Inverte a ordem dos logs para mostrar do mais recente para o mais antigo
            logs.reverse()

            # Insere os logs filtrados ou todos os logs
            for log in logs:
                text_area.insert(tk.END, log)
            
        except FileNotFoundError:
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, "Arquivo de log não encontrado.")

    # Função chamada quando o filtro de usuário é alterado
    def aplicar_filtro():
        filtro_usuario = entry_usuario.get()
        atualizar_logs(filtro_usuario)

    # Criação da interface gráfica com Tkinter
    root = tk.Tk()
    root.title("Monitoramento de Logs")

    # Área de texto para exibição dos logs (aumentando a largura e altura)
    text_area = scrolledtext.ScrolledText(root, width=150, height=30, wrap=tk.WORD)
    text_area.pack(padx=10, pady=10)

    # Caixa de entrada para filtrar logs por usuário
    label_usuario = tk.Label(root, text="Filtrar:")
    label_usuario.pack(padx=10, pady=5)

    entry_usuario = tk.Entry(root, width=50)
    entry_usuario.pack(padx=10, pady=5)

    # Botão para aplicar o filtro
    button_aplicar_filtro = tk.Button(root, text="Aplicar Filtro", command=aplicar_filtro)
    button_aplicar_filtro.pack(padx=10, pady=10)

    # Iniciar o monitoramento de logs sem filtro inicial
    atualizar_logs()

#Estoque
def tela_controle_estoque():
    limpar_tela()

    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    # Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(main_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    content_frame = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=content_frame, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    content_frame.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(content_frame, text="Controle de Estoque", font=('Arial', 18, 'bold'), bg="dimgray", fg="black")
    label_titulo.pack(pady=10)
    
    # Frame para os campos de filtro
    frame_filtro = tk.Frame(content_frame, bg="dimgray")
    frame_filtro.pack(pady=5)

    # Campos de filtro
    tk.Label(frame_filtro, text="ID:", bg="dimgray").grid(row=0, column=0, padx=5, pady=5)
    entry_id = tk.Entry(frame_filtro)
    entry_id.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Produto:", bg="dimgray").grid(row=1, column=0, padx=5, pady=5)
    entry_produto = tk.Entry(frame_filtro)
    entry_produto.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Fornecedor:", bg="dimgray").grid(row=2, column=0, padx=5, pady=5)
    entry_fornecedor = tk.Entry(frame_filtro)
    entry_fornecedor.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Quantidade:", bg="dimgray").grid(row=3, column=0, padx=5, pady=5)
    entry_quantidade = tk.Entry(frame_filtro)
    entry_quantidade.grid(row=3, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Valor de Compra: (Unidade)", bg="dimgray").grid(row=4, column=0, padx=5, pady=5)
    entry_valor_compra = tk.Entry(frame_filtro)
    entry_valor_compra.grid(row=4, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Data Inicial (DD/MM/AAAA):", bg="dimgray").grid(row=5, column=0, padx=5, pady=5)
    entry_data_inicial = tk.Entry(frame_filtro)
    entry_data_inicial.grid(row=5, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Data Final (DD/MM/AAAA):", bg="dimgray").grid(row=6, column=0, padx=5, pady=5)
    entry_data_final = tk.Entry(frame_filtro)
    entry_data_final.grid(row=6, column=1, padx=5, pady=5)

    def formatar_data(event):
        data = entry_data_inicial.get()
        data = ''.join(filter(str.isdigit, data))
        if len(data) > 2:
            data = data[:2] + '/' + data[2:]
        if len(data) > 5:
            data = data[:5] + '/' + data[5:]
        entry_data_inicial.delete(0, tk.END)
        entry_data_inicial.insert(0, data)

        # Formatação para a data final também
        data_final = entry_data_final.get()
        data_final = ''.join(filter(str.isdigit, data_final))
        if len(data_final) > 2:
            data_final = data_final[:2] + '/' + data_final[2:]
        if len(data_final) > 5:
            data_final = data_final[:5] + '/' + data_final[5:]
        entry_data_final.delete(0, tk.END)
        entry_data_final.insert(0, data_final)

    entry_data_inicial.bind("<KeyRelease>", formatar_data)
    entry_data_final.bind("<KeyRelease>", formatar_data)

    # Função para aplicar o filtro
    def aplicar_filtro():
        # Limpa a Treeview
        for item in tree.get_children():
            tree.delete(item)

        # Lê os valores dos campos de filtro
        filtro_id = entry_id.get().strip()
        filtro_produto = entry_produto.get().strip().lower()
        filtro_fornecedor = entry_fornecedor.get().strip().lower()
        filtro_quantidade = entry_quantidade.get().strip()
        filtro_valor_compra = entry_valor_compra.get().strip()
        filtro_data_inicial = entry_data_inicial.get().strip()
        filtro_data_final = entry_data_final.get().strip()

        # Converte as datas para o formato datetime
        data_inicial = datetime.strptime(filtro_data_inicial, "%d/%m/%Y") if filtro_data_inicial else None
        data_final = datetime.strptime(filtro_data_final, "%d/%m/%Y") if filtro_data_final else None

        # Carrega produtos do CSV
        arquivo_csv = 'Base/estoque.csv'
        if os.path.isfile(arquivo_csv):
            with open(arquivo_csv, mode='r', newline='') as file:
                reader = csv.reader(file)
                next(reader)  # Pula o cabeçalho
                for row in reader:
                    if len(row) == 6:  # Verifica se a linha tem 6 colunas
                        valor_compra_float = float(row[4])  # Converte a string para float
                        valor_compra_formatado = f"R$ {valor_compra_float:.2f}"  # Formata o valor
                        data_produto = datetime.strptime(row[5], "%d/%m/%Y")  # Converte a data do CSV

                        # Verifica se os filtros correspondem
                        if (filtro_id == "" or filtro_id == row[0]) and \
                           (filtro_produto in row[1].lower() and
                            filtro_fornecedor in row[2].lower() and
                            (filtro_quantidade == "" or filtro_quantidade in row[3]) and
                            (filtro_valor_compra == "" or filtro_valor_compra in str(valor_compra_float)) and
                            (data_inicial is None or data_produto >= data_inicial) and
                            (data_final is None or data_produto <= data_final)):
                            tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], valor_compra_formatado, row[5]))

    # Frame para os botões
    frame_botoes = tk.Frame(content_frame, bg="dimgray")
    frame_botoes.pack(pady=10)

    # Botão de retornar
    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    # Botão para aplicar o filtro
    button_filtrar = tk.Button(frame_botoes, text="Filtrar", command=aplicar_filtro, bg='lightgreen', fg='black')
    button_filtrar.pack(side=tk.LEFT, padx=5)

    # Botão para adicionar produto
    button_adicionar = tk.Button(frame_botoes, text="Adicionar Produto", command=tela_cadastro_produto, bg='lightgreen', fg='black')
    button_adicionar.pack(side=tk.LEFT, padx=5)

    # Botão para aumentar estoque
    button_aumentar_estoque = tk.Button(frame_botoes, text="Aumentar Estoque", command=aumentar_estoque, bg='lightgreen', fg='black')
    button_aumentar_estoque.pack(side=tk.LEFT, padx=5)

    # Botão para realizar venda
    button_vender = tk.Button(frame_botoes, text="Realizar Venda", command=realizar_venda, bg='lightgreen', fg='black')
    button_vender.pack(side=tk.LEFT, padx=5)

    # Frame para a lista de produtos
    frame_lista = tk.Frame(content_frame, bg="dimgray")
    frame_lista.pack(pady=10)

    # Treeview para mostrar os produtos
    global tree
    tree = ttk.Treeview(frame_lista, columns=("ID", "Produto", "Fornecedor", "Quantidade", "Valor de Compra", "Data"), show='headings', height=15)
    tree.pack(side=tk.LEFT, fill=tk.BOTH)

    # Definindo as colunas
    tree.heading("ID", text="ID")
    tree.heading("Produto", text="Produto")
    tree.heading("Fornecedor", text="Fornecedor")
    tree.heading("Quantidade", text="Quantidade")
    tree.heading("Valor de Compra", text="Valor de Compra (Unidade)")
    tree.heading("Data", text="Data da Compra")
    tree.column("ID", width=50)
    tree.column("Produto", width=250)
    tree.column("Fornecedor", width=150)
    tree.column("Quantidade", width=100)
    tree.column("Valor de Compra", width=200)
    tree.column("Data", width=130)

    # Scrollbar para a lista de produtos
    scrollbar_lista = ttk.Scrollbar(frame_lista, orient="vertical", command=tree.yview)
    scrollbar_lista.pack(side=tk.RIGHT, fill=tk.Y)

    tree.configure(yscroll=scrollbar_lista.set)

    # Carrega produtos ao iniciar
    carregar_produtos_do_csv()

    # Centralizando o content_frame no canvas
    content_frame.update_idletasks()
    width = max(canvas.winfo_width(), content_frame.winfo_width())
    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.create_window((width // 2, 0), window=content_frame, anchor="n")

def tela_cadastro_produto():
    janela_cadastro = tk.Toplevel(app)
    janela_cadastro.title("Cadastrar Produto")

    # Frame para os campos de entrada
    frame_entrada = tk.Frame(janela_cadastro)
    frame_entrada.pack(pady=10)

    # Entradas de dados
    tk.Label(frame_entrada, text="Produto:").grid(row=0, column=0, padx=5, pady=5)
    entry_produto = tk.Entry(frame_entrada)
    entry_produto.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Fornecedor:").grid(row=1, column=0, padx=5, pady=5)
    entry_fornecedor = tk.Entry(frame_entrada)
    entry_fornecedor.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Quantidade:").grid(row=2, column=0, padx=5, pady=5)
    entry_quantidade = tk.Entry(frame_entrada)
    entry_quantidade.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Valor de Compra: (Unidade)").grid(row=3, column=0, padx=5, pady=5)
    entry_valor = tk.Entry(frame_entrada)
    entry_valor.grid(row=3, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Data (DD/MM/AAAA):").grid(row=4, column=0, padx=5, pady=5)
    entry_data = tk.Entry(frame_entrada)
    entry_data.grid(row=4, column=1, padx=5, pady=5)

    def formatar_data(event):
        data = entry_data.get()
        # Remove todos os caracteres não numéricos
        data = ''.join(filter(str.isdigit, data))

        if len(data) > 2:
            data = data[:2] + '/' + data[2:]
        if len(data) > 5:
            data = data[:5] + '/' + data[5:]

        entry_data.delete(0, tk.END)
        entry_data.insert(0, data)

    entry_data.bind("<KeyRelease>", formatar_data)

    def confirmar_cadastro():
        adicionar_produto(entry_produto.get(), entry_fornecedor.get(), entry_quantidade.get(), entry_valor.get(), entry_data.get())
        janela_cadastro.destroy()  # Fecha a janela após adicionar

    # Botão para confirmar o cadastro
    button_confirmar = tk.Button(janela_cadastro, text="Confirmar", command=confirmar_cadastro, bg='lightgreen', fg='black')
    button_confirmar.pack(pady=10)

    # Botão para cancelar
    button_cancelar = tk.Button(janela_cadastro, text="Cancelar", command=janela_cadastro.destroy, bg='lightcoral', fg='black')
    button_cancelar.pack(pady=5)

# Função para carregar produtos do arquivo CSV
def carregar_produtos_do_csv():
    arquivo_csv = 'Base/estoque.csv'
    # Limpa os produtos existentes na treeview
    for item in tree.get_children():
        tree.delete(item)

    if os.path.isfile(arquivo_csv):
        with open(arquivo_csv, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Pular o cabeçalho
            for row in reader:
                if len(row) == 6:  # Verifica se a linha tem 6 colunas
                    valor_float = float(row[4])  # Converte a string para float
                    valor_formatado = f"R$ {valor_float:.2f}"  # Formata o valor como R$
                    tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], valor_formatado, row[5]))  # Inclui a data


# Função para adicionar produto e salvar no CSV
def adicionar_produto(produto, fornecedor, quantidade, valor, data):
    valor = valor.replace(',', '.')
    
    if produto and fornecedor and quantidade.isdigit() and valor.replace('.', '', 1).isdigit() and data:
        valor_float = float(valor)  # Mantém como float
        valor_formatado = f"R$ {valor_float:.2f}"  # Formata para exibição

        novo_id = gerar_novo_id()
        tree.insert("", tk.END, values=(novo_id, produto, fornecedor, quantidade, valor_formatado, data))
        salvar_no_csv(novo_id, produto, fornecedor, quantidade, valor_float, data)  # Salva sem o "R$"
        registrar_acao(usuario_logado, f"Adicionado produto. {produto}, Quantidade: {quantidade}")
    else:
        messagebox.showerror("Erro", "Por favor, insira dados válidos.")

# Função para gerar novo ID
def gerar_novo_id():
    arquivo_csv = 'Base/estoque.csv'
    if os.path.isfile(arquivo_csv):
        with open(arquivo_csv, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Ignora o cabeçalho
            ids = [int(row[0]) for row in reader if row]  # Converte os IDs das linhas restantes
            if ids:
                return max(ids) + 1
    return 1

# Função para salvar produto no CSV
def salvar_no_csv(id, produto, fornecedor, quantidade, valor, data):
    arquivo_csv = 'Base/estoque.csv'
    file_exists = os.path.isfile(arquivo_csv)
    with open(arquivo_csv, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["ID", "Produto", "Fornecedor", "Quantidade", "Valor de Compra", "Data"])  # Cabeçalho
        writer.writerow([id, produto, fornecedor, quantidade, valor, data])  # Salva dados

def aumentar_estoque():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showerror("Erro", "Selecione um produto para aumentar o estoque.")
        return

    produto_selecionado = tree.item(selected_item)
    produto_id = produto_selecionado['values'][0]
    produto_nome = produto_selecionado['values'][1]
    quantidade_atual = int(produto_selecionado['values'][3])
    data_atual = produto_selecionado['values'][5]  # Preserva o campo de data, agora no índice 5

    # Cria uma nova janela para coletar a quantidade a ser adicionada
    janela_aumento = tk.Toplevel(app)
    janela_aumento.title("Aumentar Estoque")

    # Frame para os campos de entrada
    frame_entrada = tk.Frame(janela_aumento)
    frame_entrada.pack(pady=10)

    tk.Label(frame_entrada, text=f"Produto: {produto_nome}").grid(row=0, column=0, padx=5, pady=5, columnspan=2)

    # Entradas de dados
    tk.Label(frame_entrada, text="Quantidade a adicionar:").grid(row=1, column=0, padx=5, pady=5)
    entry_quantidade_aumento = tk.Entry(frame_entrada)
    entry_quantidade_aumento.grid(row=1, column=1, padx=5, pady=5)

    def confirmar_aumento():
        try:
            # Obtém a quantidade a ser adicionada
            quantidade_a_adicionar = int(entry_quantidade_aumento.get())

            # Verifica se a quantidade é válida (maior que zero)
            if quantidade_a_adicionar <= 0:
                messagebox.showerror("Erro", "Quantidade deve ser maior que zero.")
                return

            # Calcula a nova quantidade
            nova_quantidade = quantidade_atual + quantidade_a_adicionar

            # Verifica se a quantidade atual é válida
            if nova_quantidade < 0:
                messagebox.showerror("Erro", "A quantidade não pode ser negativa.")
                return

            # Verifica se o item selecionado na árvore está correto
            if not selected_item:
                messagebox.showerror("Erro", "Nenhum item selecionado.")
                return

            # Garantir que produto_selecionado tenha dados suficientes para evitar o IndexError
            if len(produto_selecionado['values']) < 6:  # A árvore tem 6 colunas
                messagebox.showerror("Erro", "Informações do produto incompletas.")
                return

            # Atualiza a árvore com a nova quantidade, preservando o campo de data
            tree.item(selected_item, values=(
                produto_id, 
                produto_nome, 
                produto_selecionado['values'][2],  # Mantém o fornecedor ou outro campo
                nova_quantidade,  # Atualiza a quantidade
                produto_selecionado['values'][4],  # Mantém o valor de compra
                data_atual  # Preserva a data
            ))

            # Salva a nova quantidade no CSV
            salvar_csv_atualizado()

            # Exibe uma mensagem de sucesso
            messagebox.showinfo("Sucesso", f"Estoque de '{produto_nome}' aumentado em {quantidade_a_adicionar} unidades.")

            # Fecha a janela de aumento
            janela_aumento.destroy()

            # Registra a ação do usuário
            registrar_acao(usuario_logado, f"Aumentado estoque. {produto_nome}, Quantidade aumentada: {quantidade_a_adicionar}, nova quantidade: {nova_quantidade}")

        except ValueError:
            # Caso o valor inserido não seja um número válido
            messagebox.showerror("Erro", "Por favor, insira uma quantidade válida.")
        except Exception as e:
            # Captura outros erros inesperados e exibe a mensagem
            messagebox.showerror("Erro", f"Ocorreu um erro inesperado: {str(e)}")

    # Botão para confirmar o aumento
    button_confirmar = tk.Button(janela_aumento, text="Confirmar Aumento", command=confirmar_aumento, bg='lightgreen', fg='black')
    button_confirmar.pack(pady=10)

    # Botão para cancelar
    button_cancelar = tk.Button(janela_aumento, text="Cancelar", command=janela_aumento.destroy, bg='lightcoral', fg='black')
    button_cancelar.pack(pady=5)


def salvar_venda(produto_id, produto_nome, fornecedor_nome, quantidade_venda, valor_venda, valor_compra, cliente_cpf, data_venda):
    with open('Base/vendas.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([produto_id, produto_nome, fornecedor_nome, quantidade_venda, valor_venda, valor_compra, cliente_cpf, data_venda])

# Declarar a variável global
entry_data_venda = None

def formatar_data(event):
    global entry_data_venda
    data = entry_data_venda.get()
    # Remove todos os caracteres não numéricos
    data = ''.join(filter(str.isdigit, data))

    if len(data) > 2:
        data = data[:2] + '/' + data[2:]
    if len(data) > 5:
        data = data[:5] + '/' + data[5:]

    entry_data_venda.delete(0, tk.END)
    entry_data_venda.insert(0, data)

def realizar_venda():
    global entry_data_venda  # Referenciar a variável global
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showerror("Erro", "Selecione um produto para vender.")
        return

    produto_selecionado = tree.item(selected_item)
    produto_id = produto_selecionado['values'][0]
    produto_nome = produto_selecionado['values'][1]
    fornecedor_nome = produto_selecionado['values'][2]
    quantidade_disponivel = int(produto_selecionado['values'][3])
    valor_compra = float(produto_selecionado['values'][4].replace('R$', '').replace(' ', '').replace(',', '.'))

    janela_venda = tk.Toplevel(app)
    janela_venda.title("Venda")

    frame_entrada = tk.Frame(janela_venda)
    frame_entrada.pack(pady=10)

    tk.Label(frame_entrada, text=f"Produto: {produto_nome}").grid(row=0, column=0, padx=5, pady=5, columnspan=2)
    tk.Label(frame_entrada, text=f"Fornecedor: {fornecedor_nome}").grid(row=1, column=0, padx=5, pady=5, columnspan=2)

    tk.Label(frame_entrada, text="Quantidade:").grid(row=2, column=0, padx=5, pady=5)
    entry_quantidade = tk.Entry(frame_entrada)
    entry_quantidade.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Valor de Venda:").grid(row=3, column=0, padx=5, pady=5)
    entry_valor = tk.Entry(frame_entrada)
    entry_valor.grid(row=3, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Cliente:").grid(row=4, column=0, padx=5, pady=5)
    entry_cliente = tk.Entry(frame_entrada)
    entry_cliente.grid(row=4, column=1, padx=5, pady=5)

    tk.Label(frame_entrada, text="Data de Venda (DD/MM/AAAA):").grid(row=5, column=0, padx=5, pady=5)
    entry_data_venda = tk.Entry(frame_entrada)
    entry_data_venda.grid(row=5, column=1, padx=5, pady=5)
    
    # Bind da função de formatação
    entry_data_venda.bind("<KeyRelease>", formatar_data)

    def confirmar_venda():
        try:
            quantidade_venda = int(entry_quantidade.get())
            valor_venda = float(entry_valor.get())
            cliente_cpf = entry_cliente.get().strip()
            data_venda = entry_data_venda.get().strip()

            # Validação da data
            try:
                datetime.strptime(data_venda, '%d/%m/%Y')
            except ValueError:
                messagebox.showerror("Erro", "Data inválida. Use o formato DD/MM/AAAA.")
                return

            if quantidade_venda <= 0 or quantidade_venda > quantidade_disponivel:
                messagebox.showerror("Erro", "Quantidade inválida.")
                return

            if valor_venda <= 0:
                messagebox.showerror("Erro", "Valor de venda inválido.")
                return

            if not cliente_cpf:
                messagebox.showwarning("Aviso", "Nenhum cliente informado. A venda será cancelada.")
                return

            nova_quantidade = quantidade_disponivel - quantidade_venda

            if nova_quantidade >= 0:
                # Atualiza a linha mantendo a data de compra
                tree.item(selected_item, values=(
                    produto_id, 
                    produto_nome, 
                    fornecedor_nome, 
                    nova_quantidade, 
                    produto_selecionado['values'][4],  # Valor de compra
                    produto_selecionado['values'][5]   # Data de compra
                ))
                
                if nova_quantidade == 0:
                    # Se a nova quantidade é 0, remove o item da tree e do CSV
                    tree.delete(selected_item)
                    remover_do_csv(produto_id)

            # Salvar a venda no CSV
            salvar_venda(produto_id, produto_nome, fornecedor_nome, quantidade_venda, valor_venda, valor_compra, cliente_cpf, data_venda)

            # Salvar estoque atualizado no CSV
            salvar_csv_atualizado()

            messagebox.showinfo("Sucesso", f"Venda de {quantidade_venda} unidades de '{produto_nome}' realizada com sucesso para o cliente {cliente_cpf}.")
            janela_venda.destroy()
            
            registrar_acao(usuario_logado, f"Realizado venda. Produto: {produto_nome}, Quantidade vendida: {quantidade_venda}")

        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira valores válidos.")

    button_confirmar = tk.Button(janela_venda, text="Confirmar Venda", command=confirmar_venda, bg='lightgreen', fg='black')
    button_confirmar.pack(pady=10)

    button_cancelar = tk.Button(janela_venda, text="Cancelar", command=janela_venda.destroy, bg='lightcoral', fg='black')
    button_cancelar.pack(pady=5)

def salvar_csv_atualizado():
    arquivo_csv = 'Base/estoque.csv'
    
    with open(arquivo_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Cabeçalho do CSV (ID, Produto, Fornecedor, Quantidade, Valor de Compra, Data)
        writer.writerow(['ID', 'Produto', 'Fornecedor', 'Quantidade', 'Valor de Compra', 'Data'])
        
        for item in tree.get_children():
            values = tree.item(item)['values']
            
            # Verifica se o item tem pelo menos 5 valores válidos antes de continuar (ID, Produto, Fornecedor, Quantidade, Valor de Compra)
            if len(values) < 5:
                print(f"Item com dados incompletos (faltando ID, Produto, Fornecedor, Quantidade ou Valor de Compra): {values}")  # Depuração
                continue  # Ignora este item, pois ele está incompleto
            
            # Extraímos os valores individuais
            produto_id = values[0]
            produto_nome = values[1]
            fornecedor = values[2]
            quantidade = values[3]
            valor_compra = values[4]
            data = values[5] if len(values) > 5 else ''  # Verifica se a data está presente, se não, atribui uma string vazia

            # Garantir que o valor de compra esteja no formato numérico correto
            try:
                valor_compra = float(valor_compra.replace('R$', '').replace(' ', '').replace(',', '.'))
            except ValueError:
                valor_compra = 0.0  # Se houver erro na conversão, coloca 0.0 como valor

            # Se a data está presente, preserva a data original sem alterações
            data_formatada = data if data else ''  # Se a data estiver presente, mantém ela como está. Caso contrário, deixa vazia

            # Escreve os dados no arquivo CSV
            writer.writerow([produto_id, produto_nome, fornecedor, quantidade, valor_compra, data_formatada])

def remover_do_csv(produto_id):
    arquivo_csv = 'Base/estoque.csv'
    produtos = []

    if os.path.isfile(arquivo_csv):
        with open(arquivo_csv, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Ignorar o cabeçalho
            for row in reader:
                if row[0] != str(produto_id):
                    produtos.append(row)

    with open(arquivo_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Produto', 'Fornecedor', 'Quantidade', 'Valor de Compra'])
        writer.writerows(produtos)
        
def tela_controle_vendas():
    limpar_tela()
    
    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    # Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(main_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    content_frame = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=content_frame, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    content_frame.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(content_frame, text="Controle de Vendas", font=('Arial', 24, 'bold'), bg="dimgray", fg="black")
    label_titulo.pack(pady=10)

    # Frame para os campos de filtro
    frame_filtro = tk.Frame(content_frame, bg="dimgray")
    frame_filtro.pack(pady=5)

    # Campos de filtro existentes
    tk.Label(frame_filtro, text="ID:", bg="dimgray").grid(row=0, column=0, padx=5, pady=5)
    entry_id = tk.Entry(frame_filtro)
    entry_id.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Produto:", bg="dimgray").grid(row=1, column=0, padx=5, pady=5)
    entry_produto = tk.Entry(frame_filtro)
    entry_produto.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Fornecedor:", bg="dimgray").grid(row=2, column=0, padx=5, pady=5)
    entry_fornecedor = tk.Entry(frame_filtro)
    entry_fornecedor.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Quantidade:", bg="dimgray").grid(row=3, column=0, padx=5, pady=5)
    entry_quantidade = tk.Entry(frame_filtro)
    entry_quantidade.grid(row=3, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Valor de Venda: (Total)", bg="dimgray").grid(row=4, column=0, padx=5, pady=5)
    entry_valor_venda = tk.Entry(frame_filtro)
    entry_valor_venda.grid(row=4, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Valor de Compra: (Unidade)", bg="dimgray").grid(row=5, column=0, padx=5, pady=5)
    entry_valor_compra = tk.Entry(frame_filtro)
    entry_valor_compra.grid(row=5, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Cliente:", bg="dimgray").grid(row=6, column=0, padx=5, pady=5)
    entry_cliente = tk.Entry(frame_filtro)
    entry_cliente.grid(row=6, column=1, padx=5, pady=5)

     # Campos para Data Inicial e Data Final
    tk.Label(frame_filtro, text="Data Inicial (DD/MM/AAAA):", bg="dimgray").grid(row=7, column=0, padx=5, pady=5)
    entry_data_inicial = tk.Entry(frame_filtro)
    entry_data_inicial.grid(row=7, column=1, padx=5, pady=5)

    tk.Label(frame_filtro, text="Data Final (DD/MM/AAAA):", bg="dimgray").grid(row=8, column=0, padx=5, pady=5)
    entry_data_final = tk.Entry(frame_filtro)
    entry_data_final.grid(row=8, column=1, padx=5, pady=5)

    def formatar_data(entry):
        # Formatação para a data
        data = entry.get()
        data = ''.join(filter(str.isdigit, data))
        if len(data) > 2:
            data = data[:2] + '/' + data[2:]
        if len(data) > 5:
            data = data[:5] + '/' + data[5:]
        entry.delete(0, tk.END)
        entry.insert(0, data)

    # Bind para os campos de Data
    entry_data_inicial.bind("<KeyRelease>", lambda event: formatar_data(entry_data_inicial))
    entry_data_final.bind("<KeyRelease>", lambda event: formatar_data(entry_data_final))


    # Função para aplicar o filtro
    def aplicar_filtro():
        for item in tree_vendas.get_children():
            tree_vendas.delete(item)

        filtro_id = entry_id.get().strip()
        filtro_produto = entry_produto.get().strip().lower()
        filtro_fornecedor = entry_fornecedor.get().strip().lower()
        filtro_quantidade = entry_quantidade.get().strip()
        filtro_valor_venda = entry_valor_venda.get().strip()
        filtro_valor_compra = entry_valor_compra.get().strip()
        filtro_cliente = entry_cliente.get().strip().lower()
        filtro_data_inicial = entry_data_inicial.get().strip()
        filtro_data_final = entry_data_final.get().strip()

        arquivo_csv = 'Base/vendas.csv'
        if os.path.isfile(arquivo_csv):
            with open(arquivo_csv, mode='r', newline='') as file:
                reader = csv.reader(file)
                rows = list(reader)
                for row in rows:
                    if len(row) == 8:  # Verifica se a linha tem 8 colunas
                        valor_venda_float = float(row[4])
                        valor_compra_float = float(row[5])
                        valor_venda_formatado = f"R$ {valor_venda_float:.2f}"
                        valor_compra_formatado = f"R$ {valor_compra_float:.2f}"
                        data_venda_row = row[7]

                        # Verificando se a data de venda está dentro do intervalo
                        if (filtro_data_inicial == "" or data_venda_row >= filtro_data_inicial) and \
                           (filtro_data_final == "" or data_venda_row <= filtro_data_final):
                            
                            if (filtro_id in row[0] and
                                    filtro_produto in row[1].lower() and
                                    filtro_fornecedor in row[2].lower() and
                                    filtro_quantidade in row[3] and
                                    (filtro_valor_venda == "" or filtro_valor_venda in str(valor_venda_float)) and
                                    (filtro_valor_compra == "" or filtro_valor_compra in str(valor_compra_float)) and
                                    filtro_cliente in row[6].lower()):
                                tree_vendas.insert("", tk.END, values=(row[0], row[1], row[2], row[3], valor_venda_formatado, valor_compra_formatado, row[6], data_venda_row))

    # Frame para os botões
    frame_botoes = tk.Frame(frame_filtro, bg="dimgray")
    frame_botoes.grid(row=10, columnspan=2, pady=5)

    # Botão de retornar
    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    # Botão para aplicar o filtro
    button_filtrar = tk.Button(frame_botoes, text="Filtrar", command=aplicar_filtro, bg='lightgreen', fg='black')
    button_filtrar.pack(side=tk.LEFT, padx=5)

    # Frame para a lista de vendas
    frame_lista = tk.Frame(content_frame, bg="dimgray")
    frame_lista.pack(pady=10)

    # Treeview para mostrar as vendas
    tree_vendas = ttk.Treeview(frame_lista, columns=("ID", "Produto", "Fornecedor", "Quantidade", "Valor de Venda", "Valor de Compra", "Cliente", "Data de Venda"), show='headings', height=15)
    tree_vendas.pack(side=tk.LEFT, fill=tk.BOTH)

    # Definindo as colunas
    tree_vendas.heading("ID", text="ID")
    tree_vendas.heading("Produto", text="Produto")
    tree_vendas.heading("Fornecedor", text="Fornecedor")
    tree_vendas.heading("Quantidade", text="Quantidade")
    tree_vendas.heading("Valor de Venda", text="Valor de Venda (Total)")
    tree_vendas.heading("Valor de Compra", text="Valor de Compra (Unidade)")
    tree_vendas.heading("Cliente", text="Cliente")
    tree_vendas.heading("Data de Venda", text="Data de Venda")
    tree_vendas.column("ID", width=50)
    tree_vendas.column("Produto", width=250)
    tree_vendas.column("Fornecedor", width=150)
    tree_vendas.column("Quantidade", width=100)
    tree_vendas.column("Valor de Venda", width=160)
    tree_vendas.column("Valor de Compra", width=190)
    tree_vendas.column("Cliente", width=150)
    tree_vendas.column("Data de Venda", width=120)

    # Scrollbar para a lista de vendas
    scrollbar_vendas = ttk.Scrollbar(frame_lista, orient="vertical", command=tree_vendas.yview)
    scrollbar_vendas.pack(side=tk.RIGHT, fill=tk.Y)

    tree_vendas.configure(yscroll=scrollbar_vendas.set)

    # Função para carregar vendas do arquivo CSV
    def carregar_vendas_do_csv():
        arquivo_csv = 'Base/vendas.csv'
        for item in tree_vendas.get_children():
            tree_vendas.delete(item)

        if os.path.isfile(arquivo_csv):
            with open(arquivo_csv, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) == 8:  # Verifica se a linha tem 8 colunas
                        valor_venda_float = float(row[4])
                        valor_compra_float = float(row[5])
                        valor_venda_formatado = f"R$ {valor_venda_float:.2f}"
                        valor_compra_formatado = f"R$ {valor_compra_float:.2f}"
                        tree_vendas.insert("", tk.END, values=(row[0], row[1], row[2], row[3], valor_venda_formatado, valor_compra_formatado, row[6], row[7]))

    # Carrega as vendas do CSV ao abrir a tela
    carregar_vendas_do_csv()

    # Centralizando o content_frame no canvas
    content_frame.update_idletasks()
    width = max(canvas.winfo_width(), content_frame.winfo_width())
    canvas.config(scrollregion=canvas.bbox("all"))
    canvas.create_window((width // 2, 0), window=content_frame, anchor="n")

#Serviço
def tela_cadastro_servicos():
    limpar_tela()

    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    # Frame principal com scrollbar
    frame_principal = tk.Frame(app, bg="dimgray")
    frame_principal.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(frame_principal)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(frame_principal, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    frame_cadastro_servicos = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame_cadastro_servicos, anchor="n")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_cadastro_servicos.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(frame_cadastro_servicos, text="Cadastro de Serviços", font=('Arial', 18, 'bold'), bg="dimgray")
    label_titulo.pack(pady=10)

    # Código de serviço
    label_codigo = tk.Label(frame_cadastro_servicos, text="Ordem de serviço:", bg="dimgray")
    label_codigo.pack(pady=5)

    frame_codigo = tk.Frame(frame_cadastro_servicos, bg="dimgray")
    frame_codigo.pack(pady=5)

    global label_codigo_exibicao
    label_codigo_exibicao = tk.Label(frame_codigo, font=('Arial', 14), width=25, bg="white")
    label_codigo_exibicao.pack(side=tk.LEFT)

    # Carrega e redimensiona a imagem
    imagem_original = Image.open('./Imagens/icone.png')
    imagem_redimensionada = imagem_original.resize((30, 30), Image.LANCZOS)
    icone = ImageTk.PhotoImage(imagem_redimensionada)

    button_preencher_codigo = tk.Button(frame_codigo, image=icone, command=preencher_codigo, bg='lightgreen', borderwidth=0)
    button_preencher_codigo.image = icone
    button_preencher_codigo.pack(side=tk.LEFT, padx=5)

    # Data e Hora
    label_data_hora = tk.Label(frame_cadastro_servicos, text="Data e Hora:", bg="dimgray")
    label_data_hora.pack(pady=5)

    global label_data_hora_exibicao
    label_data_hora_exibicao = tk.Label(frame_cadastro_servicos, font=('Arial', 14), bg="white")
    label_data_hora_exibicao.pack(pady=5)

    data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    label_data_hora_exibicao.config(text=data_hora_atual)

    # Campo para CPF
    label_cpf = tk.Label(frame_cadastro_servicos, text="CPF/CNPJ do Cliente:", bg="dimgray")
    label_cpf.pack(pady=5)

    frame_cpf = tk.Frame(frame_cadastro_servicos, bg="dimgray")
    frame_cpf.pack(pady=5)

    vcmd_cpf = (frame_cadastro_servicos.register(lambda s: len(s) <= 18), '%P')
    global entry_cpf
    entry_cpf = tk.Entry(frame_cpf, font=('Arial', 14), width=30, validate='key', validatecommand=vcmd_cpf)
    entry_cpf.pack(side=tk.LEFT)
    
    entry_cpf.bind("<KeyRelease>", lambda event: formatar_input_documento_cadastro(entry_cpf))

    # Botão para buscar cliente por CPF
    button_buscar_cliente = tk.Button(frame_cpf, image=icone, command=buscar_cliente, font=('Arial', 14), bg='lightgreen', fg='black')
    button_buscar_cliente.pack(side=tk.LEFT, padx=5)

    # Botão para buscar cliente por nome
    button_buscar_nome = tk.Button(frame_cadastro_servicos, text="Buscar Cliente por Nome", command=buscar_clientes_por_nome, font=('Arial', 14), bg='lightgreen', fg='black')
    button_buscar_nome.pack(pady=5)

    # Nome do Cliente
    label_nome = tk.Label(frame_cadastro_servicos, text="Nome do Cliente:", bg="dimgray")
    label_nome.pack(pady=5)

    global entry_nome
    entry_nome = tk.Entry(frame_cadastro_servicos, font=('Arial', 14), width=30)
    entry_nome.pack(pady=5)
    entry_nome.config(state="readonly")

    # Equipamento
    label_equipamento = tk.Label(frame_cadastro_servicos, text="Equipamento:", bg="dimgray")
    label_equipamento.pack(pady=5)

    global entry_equipamento
    entry_equipamento = tk.Entry(frame_cadastro_servicos, font=('Arial', 14), width=30)
    entry_equipamento.pack(pady=5)

    # Marca
    label_marca = tk.Label(frame_cadastro_servicos, text="Marca do Equipamento:", bg="dimgray")
    label_marca.pack(pady=5)

    global entry_marca
    entry_marca = tk.Entry(frame_cadastro_servicos, font=('Arial', 14), width=30)
    entry_marca.pack(pady=5)

   # Observação
    label_observacao = tk.Label(frame_cadastro_servicos, text="Observação:", bg="dimgray")
    label_observacao.pack(pady=5)

    # Campo para observação
    global entry_observacao
    entry_observacao = tk.Text(frame_cadastro_servicos, font=('Arial', 14), width=50, height=10, wrap=tk.WORD)
    entry_observacao.pack(pady=5)

    # Status do Serviço
    label_status = tk.Label(frame_cadastro_servicos, text="Status do Serviço:", bg="dimgray")
    label_status.pack(pady=5)

    global combo_status
    status_options = [
        "Solicitado orçamento",
        "Orçamento realizado",
        "Orçamento recusado",
        "Orçamento aprovado",
        "Serviço finalizado",
        "Ordem para descarte"
    ]
    combo_status = ttk.Combobox(frame_cadastro_servicos, values=status_options, font=('Arial', 14), state="readonly")
    combo_status.pack(pady=5)

    # Novo campo para Garantia
    global var_garantia
    var_garantia = tk.BooleanVar()  # Variável para o Checkbutton
    label_garantia = tk.Label(frame_cadastro_servicos, text="Serviço de Garantia:", bg="dimgray")
    label_garantia.pack(pady=5)
    check_garantia = tk.Checkbutton(frame_cadastro_servicos, variable=var_garantia, bg="dimgray")
    check_garantia.pack(pady=5)

    frame_botoes = tk.Frame(frame_cadastro_servicos, bg="dimgray")
    frame_botoes.pack(pady=20)

    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    button_adicionar_servico = tk.Button(frame_botoes, text="Adicionar Serviço",
                                          command=lambda: adicionar_servico(label_codigo_exibicao.cget("text"),
                                                                            entry_observacao.get("1.0", tk.END).strip(),
                                                                            combo_status.get(),
                                                                            data_hora_atual.strip(),
                                                                            entry_cpf.get(),
                                                                            entry_equipamento.get(),
                                                                            entry_marca.get(),
                                                                            var_garantia.get()),  # Passa o valor do Checkbutton
                                        bg='lightgreen', fg='black')
    button_adicionar_servico.pack(side=tk.LEFT, padx=5)

    # Centralizando o frame_cadastro_servicos no canvas
    frame_cadastro_servicos.update_idletasks()  # Atualiza o tamanho do frame
    width = frame_cadastro_servicos.winfo_width()
    canvas.create_window((canvas.winfo_width() // 2 - width // 2, 0), window=frame_cadastro_servicos, anchor="n")
    
def buscar_cliente():
    cpf = entry_cpf.get().strip()
    cpf_normalizado = ''.join(filter(str.isdigit, cpf))  # Normaliza o CPF

    if not validar_cpf_existe(cpf_normalizado):
        messagebox.showwarning("Aviso", "CPF não cadastrado.")
        return

    cliente_info = clientes.get(cpf_normalizado)
    if cliente_info:
        entry_nome.config(state="normal")  # Permitir edição temporária
        entry_nome.delete(0, tk.END)
        entry_nome.insert(0, cliente_info[0])  # Insere o nome do cliente
        entry_nome.config(state="readonly")  # Retorna ao estado readonly
    else:
        messagebox.showwarning("Aviso", "Cliente não encontrado.")

def buscar_clientes_por_nome():
    # Cria uma nova janela para busca de clientes
    busca_nome_janela = tk.Toplevel(app)
    busca_nome_janela.title("Buscar Clientes por Nome")
    busca_nome_janela.geometry("600x500")
    busca_nome_janela.config(bg="dimgray")

    label_nome = tk.Label(busca_nome_janela, text="Nome do Cliente:", bg="dimgray", font=('Arial', 14))
    label_nome.pack(pady=10)

    entry_nome_busca = tk.Entry(busca_nome_janela, font=('Arial', 14), width=30)
    entry_nome_busca.pack(pady=5)

    # Lista para exibir os clientes encontrados
    lista_clientes = tk.Listbox(busca_nome_janela, font=('Arial', 14), width=50, height=10)
    lista_clientes.pack(pady=10)

    def filtrar_clientes():
        nome_busca = entry_nome_busca.get().strip().lower()
        clientes_filtrados = [(cpf, info[0]) for cpf, info in clientes.items() if nome_busca in info[0].lower()]

        lista_clientes.delete(0, tk.END)  # Limpa a lista antes de adicionar novos clientes
        for cpf, nome in clientes_filtrados:
            lista_clientes.insert(tk.END, f"{nome} - {cpf}")  # Exibe o nome e o CPF

    button_filtrar = tk.Button(busca_nome_janela, text="Buscar", command=filtrar_clientes, font=('Arial', 14), bg='lightgreen', fg='black')
    button_filtrar.pack(pady=5)

    def selecionar_cliente():
        try:
            selecionado = lista_clientes.curselection()[0]  # Pega o índice do cliente selecionado
            cliente_selecionado = lista_clientes.get(selecionado)
            nome_cliente, cpf_cliente = cliente_selecionado.rsplit(" - ", 1)  # Divide o nome e CPF
            entry_cpf.delete(0, tk.END)
            entry_cpf.insert(0, cpf_cliente)  # Insere o CPF no campo de CPF

            # Busca o nome correspondente para preencher
            cliente_info = clientes.get(cpf_cliente)
            entry_nome.config(state="normal")
            entry_nome.delete(0, tk.END)
            entry_nome.insert(0, cliente_info[0])  # Insere o nome do cliente
            entry_nome.config(state="readonly")
            busca_nome_janela.destroy()  # Fecha a janela de busca
        except IndexError:
            messagebox.showwarning("Aviso", "Selecione um cliente da lista.")

    button_selecionar = tk.Button(busca_nome_janela, text="Selecionar Cliente", command=selecionar_cliente, font=('Arial', 14), bg='lightgreen', fg='black')
    button_selecionar.pack(pady=5)
    
def obter_proximo_codigo():
    # Lógica para determinar o próximo código
    # Por exemplo, se `servicos` é uma lista de serviços cadastrados
    proximo_codigo = len(servicos) + 1  # Calcula o próximo código
    return str(proximo_codigo).zfill(5)  # Retorna o código com 5 dígitos

def preencher_codigo():
    novo_codigo = obter_proximo_codigo()  # Função para obter o próximo código
    label_codigo_exibicao.config(text=novo_codigo)  # Atualiza o label com o novo código
    
def adicionar_servico(codigo, observacao, status, data_hora, cpf, equipamento, marca, garantia):
    if not codigo or not observacao or not status or not cpf or not equipamento or not marca:
        messagebox.showwarning("Aviso", "Os campos Observação, Status, Ordem de serviço, CPF, Equipamento e Marca são obrigatórios.")
        return

    # Normaliza o CPF removendo caracteres especiais
    cpf_normalizado = ''.join(filter(str.isdigit, cpf))

    # Verifica se o código já existe
    if any(servico[0] == codigo for servico in servicos):
        messagebox.showwarning("Aviso", "Essa Ordem de serviço já está cadastrada.")
        return
    
    # Verifica se o CPF está cadastrado
    if not validar_cpf_existe(cpf_normalizado):
        messagebox.showwarning("Aviso", "CPF não cadastrado.")
        return

    # Obtém o nome do cliente a partir do CPF
    cliente_info = clientes.get(cpf_normalizado)
    nome_cliente = cliente_info[0] if cliente_info else "Cliente não encontrado"

    # Adiciona o novo serviço
    servicos.append([codigo, observacao, status, data_hora, cpf_normalizado, nome_cliente, equipamento, marca, garantia])  # Adiciona garantia
    salvar_servicos()  # Salva os serviços

    # Exibe mensagem de sucesso
    messagebox.showinfo("Sucesso", f"Serviço cadastrado com sucesso!\nOrdem de serviço: {codigo}\nData/Hora: {data_hora}\nObservação: {observacao}\nStatus: {status}\nEquipamento: {equipamento}\nMarca: {marca}\nGarantia: {'Sim' if garantia else 'Não'}\nNome: {nome_cliente}\nCPF: {cpf_normalizado}")

    # Limpa os campos de entrada após a adição
    label_codigo_exibicao.config(text='')  # Limpa o código exibido
    entry_observacao.delete("1.0", tk.END)  # Limpa o campo de observação
    combo_status.set('')
    entry_cpf.delete(0, tk.END)  # Limpa o campo de CPF
    entry_equipamento.delete(0, tk.END)  # Limpa o campo de equipamento
    entry_marca.delete(0, tk.END)  # Limpa o campo de marca
    var_garantia.set(False)  # Reseta o Checkbutton

    registrar_acao(usuario_logado, f"Serviço criado. OS: {codigo}, Cliente: {nome_cliente}, CPF/CNPJ: {cpf_normalizado}")

    # Atualiza a tabela de serviços
    carregar_servicos_na_tabela()

    global tree_servicos

    # Seleciona automaticamente o novo serviço adicionado
    for item in tree_servicos.get_children():
        if tree_servicos.item(item)['values'][0] == codigo:
            tree_servicos.selection_set(item)  # Seleciona o serviço recém-adicionado
            tree_servicos.focus(item)  # Coloca o foco no item
            exibir_observacao(None)  # Força a exibição da observação do novo serviço
            break
        
def validar_cpf_existe(cpf):
    # Verifica se o CPF existe nos clientes
     return cpf in clientes

def obter_servico(codigo):
    """Função para obter as informações de um serviço pelo código."""
    for servico in servicos:
        if servico[0] == codigo:
            return servico
    return None

def formatar_cpf(cpf):
    """Formata o CPF para o formato xxx.xxx.xxx-xx."""
    cpf = ''.join(filter(str.isdigit, cpf))  # Remove caracteres não numéricos
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf  # Retorna o CPF sem formatação se não tiver 11 dígitos

def formatar_celular(celular):
    """Formata o celular para o formato (xx) xxxxx-xxxx."""
    celular = ''.join(filter(str.isdigit, celular))  # Remove caracteres não numéricos
    if len(celular) == 11:  # Ex: 11987654321
        return f"({celular[:2]}) {celular[2:7]}-{celular[7:]}"
    return celular  # Retorna o celular sem formatação se não tiver 11 dígitos

def gerar_pdf(codigo):
    template_path = "./Imagens/template.pdf"
    output_pdf_path = f"./PDF_Gerado/servico_{codigo}.pdf"

    # Verifica se o diretório existe
    output_dir = "./PDF_Gerado/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # Carregar o template PDF
        reader = PdfReader(template_path)
        writer = PdfWriter()

        # Criar um buffer em memória para o PDF
        packet = io.BytesIO()
        c = pdf_canvas.Canvas(packet, pagesize=letter)

        # Obter informações do serviço
        servico = obter_servico(codigo)

        if servico:
            c.setFillColor(red)

            # Adicionar o serviço em três locais diferentes
            c.drawString(450, 762, f"{servico[0]}")
            c.drawString(480, 300, f"{servico[0]}")
            c.drawString(170, 299, f"{servico[0]}")
            c.drawString(485, 215, f"{servico[0]}")

            c.setFillColor(black)
            c.setFont("Helvetica", 10)

            # Adicionar observações
            observacao = servico[1]
            x = 19
            y = 595
            max_width = 300
            text_object = c.beginText(x, y)
            text_object.setFont("Helvetica", 10)

            for line in observacao.splitlines():
                while line:
                    if c.stringWidth(line, "Helvetica", 10) <= max_width:
                        text_object.textLine(line)
                        break
                    else:
                        break_index = 0
                        while c.stringWidth(line[:break_index], "Helvetica", 10) < max_width:
                            break_index += 1
                        break_index -= 1
                        text_object.textLine(line[:break_index])
                        line = line[break_index:]

            c.drawText(text_object)

            # Adicionar outros campos
            c.drawString(410, 720, f"{servico[3]}")  # Data/Hora
            c.drawString(205, 71, f"{servico[3]}")  # Data/Hora
            
            # Formatando e adicionando o CPF
            cpf_formatado = formatar_cpf(servico[4])
            c.drawString(425, 695, cpf_formatado)  # CPF
            
            c.drawString(49, 692, f"{servico[5]}")   # Nome do Cliente
            c.drawString(340, 284, f"{servico[5]}")
            c.drawString(47, 284, f"{servico[5]}")
            c.drawString(50, 115, f"{servico[5]}")
            
            # Adicionar Equipamento e Marca
            c.drawString(140, 650, f"{servico[6]}")  # Equipamento
            c.drawString(141, 98, f"{servico[6]}")  # Equipamento
             
            c.drawString(335, 621, f"{servico[7]}")  # Marca

            c.setFillColor(black)
            c.setFont("Helvetica", 15)
            garantia = servico[8]  # Certifique-se de que a garantia esteja no índice correto
            if garantia:  # Verifica se é True
                c.drawString(107, 72, "X")  # Posição onde deseja mostrar o X
            else:
                c.drawString(100, 72, "")  # Não preencher nada

            c.setFillColor(black)
            c.setFont("Helvetica", 10)
            celular = obter_celular_por_cpf(servico[4])
            if celular:
                celular_formatado = formatar_celular(celular)
                c.drawString(310, 665, celular_formatado)  # Celular formatado
            else:
                c.drawString(310, 665, "Celular: Não encontrado")

            c.save()

            # Combinar o conteúdo gerado com o template
            packet.seek(0)
            new_pdf = PdfReader(packet)
            page = reader.pages[0]

            # Mesclar o novo conteúdo na página do template
            page.merge_page(new_pdf.pages[0])
            writer.add_page(page)

            # Salvar o PDF
            with open(output_pdf_path, "wb") as outputStream:
                writer.write(outputStream)
                
            registrar_acao(usuario_logado, f"Gerou PDF/Imprimiu PDF. OS: {codigo}")

            messagebox.showinfo("PDF Gerado", f"Arquivo {output_pdf_path} gerado com sucesso!")
            return output_pdf_path  # Retorna o caminho do PDF gerado
        else:
            messagebox.showerror("Erro", "Serviço não encontrado.")
            return None

    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        messagebox.showerror("Erro", f"Erro ao gerar PDF: {e}")
        return None
    
def obter_celular_por_cpf(cpf):
    if cpf in clientes:
        return clientes[cpf][1]
    return None

def imprimir_pdf(codigo):
    pdf_path = gerar_pdf(codigo)  # Gera o PDF e obtém o caminho
    if pdf_path and os.path.exists(pdf_path):
        if platform.system() == "Windows":
            os.startfile(pdf_path, "print")  # Para Windows
        else:
            # Para Linux, usa o comando lp ou lpr
            try:
                subprocess.run(["lp", pdf_path], check=True)  # ou ["lpr", pdf_path]
                messagebox.showinfo("Impressão", "PDF enviado para impressão.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao enviar PDF para impressão: {e}")
    else:
        messagebox.showerror("Erro", "O PDF para impressão não foi encontrado.")

def enviar_mensagem_whatsapp():
    try:
        item_selecionado = tree_servicos.selection()
        if not item_selecionado:
            messagebox.showwarning("Selecione um Serviço", "Por favor, selecione um serviço.")
            return

        dados_servico = tree_servicos.item(item_selecionado, 'values')

        # Extrair CPF e Nome corretamente
        cliente_info = dados_servico[1]
        partes_cliente = cliente_info.split('-')
        if len(partes_cliente) < 2:
            messagebox.showwarning("Erro", "Formato de cliente inválido.")
            return
        
        cpf_cliente = partes_cliente[0].strip()
        nome_cliente = partes_cliente[1].strip()

        # Tente buscar o celular no dicionário
        celular_cliente = clientes.get(cpf_cliente, (None, None))[1]

        if celular_cliente is None:
            messagebox.showwarning("Erro", "Número de celular não encontrado para este cliente.")
            return

        # Formatação do número do celular
        celular_cliente = ''.join(filter(str.isdigit, celular_cliente))

        if len(celular_cliente) == 11:
            celular_cliente = f"+55{celular_cliente}"
        elif len(celular_cliente) == 10:
            celular_cliente = f"+55{celular_cliente}"
        else:
            messagebox.showwarning("Número Inválido", "O número deve ter 10 ou 11 dígitos (sem contar o +55).")
            return
        
        # Obter o código do serviço
        codigo_servico = dados_servico[0]
        servico_info = dados_servico[2]

        # Criar uma janela para selecionar a mensagem e inserir o orçamento
        def escolher_mensagem():
            # Criar uma nova janela
            mensagem_window = tk.Toplevel(app)
            mensagem_window.title("Escolha a Mensagem")
            mensagem_window.geometry("400x300")  # Aumentando a altura para acomodar os campos adicionais

            # Combobox para selecionar a mensagem
            mensagens = [
                "Seu serviço está pronto.",
                "Enviar orçamento.",
                "Sem conserto."
            ]
            combo_mensagem = ttk.Combobox(mensagem_window, values=mensagens, state="readonly", width=40)
            combo_mensagem.pack(pady=10)
            combo_mensagem.current(0)  # Define a primeira opção como selecionada

            # Campo para inserir as peças que serão trocadas
            label_pecas = tk.Label(mensagem_window, text="Peças a serem trocadas:")
            label_pecas.pack(pady=5)
            entry_pecas = tk.Entry(mensagem_window, width=40)
            entry_pecas.pack(pady=5)

            # Campo para inserir o valor do orçamento
            label_orcamento = tk.Label(mensagem_window, text="Valor do Orçamento:")
            label_orcamento.pack(pady=5)
            entry_orcamento = tk.Entry(mensagem_window, width=20)
            entry_orcamento.pack(pady=5)

            # Botão para confirmar a seleção
            button_confirmar = tk.Button(mensagem_window, text="Enviar", command=lambda: enviar_mensagem_selecionada(combo_mensagem.get(), entry_orcamento.get(), entry_pecas.get(), mensagem_window))
            button_confirmar.pack(pady=5)

        def enviar_mensagem_selecionada(mensagem, orcamento, pecas, window):
            # Formatar a mensagem no modelo solicitado
            if mensagem == "Seu serviço está pronto.":
                mensagem_final = f"Olá, aqui é da Eletro Espíndola, sobre seu equipamento ({servico_info}) em nome de {nome_cliente}, Os {codigo_servico}.\n\n" \
                                 f"-Já está pronto e pode passar para retira-lo. Obrigado.😄"
            elif mensagem == "Enviar orçamento.":
                total = orcamento if orcamento else "N/A"
                mensagem_final = f"Olá, aqui é da Eletro Espíndola, sobre seu equipamento ({servico_info}) em nome de {nome_cliente}, Os {codigo_servico}.\n\n" \
                                 f"Orçamento:\n\n" \
                                 f"{pecas if pecas else 'N/A'}\n\n" \
                                 f"Total: R${total}\n\n" \
                                 f"Podemos efetuar o serviço? Obrigado.😊"
            elif mensagem == "Sem conserto.":
                mensagem_final = f"Olá, aqui é da Eletro Espíndola sobre seu equipamento ({servico_info}) em nome de {nome_cliente}, Os {codigo_servico}.\n\n" \
                                 f"Orçamento:\n\n" \
                                 f"{pecas if pecas else 'N/A'}\n\n" \
                                 f"Infelizmente não será possível efetuar o serviço. Obrigado.😔"

            kit.sendwhatmsg_instantly(celular_cliente, mensagem_final, 10)  # Aguarda 1 segundo
            
             # Registrar a ação de envio de mensagem
            registrar_acao(usuario_logado, f"Enviou mensagem WhatsApp. OS: {codigo_servico}, Celular: {celular_cliente}")
            
            window.destroy()  # Fecha a janela após enviar

        escolher_mensagem()  # Chama a função para abrir a janela de seleção

    except Exception as e:
        messagebox.showerror("Erro", str(e))

def tela_listar_servicos():
    limpar_tela()

    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    if not servicos:
        messagebox.showinfo("Lista de Serviços", "Nenhum serviço cadastrado.")
        return

    global tree_servicos, text_observacao, entry_filtro_codigo, entry_filtro_cpf, entry_filtro_nome
    global entry_filtro_data_inicial, entry_filtro_data_final, combo_status_filtro
    global entry_filtro_equipamento, entry_filtro_marca, combo_garantia_filtro

    # Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem vertical
    scrollbar_y = ttk.Scrollbar(main_frame)
    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

    # Adicionando a barra de rolagem horizontal
    scrollbar_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL)
    scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando as barras de rolagem
    scrollbar_y.config(command=canvas.yview)
    scrollbar_x.config(command=canvas.xview)

    # Frame que irá conter os widgets
    frame_listar = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame_listar, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_listar.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(frame_listar, text="   Lista de Serviços", font=('Arial', 18, 'bold'), bg="dimgray")
    label_titulo.pack(pady=10)

    # Frame para a seção de filtros
    frame_filtros = tk.Frame(frame_listar, bg="dimgray")
    frame_filtros.pack(pady=5)

    # Criar filtros
    filtros = [
        ("Código:", "entry_filtro_codigo"),
        ("CPF:", "entry_filtro_cpf"),
        ("Nome:", "entry_filtro_nome"),
        ("Equipamento:", "entry_filtro_equipamento"),
        ("Marca:", "entry_filtro_marca"),
        ("Status:", None),
        ("Garantia:", None)
    ]

    for i, (label_text, entry_name) in enumerate(filtros):
        label = tk.Label(frame_filtros, text=label_text, bg="dimgray")
        label.grid(row=i, column=0, padx=5)

        if entry_name:
            entry = tk.Entry(frame_filtros)
            entry.grid(row=i, column=1, padx=5)
            globals()[entry_name] = entry
        elif label_text == "Status:":
            status_options = [
                "Todos", "Solicitado orçamento", "Orçamento realizado",
                "Orçamento recusado", "Orçamento aprovado", "Serviço finalizado", "Ordem para descarte"
            ]
            combo_status_filtro = ttk.Combobox(frame_filtros, values=status_options, font=('Arial', 14), state="readonly")
            combo_status_filtro.set("Todos")
            combo_status_filtro.grid(row=i, column=1, padx=5)
        elif label_text == "Garantia:":
            garantia_options = ["Todos", "Sim", "Não"]
            combo_garantia_filtro = ttk.Combobox(frame_filtros, values=garantia_options, font=('Arial', 14), state="readonly")
            combo_garantia_filtro.set("Todos")
            combo_garantia_filtro.grid(row=i, column=1, padx=5)

    # Adicionando campos de Data Inicial e Data Final
    label_data_inicial = tk.Label(frame_filtros, text="Data Inicial:", bg="dimgray")
    label_data_inicial.grid(row=len(filtros), column=0, padx=5)

    entry_filtro_data_inicial = DateEntry(frame_filtros, locale='pt_BR', date_pattern='dd/MM/yyyy',
                                           background='darkblue', foreground='white', borderwidth=2)
    entry_filtro_data_inicial.grid(row=len(filtros), column=1, padx=5)

    label_data_final = tk.Label(frame_filtros, text="Data Final:", bg="dimgray")
    label_data_final.grid(row=len(filtros) + 1, column=0, padx=5)

    entry_filtro_data_final = DateEntry(frame_filtros, locale='pt_BR', date_pattern='dd/MM/yyyy',
                                         background='darkblue', foreground='white', borderwidth=2)
    entry_filtro_data_final.grid(row=len(filtros) + 1, column=1, padx=5)

    # Adicionando colunas vazias para centralizar
    frame_filtros.grid_columnconfigure(0, weight=1)
    frame_filtros.grid_columnconfigure(2, weight=1)

    # Frame para os botões
    frame_botoes = tk.Frame(frame_listar, bg="dimgray")
    frame_botoes.pack(pady=5)

    # Botões
    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=(0, 10))

    button_filtrar = tk.Button(frame_botoes, text="Filtrar", command=aplicar_filtro, bg='lightgreen', fg='black')
    button_filtrar.pack(side=tk.LEFT, padx=(0, 5))
    
    button_enviar_whatsapp = tk.Button(frame_botoes, text="Enviar WhatsApp", command=enviar_mensagem_whatsapp, bg='lightgreen', fg='black')
    button_enviar_whatsapp.pack(side=tk.LEFT, padx=(5, 5))

    button_editar_servico = tk.Button(frame_botoes, text="Editar Serviço", command=editar_servico, bg='lightgreen', fg='black')
    button_editar_servico.pack(side=tk.LEFT, padx=(5, 5))

    button_gerar_pdf = tk.Button(frame_botoes, text="Gerar PDF", 
                                  command=lambda: gerar_pdf(tree_servicos.item(tree_servicos.selection(), 'values')[0]),
                                  bg='lightgreen', fg='black')
    button_gerar_pdf.pack(side=tk.LEFT, padx=(5, 5))

    button_imprimir = tk.Button(frame_botoes, text="Imprimir PDF", 
                                command=lambda: imprimir_pdf(tree_servicos.item(tree_servicos.selection(), 'values')[0]),
                                bg='lightgreen', fg='black')
    button_imprimir.pack(side=tk.LEFT, padx=(5, 0))

    # Frame para a tabela de serviços e a scrollbar
    frame_tree = tk.Frame(frame_listar, bg="dimgray")
    frame_tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # Cria a barra de rolagem vertical
    scrollbar_tree_y = tk.Scrollbar(frame_tree, orient=tk.VERTICAL)
    scrollbar_tree_y.pack(side=tk.RIGHT, fill=tk.Y)

    # Cria a barra de rolagem horizontal
    scrollbar_tree_x = tk.Scrollbar(frame_tree, orient=tk.HORIZONTAL)
    scrollbar_tree_x.pack(side=tk.BOTTOM, fill=tk.X)

    # Cria o Treeview com as novas colunas, incluindo "Garantia"
    tree_servicos = ttk.Treeview(frame_tree, columns=("Codigo", "Cliente", "Equipamento", "Marca", "Status", "DataHora", "Garantia"), show='headings', 
                                  yscrollcommand=scrollbar_tree_y.set, xscrollcommand=scrollbar_tree_x.set)

    # Configura as colunas do Treeview
    for col in ["Codigo", "Cliente", "Equipamento", "Marca", "Status", "DataHora", "Garantia"]:
        tree_servicos.heading(col, text=col)
        tree_servicos.column(col, width=50 if col == "Codigo" else (100 if col == "Garantia" else 300))

    tree_servicos.pack(expand=True, fill=tk.BOTH)

    # Configura a barra de rolagem para funcionar com o Treeview
    scrollbar_tree_y.config(command=tree_servicos.yview)
    scrollbar_tree_x.config(command=tree_servicos.xview)
    tree_servicos.bind('<<TreeviewSelect>>', exibir_observacao)

    # Frame para exibir a observação selecionada
    frame_observacao = tk.Frame(frame_listar, bg="dimgray")
    frame_observacao.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    label_observacao = tk.Label(frame_observacao, text="Observação:", bg="dimgray")
    label_observacao.pack(pady=5)

    text_observacao = tk.Text(frame_observacao, font=('Arial', 12), height=10, wrap=tk.WORD)
    text_observacao.pack(expand=True, fill=tk.BOTH)

    # Carrega os serviços na tabela
    carregar_servicos_na_tabela()

    # Seleciona automaticamente o primeiro serviço, se houver, e exibe sua observação
    if tree_servicos.get_children():
        first_item = tree_servicos.get_children()[0]
        tree_servicos.selection_set(first_item)
        tree_servicos.focus(first_item)
        exibir_observacao(None)

    # Centralizando o frame_listar no canvas
    frame_listar.update_idletasks()  # Atualiza o tamanho do frame
    width = max(canvas.winfo_width(), frame_listar.winfo_width())
    canvas.create_window((width // 2, 0), window=frame_listar, anchor="n")

def carregar_servicos_na_tabela(filtro_codigo="", filtro_cpf="", filtro_nome="", filtro_equipamento="", filtro_marca="", filtro_status="Todos", filtro_garantia="Todos", filtro_data_inicial=None, filtro_data_final=None):
    tree_servicos.delete(*tree_servicos.get_children())

    for codigo, observacao, status, data_hora, cpf_cliente, nome_cliente, equipamento, marca, garantia in servicos:
        # Converter garantia de string para booleano
        garantia = garantia == "True"

        if isinstance(status, bytes):
            try:
                status = status.decode('latin1')
            except UnicodeDecodeError:
                print(f"Erro ao decodificar status: {status}")
                status = str(status)
        elif not isinstance(status, str):
            print(f"Status não é uma string ou bytes: {status}")
            status = str(status)

        # Verifica cada critério de filtro individualmente
        if filtro_codigo and filtro_codigo not in str(codigo):
            continue
        if filtro_cpf and filtro_cpf not in cpf_cliente:
            continue
        if filtro_nome and filtro_nome.lower() not in nome_cliente.lower():
            continue
        if filtro_equipamento and filtro_equipamento.lower() not in equipamento.lower():
            continue
        if filtro_marca and filtro_marca.lower() not in marca.lower():
            continue
        if filtro_status != "Todos" and filtro_status != status:
            continue

        # Filtragem da garantia
        if filtro_garantia != "Todos":
            if filtro_garantia == "Sim" and not garantia:  # Se filtro for "Sim", mas garantia for False
                continue
            elif filtro_garantia == "Não" and garantia:  # Se filtro for "Não", mas garantia for True
                continue

        # Filtragem das datas
        data_base = data_hora.split()[0]
        if filtro_data_inicial and data_base < filtro_data_inicial.strftime('%d/%m/%Y'):
            continue
        if filtro_data_final and data_base > filtro_data_final.strftime('%d/%m/%Y'):
            continue

        cliente_info = f"{cpf_cliente} - {nome_cliente}" if cpf_cliente else f"Cliente não encontrado - {nome_cliente}"
        # Inserindo na tabela com conversão de booleano para "Sim" ou "Não"
        tree_servicos.insert("", tk.END, values=(codigo, cliente_info, equipamento, marca, status, data_hora, "Sim" if garantia else "Não"))

    if not tree_servicos.get_children():
        messagebox.showinfo("Resultado da Filtragem", "Nenhum serviço encontrado com os critérios especificados.")

def exibir_observacao(event):
    text_observacao.delete(1.0, tk.END)
    item = tree_servicos.selection()
    if item:
        item_id = item[0]
        codigo = tree_servicos.item(item_id, 'values')[0]
        for servico in servicos:
            if servico[0] == codigo:
                text_observacao.insert(tk.END, servico[1])
                break
            
def aplicar_filtro():
    filtro_codigo = entry_filtro_codigo.get().strip()
    filtro_cpf = entry_filtro_cpf.get().strip()
    filtro_nome = entry_filtro_nome.get().strip()
    filtro_equipamento = entry_filtro_equipamento.get().strip()
    filtro_marca = entry_filtro_marca.get().strip()
    filtro_status = combo_status_filtro.get()
    filtro_garantia = combo_garantia_filtro.get()  # Novo filtro de garantia
    
    filtro_data_inicial = entry_filtro_data_inicial.get_date() if hasattr(entry_filtro_data_inicial, 'get_date') else None
    filtro_data_final = entry_filtro_data_final.get_date() if hasattr(entry_filtro_data_final, 'get_date') else None

    tree_servicos.delete(*tree_servicos.get_children())

    carregar_servicos_na_tabela(filtro_codigo, filtro_cpf, filtro_nome, filtro_equipamento, filtro_marca, filtro_status, filtro_garantia, filtro_data_inicial, filtro_data_final)

def editar_servico():
    selected_item = tree_servicos.selection()
    if not selected_item:
        messagebox.showwarning("Aviso", "Selecione um serviço para editar.")
        return
    
    codigo_servico = tree_servicos.item(selected_item[0], 'values')[0]
    tela_editar_servico(codigo_servico)

def tela_editar_servico(codigo_servico):
    global entry_cpf, entry_nome, combo_status, entry_data_hora
    global text_observacao, entry_equipamento, entry_marca
    global codigo_servico_antigo, data_hora_servico_antigo
    codigo_servico_antigo = codigo_servico
    global combo_garantia

    # Limpa a tela anterior
    limpar_tela()

    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    # Criação de um Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(main_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    frame = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame.bind("<Configure>", configure_scroll_region)

    label_titulo = tk.Label(frame, text="Editar Serviço", font=('Arial', 18, 'bold'), bg="dimgray")
    label_titulo.pack(pady=5)

    # Campos de CPF
    label_cpf = tk.Label(frame, text="CPF do Cliente:", bg="dimgray")
    label_cpf.pack(pady=5)
    
    entry_cpf = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_cpf.pack(pady=5)

    # Campo para Nome
    label_nome = tk.Label(frame, text="Nome do Cliente:", bg="dimgray")
    label_nome.pack(pady=5)

    entry_nome = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_nome.pack(pady=5)

    # Campo para Equipamento
    label_equipamento = tk.Label(frame, text="Equipamento:", bg="dimgray")
    label_equipamento.pack(pady=5)

    entry_equipamento = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_equipamento.pack(pady=5)

    # Campo para Marca
    label_marca = tk.Label(frame, text="Marca:", bg="dimgray")
    label_marca.pack(pady=5)

    entry_marca = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_marca.pack(pady=5)

    # Campo para Data/Hora
    label_data_hora = tk.Label(frame, text="Data/Hora:", bg="dimgray")
    label_data_hora.pack(pady=5)
    
    entry_data_hora = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_data_hora.pack(pady=5)
    entry_data_hora.config(state="readonly")

    label_observacao = tk.Label(frame, text="Observação:", bg="dimgray")
    label_observacao.pack(pady=5)

    text_observacao = tk.Text(frame, font=('Arial', 14), width=50, height=10, wrap=tk.WORD)
    text_observacao.pack(pady=5)

    label_status = tk.Label(frame, text="Status do Serviço:", bg="dimgray")
    label_status.pack(pady=5)

    status_options = [
        "Solicitado orçamento",
        "Orçamento realizado",
        "Orçamento recusado",
        "Orçamento aprovado",
        "Serviço finalizado",
        "Ordem para descarte"
    ]
    combo_status = ttk.Combobox(frame, values=status_options, font=('Arial', 14), state="readonly")
    combo_status.pack(pady=5)
    
        # Campo para Garantia
    label_garantia = tk.Label(frame, text="Garantia:", bg="dimgray")
    label_garantia.pack(pady=5)

    combo_garantia = ttk.Combobox(frame, values=["Sim", "Não"], font=('Arial', 14), state="readonly")
    combo_garantia.pack(pady=5)

    frame_botoes = tk.Frame(frame, bg="dimgray")
    frame_botoes.pack(pady=20)

    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_listar_servicos, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    button_atualizar_servico = tk.Button(frame_botoes, text="Atualizar Serviço", command=atualizar_servico, bg='lightgreen', fg='black')
    button_atualizar_servico.pack(side=tk.LEFT, padx=5)

    # Preenche os campos com as informações do serviço, se encontrado
    for servico in servicos:
        if servico[0] == codigo_servico:
            text_observacao.delete(1.0, tk.END)
            text_observacao.insert(tk.END, servico[1])
            combo_status.set(servico[2])
            entry_data_hora.config(state="normal")
            entry_data_hora.delete(0, tk.END)
            entry_data_hora.insert(0, servico[3])
            entry_data_hora.config(state="readonly")
            entry_cpf.delete(0, tk.END)
            entry_cpf.insert(0, servico[4])  # CPF do cliente
            entry_nome.delete(0, tk.END)
            entry_nome.insert(0, servico[5])  # Nome do cliente
            entry_equipamento.delete(0, tk.END)
            entry_equipamento.insert(0, servico[6])  # Equipamento
            entry_marca.delete(0, tk.END)
            entry_marca.insert(0, servico[7])  # Marca
            combo_garantia.set("Sim" if servico[8] else "Não")  # Garantia
            entry_nome.config(state="readonly")
            break

    # Centralizando o frame no canvas
    frame.update_idletasks()  # Atualiza o tamanho do frame
    canvas.create_window((canvas.winfo_width() // 2, 0), window=frame, anchor="n")  # Ajusta a posição do frame

def atualizar_nome_cliente(event):
    cpf = entry_cpf.get().strip()
    cpf_normalizado = ''.join(filter(str.isdigit, cpf))
    
    # Obtém a informação do cliente diretamente pelo CPF normalizado
    cliente_info = clientes.get(cpf_normalizado)
    
    if cliente_info:
        nome_cliente = cliente_info[0]
    else:
        nome_cliente = "Cliente não encontrado"
    
    entry_nome.config(state="normal")  # Permitir temporariamente a modificação
    entry_nome.delete(0, tk.END)
    entry_nome.insert(0, nome_cliente)
    entry_nome.config(state="readonly")  # Retornar ao estado readonly

codigo_servico_antigo = None  # Inicialização no início do seu programa

def atualizar_servico():
    global codigo_servico_antigo, text_observacao, combo_status, entry_data_hora, entry_cpf, entry_nome
    global entry_equipamento, entry_marca
    global combo_garantia
    
    observacao = text_observacao.get("1.0", tk.END).strip()
    status = combo_status.get()
    nova_data_hora = entry_data_hora.get().strip()
    novo_cpf = entry_cpf.get().strip()
    novo_nome = entry_nome.get().strip()
    novo_equipamento = entry_equipamento.get().strip()
    nova_marca = entry_marca.get().strip()
    novo_garantia = combo_garantia.get() == "Sim"

    if not observacao or not status or not nova_data_hora or not novo_cpf or not novo_nome or not novo_equipamento or not nova_marca:
        messagebox.showwarning("Aviso", "Todos os campos são obrigatórios.")
        return

    if codigo_servico_antigo is not None:
        for index, servico in enumerate(servicos):
            if servico[0] == codigo_servico_antigo:
                # Atualiza o serviço com os novos valores
                servicos[index] = [codigo_servico_antigo, observacao, status, nova_data_hora, novo_cpf, novo_nome, novo_equipamento, nova_marca, novo_garantia]
                salvar_servicos()  # Certifique-se de que esta função salva corretamente
                messagebox.showinfo("Sucesso", "Serviço atualizado com sucesso!")
                
                registrar_acao(usuario_logado, f"Serviço editado. OS: {codigo_servico_antigo}")
                
                # Limpeza dos campos
                limpar_campos()  # Função para limpar os campos
                tela_listar_servicos()  # Atualiza a lista após a edição
                return

    messagebox.showwarning("Aviso", "Serviço não encontrado.")

def limpar_campos():
    text_observacao.delete(1.0, tk.END)
    entry_data_hora.delete(0, tk.END)
    entry_cpf.delete(0, tk.END)
    entry_nome.delete(0, tk.END)
    entry_equipamento.delete(0, tk.END)
    entry_marca.delete(0, tk.END)
    combo_garantia.set('')  # Limpa o campo de garantia
    combo_status.set('')  # Limpa o campo de status
    
    tela_listar_servicos()

#Cliente
def tela_cadastro():
    limpar_tela()
    
    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    # Frame principal com scrollbar
    frame_principal = tk.Frame(app, bg="dimgray")
    frame_principal.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(frame_principal)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(frame_principal, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    frame_cadastro = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame_cadastro, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_cadastro.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(frame_cadastro, text="Cadastro de Cliente", font=('Arial', 18, 'bold'), bg="dimgray")
    label_titulo.pack(pady=10)

    label_nome = tk.Label(frame_cadastro, text="Nome Completo: (Obrigatório)", bg="dimgray")
    label_nome.pack(pady=5)

    global entry_nome, entry_celular, entry_celular2, entry_cpf
    entry_nome = tk.Entry(frame_cadastro, font=('Arial', 14), width=30)
    entry_nome.pack(pady=5)

    def formatar_nome(event):
        nome_atual = entry_nome.get()
        if nome_atual:
            nome_formatado = nome_atual.title()
            entry_nome.delete(0, tk.END)
            entry_nome.insert(0, nome_formatado)

    entry_nome.bind("<KeyRelease>", formatar_nome)

    label_celular = tk.Label(frame_cadastro, text="Celular: (Obrigatório)", bg="dimgray")
    label_celular.pack(pady=5)

    entry_celular = tk.Entry(frame_cadastro, font=('Arial', 14), width=30)
    entry_celular.pack(pady=5)

    label_celular2 = tk.Label(frame_cadastro, text="Celular 2: (Opcional)", bg="dimgray")
    label_celular2.pack(pady=5)

    entry_celular2 = tk.Entry(frame_cadastro, font=('Arial', 14), width=30)
    entry_celular2.pack(pady=5)

    label_cpf = tk.Label(frame_cadastro, text="CPF ou CNPJ: (Obrigatório)", bg="dimgray")
    label_cpf.pack(pady=5)

    vcmd = (frame_cadastro.register(lambda s: len(s) <= 18), '%P')
    entry_cpf = tk.Entry(frame_cadastro, font=('Arial', 14), width=30, validate='key', validatecommand=vcmd)
    entry_cpf.pack(pady=5)

    entry_cpf.bind("<KeyRelease>", lambda event: formatar_input_documento_cadastro(entry_cpf))

     # Frame para os botões "Cadastrar Cliente" e "Retornar"
    frame_botoes = tk.Frame(frame_cadastro, bg="dimgray")
    frame_botoes.pack(pady=20)

    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    button_adicionar = tk.Button(frame_botoes, text="Cadastrar Cliente", command=adicionar_cliente, bg='lightgreen', fg='black')
    button_adicionar.pack(side=tk.LEFT, padx=5)

    frame_cadastro.update_idletasks()
    width = frame_cadastro.winfo_width()
    height = frame_cadastro.winfo_height()
    canvas.create_window((canvas.winfo_width() // 2 - width // 2, 0), window=frame_cadastro, anchor="nw")

def adicionar_cliente():
    nome = entry_nome.get()
    celular = entry_celular.get()
    celular2 = entry_celular2.get()  or "Sem celular"
    documento = entry_cpf.get().replace('.', '').replace('/', '').replace('-', '')

    if not nome or not celular or not documento:
        messagebox.showwarning("Aviso", "Os campos Nome Completo, Celular e CPF/CNPJ são obrigatórios.")
        return

    if len(documento) == 11:
        if not validar_cpf(documento):
            messagebox.showwarning("Aviso", "CPF inválido.")
            return
    elif len(documento) == 14:
        if not validar_cnpj(documento):
            messagebox.showwarning("Aviso", "CNPJ inválido.")
            return
    else:
        messagebox.showwarning("Aviso", "Documento deve conter 11 (CPF) ou 14 (CNPJ) dígitos.")
        return

    if documento in clientes:
        messagebox.showwarning("Aviso", "Esse CPF/CNPJ já está cadastrado.")
        return

    # Adiciona o cliente com o celular2
    clientes[documento] = (nome, celular, celular2)
    salvar_clientes()
    messagebox.showinfo("Sucesso", f"Cliente {nome} adicionado com sucesso.")

    entry_nome.delete(0, tk.END)
    entry_celular.delete(0, tk.END)
    entry_celular2.delete(0, tk.END)  # Limpa o campo celular 2
    entry_cpf.delete(0, tk.END)
    
    registrar_acao(usuario_logado, f"Criar o cliente: {nome}, CPF/CNPJ: {documento}")

def formatar_input_documento_cadastro(entry):
    """
    Formata a entrada de CPF ou CNPJ enquanto o usuário digita.
    """
    input_text = entry.get().replace('.', '').replace('/', '').replace('-', '')
    
    if len(input_text) > 14:
        input_text = input_text[:14]  # Limitar a 14 caracteres
    
    if len(input_text) <= 11:  # CPF
        input_text = (f"{input_text[:3]}{'.' if len(input_text) >= 3 else ''}"
                       f"{input_text[3:6]}{'.' if len(input_text) >= 6 else ''}"
                       f"{input_text[6:9]}{'-' if len(input_text) == 11 else ''}"
                       f"{input_text[9:]}")
    else:  # CNPJ
        input_text = (f"{input_text[:2]}{'.' if len(input_text) >= 2 else ''}"
                       f"{input_text[2:5]}{'.' if len(input_text) >= 5 else ''}"
                       f"{input_text[5:8]}{'/' if len(input_text) >= 8 else ''}"
                       f"{input_text[8:12]}{'-' if len(input_text) == 14 else ''}"
                       f"{input_text[12:]}")
    
    entry.delete(0, tk.END)
    entry.insert(0, input_text)
    
def formatar_input_documento(event):
    """
    Formata o input do CPF ou CNPJ enquanto o usuário digita.
    """
    # Remove qualquer formatação existente
    input_text = entry_filtro_documento.get().replace('.', '').replace('/', '').replace('-', '')

    # Verifica o comprimento do texto
    if len(input_text) <= 11:  # CPF
        formatted = f"{input_text[:3]}{'.' if len(input_text) >= 3 else ''}" \
                    f"{input_text[3:6]}{'.' if len(input_text) >= 6 else ''}" \
                    f"{input_text[6:9]}{'-' if len(input_text) == 11 else ''}" \
                    f"{input_text[9:]}"
    elif len(input_text) <= 14:  # CNPJ
        formatted = f"{input_text[:2]}{'.' if len(input_text) >= 2 else ''}" \
                    f"{input_text[2:5]}{'.' if len(input_text) >= 5 else ''}" \
                    f"{input_text[5:8]}/" \
                    f"{input_text[8:12]}{'-' if len(input_text) == 14 else ''}" \
                    f"{input_text[12:]}"
    else:
        formatted = input_text[:14]  # Limita ao máximo de 14 caracteres (CNPJ)

    # Atualiza o campo de entrada
    entry_filtro_documento.delete(0, tk.END)
    entry_filtro_documento.insert(0, formatted)
    # Move o cursor para o final
    entry_filtro_documento.icursor(tk.END)

def tela_listar():
    limpar_tela()
    
    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)

    if not clientes:
        messagebox.showinfo("Lista de Clientes", "Nenhum cliente cadastrado.")
        return
    
    # Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(main_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    frame_listar = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame_listar, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_listar.bind("<Configure>", configure_scroll_region)

    # Título
    label_titulo = tk.Label(frame_listar, text="Lista de clientes", font=('Arial', 18, 'bold'), bg="dimgray")
    label_titulo.pack(pady=10)

    # Frame para conter a tabela e a scrollbar
    frame_tree = tk.Frame(frame_listar, bg="dimgray")
    frame_tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # Cria a barra de rolagem vertical para o Treeview
    scrollbar_tree = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL)
    scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)

    # Cria o Treeview com o campo celular 2
    global tree
    tree = ttk.Treeview(frame_tree, columns=("Documento", "Nome", "Celular", "Celular 2"), show='headings', yscrollcommand=scrollbar_tree.set)
    tree.heading("Documento", text="CPF/CNPJ")
    tree.heading("Nome", text="Nome")
    tree.heading("Celular", text="Celular")
    tree.heading("Celular 2", text="Celular 2")  # Novo cabeçalho
    tree.column("Documento", width=150)
    tree.column("Nome", width=300)
    tree.column("Celular", width=200)
    tree.column("Celular 2", width=200)  # Largura da nova coluna
    tree.pack(expand=True, fill=tk.BOTH)

    # Vincula a scrollbar ao Treeview
    scrollbar_tree.config(command=tree.yview)

    # Frame para os filtros
    frame_filtros = tk.Frame(frame_listar, bg="dimgray")
    frame_filtros.pack(pady=5)

    # Filtro por Documento
    label_filtro_documento = tk.Label(frame_filtros, text="Filtrar por CPF/CNPJ:", bg="dimgray")
    label_filtro_documento.grid(row=0, column=0, padx=5)
    global entry_filtro_documento
    entry_filtro_documento = tk.Entry(frame_filtros)
    entry_filtro_documento.grid(row=0, column=1, padx=5)

    # Bind para formatação automática
    entry_filtro_documento.bind("<KeyRelease>", formatar_input_documento)

    # Filtro por Celular
    label_filtro_celular = tk.Label(frame_filtros, text="Filtrar por Celular:", bg="dimgray")
    label_filtro_celular.grid(row=1, column=0, padx=5)
    global entry_filtro_celular
    entry_filtro_celular = tk.Entry(frame_filtros)
    entry_filtro_celular.grid(row=1, column=1, padx=5)

    # Filtro por Celular 2
    label_filtro_celular2 = tk.Label(frame_filtros, text="Filtrar por Celular 2:", bg="dimgray")
    label_filtro_celular2.grid(row=2, column=0, padx=5)
    global entry_filtro_celular2
    entry_filtro_celular2 = tk.Entry(frame_filtros)
    entry_filtro_celular2.grid(row=2, column=1, padx=5)

    # Filtro por Nome
    label_filtro_nome = tk.Label(frame_filtros, text="Filtrar por Nome:", bg="dimgray")
    label_filtro_nome.grid(row=3, column=0, padx=5)
    global entry_filtro_nome
    entry_filtro_nome = tk.Entry(frame_filtros)
    entry_filtro_nome.grid(row=3, column=1, padx=5)

    frame_botoes = tk.Frame(frame_filtros, bg="dimgray")
    frame_botoes.grid(row=4, columnspan=2, pady=5)

    # Botão de Filtrar
    button_filtrar = tk.Button(frame_botoes, text="Filtrar", command=aplicar_filtro_cliente, bg='lightgreen', fg='black')
    button_filtrar.pack(side=tk.RIGHT, padx=5)

    # Botão de Editar
    button_editar = tk.Button(frame_botoes, text="Editar", command=editar_cliente_selecionado, bg='lightgreen', fg='black')
    button_editar.pack(side=tk.RIGHT, padx=5)

    # Botão de Retornar
    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_principal, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    # Carrega os clientes na tabela sem filtro inicialmente
    carregar_clientes_na_tabela()
    
    # Centralizando o frame_listar no canvas
    frame_listar.update_idletasks()  # Atualiza o tamanho do frame
    width = max(canvas.winfo_width(), frame_listar.winfo_width())
    canvas.create_window((width // 2, 0), window=frame_listar, anchor="n")  # Ajusta a posição do frame_listar
    
def formatar_documento(documento):
    """
    Formata o CPF ou CNPJ para exibição.
    """
    if len(documento) == 11:  # CPF
        return f"{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}"
    elif len(documento) == 14:  # CNPJ
        return f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}"
    return documento  # Retorna o documento sem formatação se não for CPF nem CNPJ
    
def carregar_clientes_na_tabela(filtro_cpf="", filtro_nome="", filtro_celular="", filtro_celular2=""):
    """
    Carrega os clientes na tabela com base nos filtros de CPF/CNPJ, Nome, Celular e Celular 2.
    Se nenhum filtro for fornecido, todos os clientes são carregados.
    """
    # Limpa a tabela antes de inserir os clientes
    tree.delete(*tree.get_children())

    # Itera sobre os clientes e aplica os filtros
    for documento, (nome, celular, celular2) in clientes.items():  # Atualizado para incluir celular2
        documento = str(documento)  # Assegure-se de que o documento é uma string

        # Formata CPF/CNPJ para a visualização (adiciona pontos e traços)
        documento_formatado = formatar_documento(documento)

        # Verifica se o documento formatado atende ao filtro
        if (filtro_cpf and filtro_cpf not in documento_formatado) or \
           (filtro_nome and filtro_nome.lower() not in nome.lower()) or \
           (filtro_celular and filtro_celular not in celular) or \
           (filtro_celular2 and filtro_celular2 not in celular2):  # Novo filtro para celular2
            continue
        
        # Insere o cliente que atende aos filtros
        tree.insert("", tk.END, values=(documento_formatado, nome, celular, celular2))  # Inclui celular2
        
        
def aplicar_filtro_cliente():
    """
    Função que aplica os filtros de CPF/CNPJ, Nome, Celular e Celular 2 aos clientes.
    """
    global entry_filtro_documento, entry_filtro_celular, entry_filtro_nome, entry_filtro_celular2  # Certifique-se de que as variáveis estão acessíveis

    filtro_documento = entry_filtro_documento.get().strip()
    filtro_celular = entry_filtro_celular.get().strip()
    filtro_celular2 = entry_filtro_celular2.get().strip()  # Novo filtro para celular 2
    filtro_nome = entry_filtro_nome.get().strip()

    # Chama a função para carregar a tabela, agora com filtros
    carregar_clientes_na_tabela(filtro_documento, filtro_nome, filtro_celular, filtro_celular2)


def aplicar_filtro_cpf_celular(filtro):
    carregar_clientes_na_tabela(filtro)

def carregar_clientes_por_nome(filtro=None):
    for item in tree.get_children():
        tree.delete(item)
    for cpf, (nome, celular) in clientes.items():
        if filtro is None or filtro.lower() in nome.lower():
            tree.insert("", tk.END, values=(cpf, nome, celular))

def aplicar_filtro_nome(filtro):
    carregar_clientes_por_nome(filtro)

def editar_cliente_selecionado():
    # Obtém o item selecionado
    selecionado = tree.selection()
    
    if not selecionado:
        messagebox.showwarning("Aviso", "Selecione um cliente para editar.")
        return
    
    # Obtém os dados do cliente selecionado
    item = tree.item(selecionado)
    cpf, nome, celular, celular2 = item['values']  # Incluindo celular 2

    # Certifique-se de que o CPF é uma string
    cpf = str(cpf)  # Forçando CPF a ser string

    # Chama a tela de edição e preenche os campos
    tela_editar_cliente(cpf, nome, celular, celular2)  # Passando celular 2

def tela_editar_cliente(cpf, nome, celular, celular2):
    limpar_tela()
    
    if usuario_logado:
        mensagem_bem_vindo = f"Usuario: {usuario_logado}!"
    else:
        mensagem_bem_vindo = "Usuario: visitante!"

    # Frame da barra superior preta
    barra_superior = tk.Frame(app, bg="black", height=40)
    barra_superior.pack(fill=tk.X, side=tk.TOP)

    frame_logo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_logo.pack(side=tk.LEFT, padx=10)
    
    try:
        logo_image = Image.open("./Imagens/logo.png")
        logo_image = logo_image.resize((350, 50), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_image)
        label_logo = tk.Label(frame_logo, image=logo, bg="#000000")
        label_logo.image = logo
        label_logo.pack(side=tk.LEFT, padx=5, pady=5)
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")
        messagebox.showerror("Erro", "Não foi possível carregar a imagem da logo.")

    # Frame para os botões (Tela Cheia e Log) à esquerda da logo
    frame_botoes_superior = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_botoes_superior.pack(side=tk.LEFT, padx=10, anchor='center')

    # Botão de tela cheia
    frame_botao_fullscreen = ctk.CTkFrame(frame_botoes_superior, fg_color="#000000")
    frame_botao_fullscreen.pack(side=tk.LEFT, padx=5)

    fullscreen_button = ctk.CTkButton(frame_botao_fullscreen, text="Tela Cheia/Janela", command=toggle_fullscreen, fg_color="#4CAF50", text_color="white", width=150, height=40, font=("Arial", 12, "bold"))
    fullscreen_button.pack(padx=5, pady=5)
    
    # Frame para a mensagem de boas-vindas e o botão de deslogar à direita
    frame_bem_vindo = ctk.CTkFrame(barra_superior, fg_color="#000000")
    frame_bem_vindo.pack(side=tk.RIGHT, padx=10)

    # Mensagem de boas-vindas
    label_bem_vindo = ctk.CTkLabel(frame_bem_vindo, text=mensagem_bem_vindo, font=("Helvetica", 18), fg_color="transparent", text_color="white")
    label_bem_vindo.pack(side=tk.LEFT)

    # Botão Deslogar à direita da mensagem de boas-vindas
    button_deslogar = ctk.CTkButton(frame_bem_vindo, text="Deslogar", command=deslogar, fg_color="#FF5722", hover_color="#E64A19", width=120, height=40,font=("Arial", 12, "bold"))
    button_deslogar.pack(side=tk.LEFT, padx=10)
    
    # Cria um Frame principal com scrollbar
    main_frame = tk.Frame(app, bg="dimgray")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Adicionando a barra de rolagem
    scrollbar = ttk.Scrollbar(main_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Canvas para rolagem
    canvas = tk.Canvas(main_frame, bg="dimgray", yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configurando a barra de rolagem
    scrollbar.config(command=canvas.yview)

    # Frame que irá conter os widgets
    frame = tk.Frame(canvas, bg="dimgray")
    canvas.create_window((0, 0), window=frame, anchor="nw")

    # Função para atualizar a área de rolagem
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame.bind("<Configure>", configure_scroll_region)

    global entry_cpf, entry_nome, entry_celular, entry_celular2, cpf_antigo, celular_antigo
    cpf_antigo = cpf  # Define o CPF antigo
    celular_antigo = celular  # Define o celular antigo

    # Adiciona o título na parte superior
    titulo = tk.Label(frame, text="Editar Cliente", font=('Arial', 18, 'bold'), bg="dimgray", fg="black")
    titulo.pack(pady=10)

    # Adiciona os elementos ao frame
    label_cpf = tk.Label(frame, text="CPF: (Obrigatório)", bg="dimgray")
    label_cpf.pack(pady=5)

    entry_cpf = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_cpf.pack(pady=5)

    # Preenche o campo com o CPF e torna-o "readonly"
    entry_cpf.insert(0, cpf)  # Exibe o CPF diretamente
    entry_cpf.config(state='readonly')

    label_nome = tk.Label(frame, text="Nome Completo: (Obrigatório)", bg="dimgray")
    label_nome.pack(pady=5)

    entry_nome = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_nome.pack(pady=5)
    entry_nome.insert(0, nome)  # Preenche o campo com o Nome

    label_celular = tk.Label(frame, text="Celular: (Obrigatório)", bg="dimgray")
    label_celular.pack(pady=5)

    entry_celular = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_celular.pack(pady=5)
    entry_celular.insert(0, celular)  # Preenche o campo com o Celular

    # Novo campo para celular 2
    label_celular2 = tk.Label(frame, text="Celular 2: (Opcional)", bg="dimgray")
    label_celular2.pack(pady=5)

    entry_celular2 = tk.Entry(frame, font=('Arial', 14), width=30)
    entry_celular2.pack(pady=5)
    entry_celular2.insert(0, celular2)  # Preenche o campo com o Celular 2

    # Frame para os botões "Atualizar Cliente" e "Retornar"
    frame_botoes = tk.Frame(frame, bg="dimgray")
    frame_botoes.pack(pady=20)

    button_retornar = tk.Button(frame_botoes, text="Retornar", command=tela_listar, bg='lightcoral', fg='black')
    button_retornar.pack(side=tk.LEFT, padx=5)

    button_atualizar = tk.Button(frame_botoes, text="Atualizar Cliente", command=atualizar_cliente, bg='lightgreen', fg='black')
    button_atualizar.pack(side=tk.LEFT, padx=5)

    # Centralizando o frame no canvas
    frame.update_idletasks()  # Atualiza o tamanho do frame
    canvas.create_window((canvas.winfo_width() // 2, 0), window=frame, anchor="n")  # Ajusta a posição do frame
    
def atualizar_cliente():
    global cpf_antigo, celular_antigo  # Certifique-se de que as variáveis globais estão declaradas

    nome = entry_nome.get()
    celular_novo = entry_celular.get() or "Sem celular"  # Use "Sem celular" se estiver vazio
    celular2_novo = entry_celular2.get() or "Sem celular"  # Use "Sem celular" se estiver vazio
    cpf = cpf_antigo  # Mantém o CPF/CNPJ original

    # Verifica se os campos obrigatórios (nome e CPF/CNPJ) estão preenchidos
    if not nome or not cpf:
        messagebox.showwarning("Aviso", "Os campos Nome Completo e CPF/CNPJ são obrigatórios.")
        return

    # Remove formatação para validação
    cpf_sem_formatacao = cpf.replace('.', '').replace('-', '').replace('/', '')

    # Validação do CPF/CNPJ
    if len(cpf_sem_formatacao) == 14:  # CNPJ
        if not validar_cnpj(cpf_sem_formatacao):
            messagebox.showwarning("Aviso", "CNPJ inválido.")
            return
    elif len(cpf_sem_formatacao) == 11:  # CPF
        if not validar_cpf(cpf_sem_formatacao):
            messagebox.showwarning("Aviso", "CPF inválido.")
            return

    # Verifica se o CPF/CNPJ já existe em outro cliente
    if any(cpf_sem_formatacao == cliente[1].replace('.', '').replace('-', '').replace('/', '') and celular_antigo != celular_novo for celular, cliente in clientes.items()):
        messagebox.showwarning("Aviso", "Esse CPF/CNPJ já está cadastrado.")
        return

    # Se o celular antigo foi alterado, remove o antigo
    if celular_antigo and celular_antigo != celular_novo:
        if celular_antigo in clientes:
            del clientes[celular_antigo]

    # Atualiza o cliente no dicionário
    clientes[cpf_sem_formatacao] = (nome, celular_novo, celular2_novo)  # Salva CPF/CNPJ sem formatação
    salvar_clientes()  # Verifique se a função salvar_clientes() está correta e funcionando
    messagebox.showinfo("Sucesso", f"Cliente {nome} atualizado com sucesso.")

    # Limpa os campos após atualização
    entry_nome.delete(0, tk.END)
    entry_celular.delete(0, tk.END)
    entry_celular2.delete(0, tk.END)  # Limpa o campo celular 2
    
    registrar_acao(usuario_logado, f"Edição de cliente. Nome: {nome}, CPF/CNPJ: {cpf_sem_formatacao}")

    # Retorna à lista de clientes
    tela_listar()

app = tk.Tk()
app.title("Sistema Eletro Espíndola")
app.configure(bg="dimgray")
fullscreen = False

# Definindo uma resolução automática baseada na resolução da tela
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Define a largura e altura da janela (exemplo: 80% da tela)
window_width = int(screen_width * 0.8)
window_height = int(screen_height * 0.8)

# Define a posição central da janela
x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 2) - (window_height // 2)

# Configurando a geometria da janela
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Frame principal
main_frame = tk.Frame(app, bg="dimgray")
main_frame.pack(fill=tk.BOTH, expand=True)

# Frame que irá conter os widgets
content_frame = tk.Frame(main_frame, bg="dimgray")
content_frame.pack(fill=tk.BOTH, expand=True)

# Adicione seus widgets ao content_frame aqui
for i in range(50):  # Adicionando muitos widgets para testar a interface
    tk.Label(content_frame, text=f"Label {i + 1}", bg="dimgray", fg="white").pack(pady=5)
    
# Carregar clientes
carregar_clientes()

# Lista de serviços
servicos = []

# Carregar serviços na inicialização
carregar_servicos()

# Chama a função para exibir a tela de login ao iniciar o aplicativo
tela_login()

# Eventos para sair do modo fullscreen pressionando Esc
app.bind("<Escape>", end_fullscreen)

# Iniciar o loop da aplicação
app.mainloop()