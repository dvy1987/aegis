"""Force IPv4 DNS resolution.

macOS resolves Google Cloud APIs to IPv6 first, but IPv6 is unreachable on
this machine.  Python's socket.create_connection tries IPv6 and hangs (60s+
timeout), while curl silently falls back to IPv4.  Patching getaddrinfo to
prefer AF_INET makes every Google SDK call succeed in <5s.
"""


import socket

_patched = False
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def apply_ipv4_patch() -> None:
    global _patched
    if _patched:
        return
    socket.getaddrinfo = _ipv4_first_getaddrinfo
    _patched = True
