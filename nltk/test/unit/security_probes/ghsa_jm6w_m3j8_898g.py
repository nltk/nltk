"""GHSA-jm6w-m3j8-898g [high] -- Unauthenticated remote shutdown in nltk.app.wordnet_app"""

import io

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-jm6w-m3j8-898g")
def _wordnet_app_shutdown():
    """wnb() binds loopback AND the shutdown route refuses a token-less request.

    Two aspects of the advisory are exercised in-process without opening a
    socket: a spy stands in for HTTPServer to capture the bind address, and a
    ``/SHUTDOWN THE SERVER`` request with no per-process token is driven through
    ``do_GET`` (with ``os._exit`` stubbed, so a broken guard is caught rather
    than killing the test) and must be refused with 403.
    """
    import nltk.app.wordnet_app as wa

    # 1) the browser server must bind loopback only
    captured = {}

    class _SpyServer:
        def __init__(self, address, handler):
            captured["address"] = address

        def serve_forever(self):
            pass

    original_server = wa.HTTPServer
    wa.HTTPServer = _SpyServer
    try:
        wa.wnb(port=0, runBrowser=False)
    finally:
        wa.HTTPServer = original_server
    host = captured.get("address", (None,))[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        return VULNERABLE, "browser server binds non-loopback host: %r" % host

    # 2) a token-less shutdown request must be refused, never reaching os._exit
    exited = []
    original_exit = wa.os._exit
    original_mode = wa.server_mode
    wa.os._exit = lambda code=0: exited.append(code)
    wa.server_mode = False  # force the per-process-token check to be the guard
    try:
        handler = wa.MyServerHandler.__new__(wa.MyServerHandler)
        handler.wfile = io.BytesIO()
        handler.path = "/SHUTDOWN THE SERVER"  # no ?token=
        codes = []
        handler.send_response = lambda code, *a, **k: codes.append(code)
        handler.send_header = lambda *a, **k: None
        handler.end_headers = lambda: None
        try:
            handler.do_GET()
        except Exception:
            # With the token guard broken, os._exit is stubbed so do_GET runs on
            # and may fall through; the os._exit call was already recorded above.
            pass
    finally:
        wa.os._exit = original_exit
        wa.server_mode = original_mode

    if exited:
        return VULNERABLE, "token-less shutdown request reached os._exit"
    if 403 in codes:
        return FIXED, f"loopback bind ({host}); token-less shutdown refused (403)"
    return STATIC, "shutdown route did not reach the token check"
