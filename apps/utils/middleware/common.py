import re
from django.http.request import validate_host
from django.middleware import common
from django.conf import settings
from django.core.exceptions import PermissionDenied, DisallowedHost

host_validation_re = re.compile(r"^(.*?)(:\d+)?$")

def split_domain_port(host):
    """
    Return a (domain, port) tuple from a given host.

    Returned domain is lowercased. If the host is invalid, the domain will be
    empty.
    """
    host = host.lower()

    if not host_validation_re.match(host):
        return '', ''

    if host[-1] == ']':
        # It's an IPv6 address without a port.
        return host, ''
    bits = host.rsplit(':', 1)
    domain, port = bits if len(bits) == 2 else (bits[0], '')
    # Remove a trailing dot (if present) from the domain.
    domain = domain[:-1] if domain.endswith('.') else domain
    return domain, port


def get_host(self):
    """Return the HTTP host using the environment or request headers."""
    host = self._get_raw_host()

    # Allow variants of localhost if ALLOWED_HOSTS is empty and DEBUG=True.
    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ['localhost', '127.0.0.1', '[::1]']

    domain, port = split_domain_port(host)
    if domain and validate_host(domain, allowed_hosts):
        return host
    else:
        msg = "Invalid HTTP_HOST header: %r." % host
        if domain:
            msg += " You may need to add %r to ALLOWED_HOSTS." % domain
        else:
            msg += " The domain name provided is not valid according to RFC 1034/1035."
        raise DisallowedHost(msg)


class CommonMiddleware(common.CommonMiddleware):
    def process_request(self, request):
        """
        Check for denied User-Agents and rewrite the URL based on
        settings.APPEND_SLASH and settings.PREPEND_WWW
        """

        # Check for denied User-Agents
        if 'HTTP_USER_AGENT' in request.META:
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex.search(request.META['HTTP_USER_AGENT']):
                    raise PermissionDenied('Forbidden user agent')

        # Check for a redirect based on settings.PREPEND_WWW
        host = get_host(request)
        must_prepend = settings.PREPEND_WWW and host and not host.startswith('www.')
        redirect_url = ('%s://www.%s' % (request.scheme, host)) if must_prepend else ''

        # Check if a slash should be appended
        if self.should_redirect_with_slash(request):
            path = self.get_full_path_with_slash(request)
        else:
            path = request.get_full_path()

        # Return a redirect if necessary
        if redirect_url or path != request.get_full_path():
            redirect_url += path
            return self.response_redirect_class(redirect_url)
