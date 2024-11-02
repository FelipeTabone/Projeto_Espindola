def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == "00000000000":
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10) % 11
    if digito1 == 10 or digito1 == 11:
        digito1 = 0
    if int(cpf[9]) != digito1:
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10) % 11
    if digito2 == 10 or digito2 == 11:
        digito2 = 0
    if int(cpf[10]) != digito2:
        return False

    return True

def validar_cnpj(cnpj):
    cnpj = ''.join(filter(str.isdigit, cnpj))  # Remove caracteres não numéricos
    if len(cnpj) != 14 or cnpj == "00000000000000":
        return False

    # Cálculo do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 0 if soma1 % 11 < 2 else 11 - (soma1 % 11)

    if int(cnpj[12]) != digito1:
        return False

    # Cálculo do segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 0 if soma2 % 11 < 2 else 11 - (soma2 % 11)

    if int(cnpj[13]) != digito2:
        return False

    return True