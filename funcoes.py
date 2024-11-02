from PIL import ImageFilter
import tkinter as tk

def aplicar_desfoque(imagem):
    return imagem.filter(ImageFilter.GaussianBlur(10))

def contar_linhas(caminho):
    """Contar o número de linhas em um arquivo."""
    try:
        with open(caminho, 'r') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Erro ao contar linhas do arquivo {caminho}: {e}")
        return 0  # Retorna 0 em caso de erro