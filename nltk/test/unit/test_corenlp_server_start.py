"""
Regression tests for the CoreNLPServer.start() startup race condition
(https://github.com/nltk/nltk/issues/3429).

CoreNLP can take a long time (up to tens of seconds) to preload its
annotators before it binds its port, so a premature exit of the server
process may only happen well after it is launched. These tests mock out
the Java subprocess and HTTP calls so they run without a real CoreNLP jar.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from nltk.parse import corenlp


def _make_server() -> corenlp.CoreNLPServer:
    # Bypass __init__ (which looks for a CoreNLP jar on disk) since start()
    # only relies on these attributes.
    server = corenlp.CoreNLPServer.__new__(corenlp.CoreNLPServer)
    server.corenlp_options = []
    server.java_options = ["-mx2g"]
    server.verbose = False
    server._classpath = ("fake.jar", "fake-models.jar")
    server.url = "http://localhost:9000"
    return server


class TestCoreNLPServerStartRace(unittest.TestCase):
    def test_late_exit_is_detected_without_exhausting_the_retry_budget(self):
        """A process that exits a few seconds in should be caught quickly,
        not only after the full "live" polling budget is exhausted."""
        server = _make_server()

        fake_popen = MagicMock()
        fake_popen.poll.side_effect = [None, None, None, 1]
        fake_popen.communicate.return_value = (None, b"port already in use")

        with patch("nltk.parse.corenlp.java", return_value=fake_popen), patch(
            "nltk.parse.corenlp.config_java"
        ), patch(
            "requests.get", side_effect=requests.exceptions.ConnectionError
        ) as mock_get, patch(
            "nltk.parse.corenlp.time.sleep"
        ) as mock_sleep:
            with self.assertRaises(corenlp.CoreNLPServerError) as ctx:
                server.start()

        self.assertIn("port already in use", str(ctx.exception))
        # Caught on the 4th iteration: far fewer than the 30-iteration budget.
        self.assertEqual(fake_popen.poll.call_count, 4)
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)

    def test_successful_start_still_breaks_out_of_the_loop(self):
        """Sanity check that the happy path (process stays alive, server
        responds) is unaffected by moving the poll() check into the loop."""
        server = _make_server()

        fake_popen = MagicMock()
        fake_popen.poll.return_value = None

        ok_response = MagicMock(ok=True)

        with patch("nltk.parse.corenlp.java", return_value=fake_popen), patch(
            "nltk.parse.corenlp.config_java"
        ), patch("requests.get", return_value=ok_response), patch(
            "nltk.parse.corenlp.time.sleep"
        ):
            server.start()

        self.assertIs(server.popen, fake_popen)


if __name__ == "__main__":
    unittest.main()
