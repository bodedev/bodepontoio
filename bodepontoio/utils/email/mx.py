import dns.exception
import dns.resolver


def domain_has_mx_record(domain: str, timeout: float = 2.0) -> bool | None:
    """
    Verifica se o domínio tem registro MX.

    Retorna True/False quando o DNS responde de forma definitiva (domínio
    existe ou não existe / não recebe e-mails). Retorna None em falhas
    transitórias (timeout, sem nameservers disponíveis, etc.) para que o
    chamador decida como tratar — normalmente falhando aberto, já que isso
    é um problema de infraestrutura de DNS, não do domínio em si.
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    try:
        resolver.resolve(domain, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except dns.exception.DNSException:
        return None
    return True
