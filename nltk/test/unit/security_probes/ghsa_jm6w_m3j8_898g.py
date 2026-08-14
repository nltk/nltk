"""GHSA-jm6w-m3j8-898g [high] -- Unauthenticated remote shutdown in nltk.app.wordnet_app"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-jm6w-m3j8-898g")
def _wordnet_app_shutdown():
    """Unauthenticated remote shutdown in nltk.app.wordnet_app."""
    source = read_source("nltk.app.wordnet_app")
    if '"127.0.0.1"' not in source and "'127.0.0.1'" not in source:
        return VULNERABLE, "server does not bind to loopback"
    return STATIC, "HTTPServer binds 127.0.0.1 only"
