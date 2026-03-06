from re import findall


def grana(valor, prefixo=None):
    """
    Formata um valor numérico para dinheiro.

    Caso o valor seja `None` ele é convertido para 0.

    :param valor: o valor para ser formatado
    :type valor: float | int
    :param prefixo: texto para ser concatenado no início do valor formatado. pode ser usado para passar o símbolo da moeda
    :type prefixo: str
    :return: valor formatado para dinheiro com o prefixo concatenado no início
    :rtype: str
    """
    # Adicionado para evitar que os nossos campos dos modelos sejam prejudicados caso os valores sejam nulos.
    if valor is None or not valor:
        valor = 0
    if not prefixo:
        prefixo = ""
    else:
        # Separa o prefixo do valor, e.g., R$ 50,00
        prefixo = prefixo + " "
    valor_str = str(valor)
    parte_decimal = "00"
    # Verifica se é um número com parte decimal
    if '.' in valor_str:
        valor_str, parte_decimal = valor_str.split('.')
        parte_decimal = parte_decimal[:2]
    # Pega cada parte inteira do número e vai formando os milhares, e.g., 160.450.001
    inteiras_e_milhares = '.'.join([parte_inteira[::-1] for parte_inteira in findall(r'\d{3}|\d{2}|\d', valor_str[::-1])][::-1])
    sinal = "-" if float(valor) < 0 else ""  # Número positivo ou negativo
    padding_zeros = "{:0<2}".format(parte_decimal)  # Se necessário, temos o padding de zeros para a parte decimal, e.g., 45,5 -> 45,50
    inteira_e_decimal = "%s%s%s,%s" % (prefixo, sinal, inteiras_e_milhares, padding_zeros)
    return inteira_e_decimal
