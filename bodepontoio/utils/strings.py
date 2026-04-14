def trim_string(s):
    return " ".join(s.split())


def split_name(full_name: str) -> tuple[str, str]:
    """
    Divide um nome completo em (primeiro_nome, resto).

    Args:
        full_name: Nome completo a ser dividido

    Returns:
        Tupla com (primeiro_nome, resto_do_nome)

    Exemplos:
        >>> split_name("João da Silva Pedroso")
        ("João", "da Silva Pedroso")

        >>> split_name("Maria")
        ("Maria", "")

        >>> split_name("  Pedro   Santos  ")
        ("Pedro", "Santos")
    """
    parts = full_name.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""  # caso não tenha sobrenome
    return parts[0], parts[1]
