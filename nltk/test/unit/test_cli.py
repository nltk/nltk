"""
Unit tests for nltk.cli — the `nltk` command-line entry point.

Regression test for https://github.com/nltk/nltk/issues/3342:
``-l`` was declared as the short option name for both ``--language``
and ``--preserve-line`` on the ``nltk tokenize`` command, which made
click emit a ``"The parameter -l is used more than once"`` UserWarning
and produced an inconsistent help message. The fix renames the short
flag for ``--preserve-line`` to ``-p``.
"""

import warnings

from click.testing import CliRunner

from nltk.cli import cli


def _invoke_help():
    runner = CliRunner()
    return runner.invoke(cli, ["tokenize", "--help"])


def test_tokenize_help_has_no_duplicate_short_options():
    """Each short option in `nltk tokenize --help` must be declared once.

    Regression for #3342: `-l` was used both for `--language` and for
    `--preserve-line`. We assert that every `-x,` short flag appearing in
    the help output is unique.
    """
    # Promote the click UserWarning that flags duplicate short options
    # into a hard failure for this test, so a future regression
    # (re-introducing the same short flag for two options) is caught here
    # rather than silently shipped.
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        result = _invoke_help()

    assert result.exit_code == 0, result.output

    # Extract every `-x,` short-option marker from the help text. Click
    # always renders short options before long ones in the form `-x, --long`.
    import re

    short_opts = re.findall(r"\s(-[a-zA-Z]),\s+--", result.output)
    duplicates = {opt for opt in short_opts if short_opts.count(opt) > 1}
    assert not duplicates, (
        f"duplicated short options in `nltk tokenize --help`: {duplicates}\n"
        f"full help output:\n{result.output}"
    )


def test_tokenize_preserve_line_short_flag_is_p():
    """`--preserve-line` is documented under its renamed short flag `-p`.

    Pinning the new short flag prevents an accidental rename back to `-l`.
    """
    result = _invoke_help()
    assert result.exit_code == 0, result.output
    assert "-p, --preserve-line" in result.output, result.output
