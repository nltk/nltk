import base64
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlsplit

import pytest

from nltk import pathsec
from nltk.util import everygrams, set_proxy, transitive_closure


@pytest.fixture
def everygram_input():
    """Form test data for tests."""
    return iter(["a", "b", "c"])


def test_everygrams_without_padding(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input))
    assert output == expected_output


def test_everygrams_max_len(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input, max_len=2))
    assert output == expected_output


def test_everygrams_min_len(everygram_input):
    expected_output = [
        ("a", "b"),
        ("a", "b", "c"),
        ("b", "c"),
    ]
    output = list(everygrams(everygram_input, min_len=2))
    assert output == expected_output


def test_everygrams_pad_right(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("b", "c", None),
        ("c",),
        ("c", None),
        ("c", None, None),
        (None,),
        (None, None),
        (None,),
    ]
    output = list(everygrams(everygram_input, max_len=3, pad_right=True))
    assert output == expected_output


def test_everygrams_pad_left(everygram_input):
    expected_output = [
        (None,),
        (None, None),
        (None, None, "a"),
        (None,),
        (None, "a"),
        (None, "a", "b"),
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input, max_len=3, pad_left=True))
    assert output == expected_output


def test_transitive_closure_chain():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    expected = {"a": {"b", "c"}, "b": {"c"}, "c": set()}
    assert transitive_closure(graph) == expected


def test_transitive_closure_reflexive():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    expected = {"a": {"a", "b", "c"}, "b": {"b", "c"}, "c": {"c"}}
    assert transitive_closure(graph, reflexive=True) == expected


def test_transitive_closure_cycle():
    graph = {"a": {"b"}, "b": {"a"}}
    expected = {"a": {"a", "b"}, "b": {"a", "b"}}
    assert transitive_closure(graph) == expected


def test_transitive_closure_empty():
    assert transitive_closure({}) == {}


def test_transitive_closure_does_not_mutate_input():
    graph = {"a": {"b"}, "b": set()}
    original_sets = {k: v for k, v in graph.items()}
    snapshot = {k: set(v) for k, v in graph.items()}

    transitive_closure(graph)

    assert graph == snapshot
    assert set(graph) == set(snapshot)
    # the same set objects, not new-but-equal ones
    assert all(graph[k] is original_sets[k] for k in snapshot)


# A Windows domain user and a password with characters that are URL delimiters.
PROXY_USER = "CORP\\alice"
PROXY_PASSWORD = "p@ss:w/rd %"
PROXY_AUTH = "Basic " + base64.b64encode(
    f"{PROXY_USER}:{PROXY_PASSWORD}".encode()
).decode("ascii")


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(handler):
    """Start an HTTP server with ``handler`` on 127.0.0.1 and return it."""
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
    return server


@pytest.fixture
def restore_opener():
    """Yield the global urllib opener, and put it back after the test."""
    original_opener = urllib.request._opener
    yield original_opener
    urllib.request.install_opener(original_opener)


@pytest.fixture
def proxy_requests(request, monkeypatch, restore_opener):
    """Run a proxy on 127.0.0.1 that wants Basic credentials, point
    ``set_proxy`` at it with PROXY_USER and PROXY_PASSWORD, and yield the
    (method, target, Proxy-Authorization) of every request it receives.

    The proxy address is "http://{}" unless a test parametrizes it, with {}
    the proxy's host:port. The proxy answers an authenticated plain HTTP
    request itself, with a redirect to the URL in its ``to`` query parameter
    if it has one, and refuses every tunnel, so no request leaves this host."""
    received = []

    class Proxy(QuietHandler):
        def do_GET(self):
            auth = self.headers.get("Proxy-Authorization")
            received.append((self.command, self.path, auth))
            redirect = parse_qs(urlsplit(self.path).query).get("to")
            if auth != PROXY_AUTH:
                self.send_response(407)
                self.send_header("Proxy-Authenticate", 'Basic realm="nltk"')
            elif self.command == "CONNECT":
                self.send_response(502)  # authenticated, but no tunnel is opened
            elif redirect:
                self.send_response(302)
                self.send_header("Location", redirect[0])
            else:
                self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_CONNECT = do_GET

    server = serve(Proxy)
    proxy = getattr(request, "param", "http://{}")
    # Neither NO_PROXY nor the system settings may route around the proxy, and
    # nltk only fetches through a proxy the operator has declared trusted.
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)
    monkeypatch.setattr(pathsec, "ALLOW_PROXIED_FETCH", True)
    try:
        set_proxy(
            proxy.format(f"127.0.0.1:{server.server_port}"),
            user=PROXY_USER,
            password=PROXY_PASSWORD,
        )
        yield received
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "proxy_requests",
    [
        "http://{}",
        "{}",
        "HTTP://{}/",
        "http://bob:old@{}",
        "http://{}/?next=http://127.0.0.1:9",
    ],
    ids=[
        "url",
        "no-scheme",
        "upper-case-scheme",
        "replaces-credentials-in-url",
        "url-in-query",
    ],
    indirect=True,
)
def test_set_proxy_authenticates_the_https_tunnel(proxy_requests):
    """nltk.download fetches over HTTPS, which a proxy carries through a
    CONNECT tunnel: the credentials given to set_proxy must be sent on that
    CONNECT request, or the proxy answers 407 Proxy Authentication Required
    (#3109). That holds for a proxy given without a scheme or with an upper-case
    one, the credentials replace any already in the proxy URL, and they go to
    the proxy's own host, not to an address later in the URL. The target is a
    public address literal, as in the SSRF tests, so no name is resolved; only
    the local proxy is contacted."""
    with pytest.raises(OSError, match="Tunnel connection failed: 502"):
        pathsec.urlopen("https://93.184.216.34/index.xml", timeout=5)
    assert proxy_requests == [("CONNECT", "93.184.216.34:443", PROXY_AUTH)]


def test_set_proxy_still_authenticates_plain_http(proxy_requests):
    """A plain HTTP request through the proxy carries the same credentials."""
    with pathsec.urlopen("http://93.184.216.34/index.xml", timeout=5) as response:
        assert response.status == 200
    assert proxy_requests[-1] == ("GET", "http://93.184.216.34/index.xml", PROXY_AUTH)


def test_set_proxy_keeps_credentials_off_a_redirect_that_bypasses_the_proxy(
    proxy_requests, monkeypatch
):
    """set_proxy's credentials go out as an ordinary header, which urllib
    copies onto a redirect. A redirect to a host that bypasses the proxy
    (NO_PROXY) must not take them to that host, also through a plain
    urllib.request.urlopen after set_proxy."""
    origin_requests = []

    class Origin(QuietHandler):
        def do_GET(self):
            origin_requests.append(self.headers.get("Proxy-Authorization"))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    origin = serve(Origin)
    landing = f"http://127.0.0.1:{origin.server_port}/landing"
    url = f"http://93.184.216.34/moved?to={quote(landing, safe='')}"
    # The origin, on 127.0.0.1, bypasses the proxy, as a NO_PROXY host would.
    monkeypatch.setattr(
        urllib.request, "proxy_bypass", lambda host: host.startswith("127.0.0.1")
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
    finally:
        origin.shutdown()
        origin.server_close()

    assert proxy_requests[-1] == ("GET", url, PROXY_AUTH)
    assert origin_requests == [None]


@pytest.mark.parametrize(
    "urlopen", [urllib.request.urlopen, pathsec.urlopen], ids=["urllib", "pathsec"]
)
def test_set_proxy_authenticates_a_redirect_that_stays_proxied(proxy_requests, urlopen):
    """Keeping the credentials off redirects does not lose them on a redirect
    the proxy carries: ProxyHandler sends them again, without a 407 first."""
    landing = "http://93.184.216.34/landing"
    url = f"http://93.184.216.34/moved?to={quote(landing, safe='')}"
    with urlopen(url, timeout=5) as response:
        assert response.status == 200
    assert proxy_requests == [("GET", url, PROXY_AUTH), ("GET", landing, PROXY_AUTH)]


def installed_proxies():
    """The proxies of the ProxyHandler in the installed urllib opener."""
    (handler,) = (
        handler
        for handler in urllib.request._opener.handlers
        if isinstance(handler, urllib.request.ProxyHandler)
    )
    return handler.proxies


@pytest.mark.parametrize(
    "proxy, credentials, proxy_url",
    [
        # password=None is the default empty password
        ("http://127.0.0.1:3128", ("alice", None), "http://alice:@127.0.0.1:3128"),
        # the (user, password) tuple that web/data.rst used to show
        (
            "http://127.0.0.1:3128",
            (("alice", "s3cret"),),
            "http://alice:s3cret@127.0.0.1:3128",
        ),
        # an IPv6 literal keeps its brackets and port
        ("http://[::1]:3128", ("alice", "s3cret"), "http://alice:s3cret@[::1]:3128"),
    ],
    ids=["password-none", "legacy-tuple", "ipv6-literal"],
)
def test_set_proxy_puts_the_credentials_in_the_proxy_url(
    restore_opener, proxy, credentials, proxy_url
):
    set_proxy(proxy, *credentials)
    assert installed_proxies() == {"http": proxy_url, "https": proxy_url}


@pytest.mark.parametrize(
    "user, password",
    [
        (b"alice", "s3cret"),
        ("alice", 1234),
        (("alice", "s3cret"), "other"),
        (type("Text", (str,), {})("alice"), "s3cret"),
    ],
    ids=["bytes-user", "int-password", "tuple-and-password", "str-subclass"],
)
def test_set_proxy_rejects_credentials_that_are_not_strings(
    restore_opener, user, password
):
    with pytest.raises(TypeError, match="user and password must be strings"):
        set_proxy("http://127.0.0.1:3128", user=user, password=password)
    assert urllib.request._opener is restore_opener
