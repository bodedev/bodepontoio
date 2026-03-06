from os.path import splitext

from django.utils.text import slugify


def file_name_cleaner(filename):
    nome_do_arquivo, extensao_do_arquivo = splitext(filename)
    return '%s%s' % (slugify(nome_do_arquivo), extensao_do_arquivo)


def file_extension(filename):
    _, extensao_do_arquivo = splitext(filename)
    return extensao_do_arquivo


def extract_name_and_surname(text: str):
    words = text.split()

    if len(words) >= 2:
        nome = words[0]
        sobrenome = ' '.join(words[1:])
        return nome, sobrenome
    else:
        return None, None


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
