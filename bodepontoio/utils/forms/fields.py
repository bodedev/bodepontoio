import logging

from django.forms import EmailField, ValidationError

from bodepontoio.utils.email.mx import domain_has_mx_record

logger = logging.getLogger(__name__)


class ValidatingEmailField(EmailField):
    """
    Django EmailField which checks for MX records on the email domain.

    Requires dnspython to be installed.
    """

    def clean(self, value):
        email = super().clean(value)

        if '@' in email:
            domain = email.split('@')[1]

            # Make sure the domain exists. Falhas transitórias de DNS (timeout,
            # sem nameservers) não bloqueiam o usuário — só rejeitamos quando o
            # DNS responde de forma definitiva que o domínio não recebe e-mails.
            logger.debug('Checking domain %s', domain)
            if domain_has_mx_record(domain) is False:
                logger.debug('Domain %s does not exist.', domain)
                raise ValidationError("Este e-mail não é válido!")

        return email
