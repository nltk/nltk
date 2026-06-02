# Contributing to NLTK

Hi! Thanks for your interest in contributing to [NLTK](https://www.nltk.org/).
:-) You'll be joining a [long list of contributors](https://github.com/nltk/nltk/blob/develop/AUTHORS.md).
In this document, we'll try to summarize everything that you need to know to
do a good job.

## Maintenance Mode

NLTK is in maintenance mode. We welcome bugfixes.
We can consider _minor_ enhancements if they are clearly documented in an [NLTK issue](https://github.com/nltk/nltk/issues)
and are supported by a [team member](https://github.com/orgs/nltk/teams/team-nltk) who is willing to review a PR.
(You are welcome to make a case for a _major_ enhancement, but please note we have limited capacity to deal with it.
Please enlist an NLTK team member before doing substantial coding.)

## Code and Issues

We use [GitHub](https://www.github.com/) to host our code repositories and
issues. The [NLTK organization on GitHub](https://github.com/nltk) has many
repositories, so we can manage better the issues and development. The most
important are:

- [nltk/nltk](https://github.com/nltk/nltk/), the main repository with code
  related to the library;
- [nltk/nltk_data](https://github.com/nltk/nltk_data), repository with data
  related to corpora, taggers and other useful data that are not shipped by
  default with the library, which can be downloaded by `nltk.downloader`;
- [nltk/nltk.github.com](https://github.com/nltk/nltk.github.com), NLTK website
  with information about the library, documentation, link for downloading NLTK
  Book etc.;
- [nltk/nltk_book](https://github.com/nltk/nltk_book), source code for the NLTK
  Book.

## Development priorities

NLTK consists of the functionality that the Python/NLP community is motivated to contribute.
Some priority areas for development are listed in the [NLTK Wiki](https://github.com/nltk/nltk/wiki#development).

## Git and our Branching model

### Git

We use [Git](https://git-scm.com/) as our [version control
system](https://en.wikipedia.org/wiki/Revision_control), so the best way to
contribute is to learn how to use it and put your changes on a Git repository.
There's plenty of documentation about Git -- you can start with the [Pro Git
book](https://git-scm.com/book/).


### Setting up a Development Environment

To set up your local development environment for contributing to the main
repository [nltk/nltk](https://github.com/nltk/nltk/):

- Fork the [nltk/nltk](https://github.com/nltk/nltk/) repository on GitHub
  to your account;
- Clone your forked repository locally
  (`git clone https://github.com/<your-github-username>/nltk.git`);
- Run `cd nltk` to get to the root directory of the `nltk` code base;
- Create and activate a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```
- Install NLTK in editable mode with dependencies:
  ```bash
  pip install -e .
  pip install -r pip-req.txt
  ```
- Install the pre-commit hooks:
  ```bash
  pip install pre-commit
  pre-commit install
  ```
- Install the code formatters and linter used by the pre-commit hooks:
  ```bash
  pip install black isort ruff pyupgrade
  ```
- Download the datasets for running tests
  (`python -m nltk.downloader all`);
- Create a remote link from your local repository to the
  upstream `nltk/nltk` on GitHub
  (`git remote add upstream https://github.com/nltk/nltk.git`) --
  you will need to use this `upstream` link when updating your local repository
  with all the latest contributions.

### Pre-commit hooks

NLTK uses [pre-commit](https://pre-commit.com) to run code quality checks
before each commit. The hooks are configured in
[`.pre-commit-config.yaml`](https://github.com/nltk/nltk/blob/develop/.pre-commit-config.yaml)
and include:

- [pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) -- trailing whitespace, end-of-file fixer, YAML check
- [pyupgrade](https://github.com/asottile/pyupgrade) -- upgrade syntax to Python 3.10+
- [black](https://github.com/psf/black) -- code formatting
- [isort](https://github.com/pycqa/isort) -- import sorting
- [ruff](https://github.com/astral-sh/ruff-pre-commit) -- fast Python linter with auto-fix

You can run all hooks manually with:
```bash
pre-commit run --all-files
```

Or run the tools individually:
```bash
isort nltk/path/to/file.py
black nltk/path/to/file.py
ruff check nltk/path/to/file.py
```

### GitHub Pull requests

We use [gitflow](https://nvie.com/posts/a-successful-git-branching-model/) to manage our branches.

Summary of our git branching model:
- Go to the `develop` branch (`git checkout develop`);
- Get all the latest work from the upstream `nltk/nltk` repository
  (`git pull upstream develop`);
- Create a new branch off of `develop` with a descriptive name (for example:
  `feature/portuguese-sentiment-analysis`, `hotfix/bug-on-downloader`). You can
  do it by switching to the `develop` branch (`git checkout develop`) and then
  creating a new branch (`git checkout -b name-of-the-new-branch`);
- Do many small commits on that branch locally (`git add files-changed`,
  `git commit -m "Add some change"`);
- Run the tests to make sure nothing breaks
  (`pytest nltk/test` or `tox -e py313` if you are on Python 3.13);
- Add your name to the `AUTHORS.md` file as a contributor;
- Push to your fork on GitHub (with the name as your local branch:
  `git push origin branch-name`);
- Create a pull request using the GitHub Web interface (asking us to pull the
  changes from your new branch and add to them our `develop` branch);
- Wait for comments.


### Tips

- Write [helpful commit
  messages](https://robots.thoughtbot.com/5-useful-tips-for-a-better-commit-message).
- Anything in the `develop` branch should be deployable (no failing tests).
- Never use `git add .`: it can add unwanted files;
- Avoid using `git commit -a` unless you know what you're doing;
- Check every change with `git diff` before adding them to the index (stage
  area) and with `git diff --cached` before committing;
- Make sure you add your name to our [list of contributors](https://github.com/nltk/nltk/blob/develop/AUTHORS.md);
- If you have push access to the main repository, please do not commit directly
  to `develop`: your access should be used only to accept pull requests; if you
  want to make a new feature, you should use the same process as other
  developers so your code will be reviewed.
- See [RELEASE-HOWTO.txt](RELEASE-HOWTO.txt) to see everything you
  need before creating a new NLTK release.


## Code Guidelines

- Use [PEP8](https://www.python.org/dev/peps/pep-0008/);
- Write tests for your new features (please see "Tests" topic below);
- Always remember that [commented code is dead
  code](https://blog.codinghorror.com/coding-without-comments/);
- Name identifiers (variables, classes, functions, module names) with readable
  names (`x` is always wrong);
- When manipulating strings, we prefer either [f-string
  formatting](https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals)
  (f`'{a} = {b}'`) or [new-style
  formatting](https://docs.python.org/library/string.html#format-string-syntax)
  (`'{} = {}'.format(a, b)`), instead of the old-style formatting (`'%s = %s' % (a, b)`);
- All `#TODO` comments should be turned into issues (use our
  [GitHub issue system](https://github.com/nltk/nltk/issues));
- Run all tests before pushing (just execute `tox`) so you will know if your
  changes broke something;

See also our [developer's
guide](https://github.com/nltk/nltk/wiki/Developers-Guide).


## Tests

You should write tests for every feature you add or bug you solve in the code.
Having automated tests for every line of our code lets us make big changes
without worries: there will always be tests to verify if the changes introduced
bugs or lack of features. If we don't have tests we will be blind and every
change will come with some fear of possibly breaking something.

For a better design of your code, we recommend using a technique called
[test-driven development](https://en.wikipedia.org/wiki/Test-driven_development),
where you write your tests **before** writing the actual code that implements
the desired feature.

You can use `pytest` to run your tests, no matter which type of test it is:

```bash
cd nltk/test
pytest util.doctest        # doctest
pytest unit/translate/test_nist.py  # unittest
pytest                     # all tests
```

If your PR only touches a single module, you can run just the relevant test
file directly with `python -m unittest` without needing pytest:

```bash
# Run a specific test file
python -m unittest nltk.test.unit.test_tokenize

# Run a specific test class
python -m unittest nltk.test.unit.test_tokenize.TestTreebankWordDetokenizer

# Run a specific test method
python -m unittest nltk.test.unit.test_tokenize.TestTreebankWordDetokenizer.test_contractions
```

If your PR touches a module that has doctests (inline `>>>` examples in
docstrings), you can run just those doctests with `python -m doctest`:

```bash
# Run doctests for a single module
python -m doctest nltk/metrics/distance.py

# Run with verbose output to see each test
python -m doctest -v nltk/metrics/distance.py

# Run a specific doctest file from the test suite
python -m doctest nltk/test/tokenize.doctest
```

These are faster than running the full test suite and useful for quick
iteration during development.


## Continuous Integration

NLTK uses [GitHub Actions](https://github.com/nltk/nltk/actions) for continuous integration.
See [here](https://docs.github.com/en/actions) for GitHub's documentation.

The [`.github/workflows/ci.yml`](https://github.com/nltk/nltk/blob/develop/.github/workflows/ci.yml) file configures the CI:

 - `on:` section
   - ensures that this CI is run on code pushes, pull request, or through the GitHub website via `workflow_dispatch`.

 - The `pre-commit` job
   - performs these steps:
     - Downloads the `nltk` source code.
     - Runs pre-commit on all files in the repository (black, isort, ruff, pyupgrade).
     - Fails if any hooks performed a change.

 - The `minimal_download_test` job
   - verifies that `nltk.download()` works on all platforms (ubuntu, macos, windows).

 - The `test` job
   - tests against supported Python versions (`3.10`, `3.11`, `3.12`, `3.13`, `3.14`).
   - tests on `ubuntu-latest`, `macos-latest`, and `windows-latest`.
   - performs these steps:
     - Downloads the `nltk` source code.
     - Sets up Python using whatever version is being checked in the current execution.
     - Installs dependencies via `pip install -r pip-req.txt`.
     - Downloads `nltk_data`.
     - Runs `pytest --numprocesses auto -rsx --doctest-modules nltk`.

#### To run tests locally

Using pytest directly:

```bash
# Run all tests
pytest nltk/test

# Run a specific test file
pytest nltk/test/unit/test_tokenize.py

# Run tests in parallel
pip install pytest-xdist
pytest --numprocesses auto nltk/test
```

Using tox (to test against a specific Python version):

```bash
pip install tox
tox -e py313  # for Python 3.13
```


## Supported Python Versions

NLTK supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.
See `python_requires` in [setup.py](https://github.com/nltk/nltk/blob/develop/setup.py).


# Discussion

We have three mail lists on Google Groups:

- [nltk][nltk-announce], for announcements only;
- [nltk-users][nltk-users], for general discussion and user questions;
- [nltk-dev][nltk-dev], for people interested in NLTK development.

Please feel free to contact us through the [nltk-dev][nltk-dev] mail list if
you have any questions or suggestions. Every contribution is very welcome!

Happy hacking! (;

[nltk-announce]: https://groups.google.com/forum/#!forum/nltk
[nltk-dev]: https://groups.google.com/forum/#!forum/nltk-dev
[nltk-users]: https://groups.google.com/forum/#!forum/nltk-users
