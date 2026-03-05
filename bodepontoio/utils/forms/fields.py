import logging

import dns.exception
import dns.resolver
from django.forms import EmailField, ValidationError

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

            # Make sure the domain exists
            try:
                logger.debug('Checking domain %s', domain)
                dns.resolver.query(domain, 'MX')
            except dns.exception.DNSException as e:
                logger.debug('Domain %s does not exist.', e)
                raise ValidationError("Este e-mail não é válido!")

        return email
