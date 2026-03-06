import re


def obfuscate_email(email: str, local_keep: int = 2, domain_keep: int = 1, mask_char: str = '*') -> str:
    """
    Ofusca um email.
    Ex: ironworld@gmail.com -> ir*******@g****.com

    local_keep: quantos caracteres manter no início do local-part
    domain_keep: quantos caracteres manter no início do nome do domínio (antes do primeiro '.')
    """
    # validação simples
    match = re.match(r'^([^@]+)@([^@]+)$', email)
    if not match:
        return email  # se não for um email simples, retorna sem alterar

    local, domain = match.groups()

    # separa nome do domínio do(s) sufixo(s) (.com, .co.uk, etc.)
    if '.' in domain:
        name, rest = domain.split('.', 1)  # rest é tudo depois do primeiro ponto
        rest = '.' + rest
    else:
        name, rest = domain, ''

    # cria máscara para local
    if len(local) <= local_keep:
        masked_local = local
    else:
        masked_local = local[:local_keep] + mask_char * (len(local) - local_keep)

    # cria máscara para nome do domínio
    if len(name) <= domain_keep:
        masked_name = name
    else:
        masked_name = name[:domain_keep] + mask_char * (len(name) - domain_keep)

    return f"{masked_local}@{masked_name}{rest}"
