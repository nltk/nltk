"""
Real-server (not mocked) regression test for the CoreNLPServer.start()
startup race condition (https://github.com/nltk/nltk/issues/3429).

Unlike test_corenlp_server_start.py, this drives an actual Stanford CoreNLP
Java process. It's skipped by default -- opt in by pointing
NLTK_CORENLP_TEST_JAR_DIR at a real CoreNLP install
(https://stanfordnlp.github.io/CoreNLP/download.html, tested against 4.5.10):

    export NLTK_CORENLP_TEST_JAR_DIR=/path/to/stanford-corenlp-4.5.10
    python -m pytest nltk/test/unit/test_corenlp_server_start_real.py -v -s

The test reproduces the exact race from #3429: something else grabs the
server's port between nltk's own up-front check (CoreNLPServer.__init__'s
try_port()) and the JVM finishing its (comparatively slow) startup and
attempting its own bind. It does this deterministically with a background
thread that exclusively binds the port shortly after construction, rather
than relying on timing a second real process -- the effect on start() is
the same either way: the JVM's own bind fails and it exits.

Profiling data (this exact test, run against a real stanford-corenlp-4.5.10
install, same machine, same port-stealing delay -- only the git commit of
nltk itself differs between the two runs):

    pre-fix  (git worktree at 6dd6c7d~1, single poll() check before the
              retry loop): FAILED -- raised after 30.1s: "Could not connect
              to the server." The single up-front poll() check runs before
              the port-stealing thread even starts, so it always sees the
              process still alive; the exit ~1s later is never re-checked,
              and the real cause is discarded -- the loop just exhausts its
              full 30-iteration/1s-sleep budget and reports the generic
              connection-failure message instead.
    post-fix (this tree, poll() re-checked every iteration of the retry
              loop): PASSED -- raised after 3.0s: CoreNLPServerError:
              "Could not start the server. The error was: (stderr not
              captured; pass stderr='pipe' to start() to see it)"
              (the "stderr not captured" text is itself the second fix in
              this PR -- see test_late_exit_with_uncaptured_stderr_gives_a_
              readable_message for why the default stderr="devnull" needs
              that guard)
"""

import os
import socket
import threading
import time
import unittest

REQUIRED_ENV_VAR = "NLTK_CORENLP_TEST_JAR_DIR"
PORT = 9091  # unlikely to collide with a real dev CoreNLP instance on 9000


@unittest.skipUnless(
    os.environ.get(REQUIRED_ENV_VAR),
    f"set {REQUIRED_ENV_VAR} to a real CoreNLP install directory to run this "
    "test against an actual Stanford CoreNLP server",
)
class TestCoreNLPServerStartRaceReal(unittest.TestCase):
    def setUp(self):
        os.environ["CORENLP"] = os.environ[REQUIRED_ENV_VAR]
        os.environ["CORENLP_MODELS"] = os.environ[REQUIRED_ENV_VAR]

    def _occupy_port_after_delay(self, delay_s: float, hold_s: float) -> None:
        """Grab PORT exclusively (no SO_REUSEADDR) after `delay_s`, holding
        it for `hold_s` -- simulates something else stealing the port after
        nltk's own construction-time check already found it free."""
        time.sleep(delay_s)
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("localhost", PORT))
        blocker.listen(5)
        blocker.settimeout(0.5)
        deadline = time.monotonic() + hold_s
        while time.monotonic() < deadline:
            try:
                conn, _ = blocker.accept()
                conn.close()  # accept-then-close: fast reset, no hanging clients
            except TimeoutError:
                pass
        blocker.close()

    def test_port_stolen_after_construction_is_detected_quickly(self):
        from nltk.parse.corenlp import CoreNLPServer, CoreNLPServerError

        server = CoreNLPServer(port=PORT)  # port is free; passes try_port()

        grabber = threading.Thread(
            target=self._occupy_port_after_delay, args=(1.0, 20.0), daemon=True
        )
        grabber.start()

        start = time.monotonic()
        try:
            with self.assertRaises(CoreNLPServerError) as ctx:
                server.start()
            elapsed = time.monotonic() - start
            print(f"\n[profiling] raised after {elapsed:.1f}s: {ctx.exception}")
            # The whole point of the fix: this must not take anywhere near
            # the full 30-iteration/1s-sleep budget (~30s).
            self.assertLess(elapsed, 10.0)
        finally:
            grabber.join(timeout=25.0)


if __name__ == "__main__":
    unittest.main()
