"""GHSA-jm6w-m3j8-898g [high] -- Unauthenticated remote shutdown in nltk.app.wordnet_app"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-jm6w-m3j8-898g")
def _wordnet_app_shutdown():
    """wnb() must bind the browser server to loopback, not a network interface.

    A spy stands in for HTTPServer so no socket is opened and serve_forever does
    not block; the captured bind address must be loopback, so the (token-gated)
    shutdown endpoint is unreachable from the network.
    """
    import nltk.app.wordnet_app as wa

    captured = {}

    class _SpyServer:
        def __init__(self, address, handler):
            captured["address"] = address

        def serve_forever(self):
            pass

    original = wa.HTTPServer
    wa.HTTPServer = _SpyServer
    try:
        wa.wnb(port=0, runBrowser=False)
    finally:
        wa.HTTPServer = original

    host = captured.get("address", (None,))[0]
    if host in ("127.0.0.1", "localhost", "::1"):
        return FIXED, "browser server binds loopback (%s)" % host
    return VULNERABLE, "browser server binds non-loopback host: %r" % host
