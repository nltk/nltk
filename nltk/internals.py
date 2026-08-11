# Natural Language Toolkit: Internal utility functions
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Nitin Madnani <nmadnani@ets.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import fnmatch
import locale
import os
import re
import stat
import subprocess
import sys
import textwrap
import types
import warnings
from xml.etree import ElementTree

from nltk.pathsec import validate_path

##########################################################################
# Java Via Command-Line
##########################################################################

_java_bin = None
_java_options = []

# Allowlist of safe JVM tuning flags for NLTK's Java wrapper.
# Anything not matching is rejected to prevent argument injection
# (CVE-2026-12841, CWE-88).  A minimal allowlist is used rather than a denylist so
# that -jar, @argfile, -XX:OnError=<cmd>, and *future* dangerous flags are blocked
# without needing to be enumerated (OWASP / SEI CERT IDS07-J both prefer this).
#
# What NLTK's wrappers (Stanford tagger/parser/tokenizer/segmenter, CoreNLP,
# MaltParser) and the Stanford CoreNLP documentation actually pass is: heap/stack
# sizing (-Xmx/-mx/-Xms/-Xss), -verbose, -server/-client, and (on JDK 9-11)
# ``--add-modules java.se.ee``. So exactly those are allowed.
#
# Deliberately NOT allowlisted, because they are unnecessary for NLTK/CoreNLP and
# proven dangerous:
#   * ``-XX:`` -- ``-XX:OnError=`` / ``-XX:OnOutOfMemoryError=`` are executed by
#     the JVM as shell commands (verified: an OOM ran the injected command), and
#     others write files or unlock restricted options.
#   * ``-D`` system properties -- e.g. ``-Djava.ext.dirs`` (RCE on JDK<=8),
#     ``-Djava.rmi.server.codebase`` / JNDI trust props. CoreNLP sets encoding via
#     its own ``-encoding`` *program* argument, not ``-Dfile.encoding``.
# An application that genuinely needs one of these passes it through the explicit
# ``trusted_raw_options`` escape hatch (see ``java()``), taking responsibility.
_SAFE_JVM_PREFIXES = (
    "-xmx",  # max heap size:   -Xmx512m
    "-mx",  # max heap (legacy alias of -Xmx, used by Stanford/CoreNLP): -mx2g
    "-xms",  # initial heap:    -Xms128m
    "-ms",  # initial heap (legacy alias of -Xms): -ms128m
    "-xss",  # thread stack:    -Xss4m
    "-ss",  # thread stack (legacy alias of -Xss): -ss4m
    "-xbatch",  # disable bg JIT
    "-xint",  # interpret-only mode
    "-xcomp",  # compile-only mode
    "-xmixed",  # mixed mode (JVM default)
    "-verbose",  # diagnostic output: -verbose:gc
)

_SAFE_JVM_EXACT = frozenset({"-server", "-client"})

# ``--add-modules <module-list>`` is required by CoreNLP on JDK 9-11 (a CoreNLP
# dependency uses the JAXB module dropped from the default set). The value is a
# comma-separated list of module names -- it names JDK modules, and because
# ``--module-path`` / ``-p`` is NOT allowlisted it cannot point at attacker code.
# Restrict the value to a plain module-list shape so nothing else rides through.
_MODULE_LIST_RE = re.compile(r"\A[A-Za-z0-9_.,-]+\Z")

# Every flag the allowlist accepts (heap/stack sizing, -verbose, -server/-client,
# --add-modules) is a single simple token; none contains whitespace or a shell
# metacharacter. Rejecting those characters is therefore a free, name-agnostic
# defense-in-depth layer (it has no false positives now that -D, whose values may
# legitimately contain them, is not accepted): e.g. a malformed ``-Xmx512m ; rm``
# token cannot ride through on the ``-xmx`` prefix.
_UNSAFE_OPTION_CHARS = frozenset(" \t\r\n;|&$`<>(){}[]*?!'\"\\")


def _validate_java_options(options):
    """
    Raise ValueError if *options* contains JVM flags that can change the
    executed program, run a command, load agents, or expand argument files.

    Uses a minimal allowlist of exactly the flags NLTK's Java wrappers and the
    Stanford CoreNLP documentation use (heap/stack sizing, -verbose,
    -server/-client, and ``--add-modules``). This is intentionally stricter than
    a denylist so that -jar, @argfile, ``-XX:OnError=<cmd>``, dangerous ``-D``
    system properties, and future dangerous flags are all rejected without
    needing to be enumerated (CVE-2026-12841, CWE-88). Applications needing an
    unlisted flag use ``java(..., trusted_raw_options=[...])``.
    """
    opts = list(options)
    i = 0
    while i < len(opts):
        flag = opts[i]

        # A JVM flag is a non-empty string; anything else cannot be reasoned
        # about safely, so reject it rather than call .lower() on it.
        if not isinstance(flag, str) or not flag:
            raise ValueError(
                f"java_options contains an invalid (non-string or empty) entry: "
                f"{flag!r} (CVE-2026-12841, CWE-88)."
            )

        # Shape guard: no legitimate allowed flag contains whitespace, a control
        # character, or a shell metacharacter; reject any that does.
        if any(
            c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F or c in _UNSAFE_OPTION_CHARS
            for c in flag
        ):
            raise ValueError(
                f"java_options contains whitespace, a control character, or a "
                f"shell metacharacter, which a valid JVM flag never does: "
                f"{flag!r} (CVE-2026-12841, CWE-88)."
            )

        n = flag.lower()

        # @argfile references are expanded by the Java launcher before
        # any other argument processing and can smuggle blocked flags.
        if n.startswith("@"):
            raise ValueError(
                f"java_options contains a disallowed Java argument file "
                f"reference: {flag!r} (CVE-2026-12841, CWE-88)."
            )

        # --add-modules <modules>  (two tokens) or  --add-modules=<modules>.
        if n == "--add-modules":
            mods = opts[i + 1] if i + 1 < len(opts) else None
            if not isinstance(mods, str) or not _MODULE_LIST_RE.match(mods):
                raise ValueError(
                    f"--add-modules must be followed by a plain module list, got "
                    f"{mods!r} (CVE-2026-12841, CWE-88)."
                )
            i += 2
            continue
        if n.startswith("--add-modules="):
            if not _MODULE_LIST_RE.match(flag.split("=", 1)[1]):
                raise ValueError(
                    f"--add-modules has a non-module-list value: {flag!r} "
                    "(CVE-2026-12841, CWE-88)."
                )
            i += 1
            continue

        if n in _SAFE_JVM_EXACT:
            i += 1
            continue

        if n.startswith(_SAFE_JVM_PREFIXES):
            i += 1
            continue

        raise ValueError(
            f"java_options contains a disallowed JVM/launcher flag: {flag!r}. "
            "Only JVM memory/stack tuning, -verbose, -server/-client and "
            "--add-modules are permitted; pass anything else through "
            "java(trusted_raw_options=...) (CVE-2026-12841, CWE-88)."
        )


# [xx] add classpath option to config_java?
def config_java(bin=None, options=None, verbose=False):
    """
    Configure nltk's java interface, by letting nltk know where it can
    find the Java binary, and what extra options (if any) should be
    passed to Java when it is run.

    :param bin: The full path to the Java binary.  If not specified,
        then nltk will search the system for a Java binary; and if
        one is not found, it will raise a ``LookupError`` exception.
    :type bin: str
    :param options: A list of options that should be passed to the
        Java binary when it is called.  A common value is
        ``'-Xmx512m'``, which tells Java binary to increase
        the maximum heap size to 512 megabytes.  If no options are
        specified, then do not modify the options list.
    :type options: list(str)
    """
    global _java_bin, _java_options
    _java_bin = find_binary(
        "java",
        bin,
        env_vars=["JAVAHOME", "JAVA_HOME"],
        verbose=verbose,
        binary_names=["java.exe"],
    )

    if options is not None:
        if isinstance(options, str):
            options = options.split()
        options = list(options)
        _validate_java_options(options)
        _java_options[:] = options


class UntrustedJarError(Exception):
    pass


def _verify_jar_sandbox(classpath_entries):
    if (
        os.environ.get("NLTK_ALLOW_UNSAFE_JARS") == "1"
        or os.environ.get("NLTK_ALLOW_UNSAFE_CLASSPATH") == "1"
    ):
        import warnings

        warnings.warn(
            "Arbitrary JAR execution is permitted via NLTK_ALLOW_UNSAFE_JARS/CLASSPATH=1",
            UserWarning,
        )
        return

    if isinstance(classpath_entries, str):
        entries = [classpath_entries]
    else:
        entries = list(classpath_entries)

    trusted_roots = []
    from nltk.data import path as data_path

    for p in data_path:
        try:
            trusted_roots.append(os.path.realpath(p))
        except Exception:
            continue

    try:
        import nltk

        nltk_package_dir = os.path.dirname(os.path.realpath(nltk.__file__))
        repo_root = os.path.realpath(os.path.join(nltk_package_dir, ".."))
        git_marker = os.path.join(repo_root, ".git")
        if os.path.isdir(git_marker) or os.path.isfile(git_marker):
            trusted_roots.append(repo_root)
    except Exception:
        pass

    for wp in (
        "/usr/share/weka",
        "/usr/local/weka",
        "/opt/weka",
        "C:\\Program Files\\Weka",
        "C:\\Program Files (x86)\\Weka",
    ):
        try:
            abs_wp = os.path.realpath(wp)
            if os.path.isdir(abs_wp):
                trusted_roots.append(abs_wp)
        except Exception:
            continue

    trusted_roots = list(dict.fromkeys(trusted_roots))

    for entry in entries:
        if not entry:
            continue
        if not os.path.isabs(entry):
            raise UntrustedJarError(f"Relative paths are strictly forbidden: {entry}")

        clean_entry = os.path.normcase(os.path.realpath(entry))
        allowed = False
        for root in trusted_roots:
            try:
                if os.path.commonpath([root, clean_entry]) == root:
                    allowed = True
                    break
            except ValueError:
                continue
        if not allowed:
            raise UntrustedJarError(
                f"Classpath entry {entry} is not in a trusted location (outside nltk_data).\n"
                f"Trusted roots: {trusted_roots}"
            )


def java(
    cmd,
    classpath=None,
    stdin=None,
    stdout=None,
    stderr=None,
    blocking=True,
    options=None,
    trusted_raw_options=None,
):
    if isinstance(cmd, str):
        raise TypeError("cmd must be a sequence of strings, not a string")
    cmd_list = list(cmd)

    def _normalise(stream):
        if stream is None:
            return None
        if stream == "pipe" or stream is True:
            return subprocess.PIPE
        if stream == "devnull":
            return subprocess.DEVNULL
        return stream

    stdin = _normalise(stdin)
    stdout = _normalise(stdout)
    stderr = _normalise(stderr)

    if options is None:
        opt_list = list(_java_options) if _java_options else []
    else:
        opt_list = options.split() if isinstance(options, str) else list(options)
        # Per-call options reach subprocess.Popen directly, so they must be
        # validated too -- config_java() alone is not enough (CVE-2026-12841,
        # CWE-88). Without this a caller-supplied -javaagent / -agentlib /
        # @argfile / -XX:OnError flag would be injected into the JVM command line.
        _validate_java_options(opt_list)
    # Escape hatch: options the caller vouches for are appended WITHOUT
    # validation. Use only for flags NLTK's allowlist rejects but you need and
    # trust (e.g. a specific ``-XX:`` GC tuning flag) -- never route untrusted
    # input here (CVE-2026-12841, CWE-88).
    if trusted_raw_options:
        if isinstance(trusted_raw_options, str):
            trusted_raw_options = trusted_raw_options.split()
        opt_list = opt_list + list(trusted_raw_options)

    classpath_arg = None
    if classpath is not None:
        if isinstance(classpath, str):
            raw_entries = [p for p in classpath.split(os.pathsep) if p]
            original_classpath_string = classpath
        else:
            raw_entries = list(classpath)
            original_classpath_string = None
        if not raw_entries:
            raise ValueError("Classpath is empty after splitting")
        _verify_jar_sandbox(raw_entries)
        if original_classpath_string is not None:
            classpath_arg = original_classpath_string
        else:
            classpath_arg = os.pathsep.join(raw_entries)

    final_cmd = []
    if isinstance(_java_bin, str):
        final_cmd.append(_java_bin)
    else:
        final_cmd.extend(_java_bin if _java_bin else ["java"])

    final_cmd.extend(opt_list)
    if classpath_arg is not None:
        final_cmd.extend(["-cp", classpath_arg])
    final_cmd.extend(cmd_list)

    try:
        p = subprocess.Popen(
            final_cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
        )
        if blocking:
            stdout_data, stderr_data = p.communicate()
            if p.returncode != 0:
                raise OSError(
                    f"Java command failed: {' '.join(final_cmd)}\n"
                    f"Return code: {p.returncode}\nOutput: {stdout_data}\nError: {stderr_data}"
                )
            return stdout_data, stderr_data
        return p
    except OSError as e:
        raise OSError(
            f"Failed to execute Java command: {' '.join(final_cmd)}\nError: {e}"
        )


######################################################################
# Parsing
######################################################################


class ReadError(ValueError):
    """
    Exception raised by read_* functions when they fail.
    :param position: The index in the input string where an error occurred.
    :param expected: What was expected when an error occurred.
    """

    def __init__(self, expected, position):
        ValueError.__init__(self, expected, position)
        self.expected = expected
        self.position = position

    def __str__(self):
        return f"Expected {self.expected} at {self.position}"


_STRING_START_RE = re.compile(r"[uU]?[rR]?(\"\"\"|\'\'\'|\"|\')")


def read_str(s, start_position):
    """
    If a Python string literal begins at the specified position in the
    given string, then return a tuple ``(val, end_position)``
    containing the value of the string literal and the position where
    it ends.  Otherwise, raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python string literal exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched string literal evaluated as a
        string and the end position of the string literal.
    :rtype: tuple(str, int)

    :raise ReadError: If the ``_STRING_START_RE`` regex doesn't return a
        match in ``s`` at ``start_position``, i.e., open quote. If the
        ``_STRING_END_RE`` regex doesn't return a match in ``s`` at the
        end of the first match, i.e., close quote.
    :raise ValueError: If an invalid string (i.e., contains an invalid
        escape sequence) is passed into the ``eval``.

    :Example:

    >>> from nltk.internals import read_str
    >>> read_str('"Hello", World!', 0)
    ('Hello', 7)

    """
    # Read the open quote, and any modifiers.
    m = _STRING_START_RE.match(s, start_position)
    if not m:
        raise ReadError("open quote", start_position)
    quotemark = m.group(1)

    # Find the close quote.
    _STRING_END_RE = re.compile(r"\\|%s" % quotemark)
    position = m.end()
    while True:
        match = _STRING_END_RE.search(s, position)
        if not match:
            raise ReadError("close quote", position)
        if match.group(0) == "\\":
            position = match.end() + 1
        else:
            break

    # Process it, using eval.  Strings with invalid escape sequences
    # might raise ValueError.
    try:
        return eval(s[start_position : match.end()]), match.end()
    except ValueError as e:
        raise ReadError("valid escape sequence", start_position) from e


_READ_INT_RE = re.compile(r"-?\d+")


def read_int(s, start_position):
    """
    If an integer begins at the specified position in the given
    string, then return a tuple ``(val, end_position)`` containing the
    value of the integer and the position where it ends.  Otherwise,
    raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python integer exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched integer casted to an int,
        and the end position of the int in ``s``.
    :rtype: tuple(int, int)

    :raise ReadError: If the ``_READ_INT_RE`` regex doesn't return a
        match in ``s`` at ``start_position``.

    :Example:

    >>> from nltk.internals import read_int
    >>> read_int('42 is the answer', 0)
    (42, 2)

    """
    m = _READ_INT_RE.match(s, start_position)
    if not m:
        raise ReadError("integer", start_position)
    return int(m.group()), m.end()


_READ_NUMBER_VALUE = re.compile(r"-?(\d*)([.]?\d*)?")


def read_number(s, start_position):
    """
    If an integer or float begins at the specified position in the
    given string, then return a tuple ``(val, end_position)``
    containing the value of the number and the position where it ends.
    Otherwise, raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python number exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched number casted to a ``float``,
        and the end position of the number in ``s``.
    :rtype: tuple(float, int)

    :raise ReadError: If the ``_READ_NUMBER_VALUE`` regex doesn't return a
        match in ``s`` at ``start_position``.

    :Example:

    >>> from nltk.internals import read_number
    >>> read_number('Pi is 3.14159', 6)
    (3.14159, 13)

    """
    m = _READ_NUMBER_VALUE.match(s, start_position)
    if not m or not (m.group(1) or m.group(2)):
        raise ReadError("number", start_position)
    if m.group(2):
        return float(m.group()), m.end()
    else:
        return int(m.group()), m.end()


######################################################################
# Check if a method has been overridden
######################################################################


def overridden(method):
    """
    :return: True if ``method`` overrides some method with the same
        name in a base class.  This is typically used when defining
        abstract base classes or interfaces, to allow subclasses to define
        either of two related methods:

        >>> class EaterI:
        ...     '''Subclass must define eat() or batch_eat().'''
        ...     def eat(self, food):
        ...         if overridden(self.batch_eat):
        ...             return self.batch_eat([food])[0]
        ...         else:
        ...             raise NotImplementedError()
        ...     def batch_eat(self, foods):
        ...         return [self.eat(food) for food in foods]

    :type method: instance method
    """
    if isinstance(method, types.MethodType) and method.__self__.__class__ is not None:
        name = method.__name__
        funcs = [
            cls.__dict__[name]
            for cls in _mro(method.__self__.__class__)
            if name in cls.__dict__
        ]
        return len(funcs) > 1
    else:
        raise TypeError("Expected an instance method.")


def _mro(cls):
    """
    Return the method resolution order for ``cls`` -- i.e., a list
    containing ``cls`` and all its base classes, in the order in which
    they would be checked by ``getattr``.  For new-style classes, this
    is just cls.__mro__.  For classic classes, this can be obtained by
    a depth-first left-to-right traversal of ``__bases__``.
    """
    if isinstance(cls, type):
        return cls.__mro__
    else:
        mro = [cls]
        for base in cls.__bases__:
            mro.extend(_mro(base))
        return mro


######################################################################
# Deprecation decorator & base class
######################################################################
# [xx] dedent msg first if it comes from  a docstring.


def _add_epytext_field(obj, field, message):
    """Add an epytext @field to a given object's docstring."""
    indent = ""
    # If we already have a docstring, then add a blank line to separate
    # it from the new field, and check its indentation.
    if obj.__doc__:
        obj.__doc__ = obj.__doc__.rstrip() + "\n\n"
        indents = re.findall(r"(?<=\n)[ ]+(?!\s)", obj.__doc__.expandtabs())
        if indents:
            indent = min(indents)
    # If we don't have a docstring, add an empty one.
    else:
        obj.__doc__ = ""

    obj.__doc__ += textwrap.fill(
        f"@{field}: {message}",
        initial_indent=indent,
        subsequent_indent=indent + "    ",
    )


def deprecated(message):
    """
    A decorator used to mark functions as deprecated.  This will cause
    a warning to be printed the when the function is used.  Usage:

        >>> from nltk.internals import deprecated
        >>> @deprecated('Use foo() instead')
        ... def bar(x):
        ...     print(x/10)

    """

    def decorator(func):
        msg = f"Function {func.__name__}() has been deprecated.  {message}"
        msg = "\n" + textwrap.fill(msg, initial_indent="  ", subsequent_indent="  ")

        def newFunc(*args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        # Copy the old function's name, docstring, & dict
        newFunc.__dict__.update(func.__dict__)
        newFunc.__name__ = func.__name__
        newFunc.__doc__ = func.__doc__
        newFunc.__deprecated__ = True
        # Add a @deprecated field to the docstring.
        _add_epytext_field(newFunc, "deprecated", message)
        return newFunc

    return decorator


class Deprecated:
    """
    A base class used to mark deprecated classes.  A typical usage is to
    alert users that the name of a class has changed:

        >>> from nltk.internals import Deprecated
        >>> class NewClassName:
        ...     pass # All logic goes here.
        ...
        >>> class OldClassName(Deprecated, NewClassName):
        ...     "Use NewClassName instead."

    The docstring of the deprecated class will be used in the
    deprecation warning message.
    """

    def __new__(cls, *args, **kwargs):
        # Figure out which class is the deprecated one.
        dep_cls = None
        for base in _mro(cls):
            if Deprecated in base.__bases__:
                dep_cls = base
                break
        assert dep_cls, "Unable to determine which base is deprecated."

        # Construct an appropriate warning.
        doc = dep_cls.__doc__ or "".strip()
        # If there's a @deprecated field, strip off the field marker.
        doc = re.sub(r"\A\s*@deprecated:", r"", doc)
        # Strip off any indentation.
        doc = re.sub(r"(?m)^\s*", "", doc)
        # Construct a 'name' string.
        name = "Class %s" % dep_cls.__name__
        if cls != dep_cls:
            name += " (base class for %s)" % cls.__name__
        # Put it all together.
        msg = f"{name} has been deprecated.  {doc}"
        # Wrap it.
        msg = "\n" + textwrap.fill(msg, initial_indent="    ", subsequent_indent="    ")
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        # Do the actual work of __new__.
        return object.__new__(cls)


##########################################################################
# COUNTER, FOR UNIQUE NAMING
##########################################################################


class Counter:
    """
    A counter that auto-increments each time its value is read.
    """

    def __init__(self, initial_value=0):
        self._value = initial_value

    def get(self):
        self._value += 1
        return self._value


##########################################################################
# Search for files/binaries
##########################################################################


def find_file_iter(
    filename,
    env_vars=(),
    searchpath=(),
    file_names=None,
    url=None,
    verbose=False,
    finding_dir=False,
):
    """
    Search for a file to be used by nltk.

    :param filename: The name or path of the file.
    :param env_vars: A list of environment variable names to check.
    :param file_names: A list of alternative file names to check.
    :param searchpath: List of directories to search.
    :param url: URL presented to user for download help.
    :param verbose: Whether or not to print path when a file is found.
    """
    file_names = [filename] + (file_names or [])
    assert isinstance(filename, str)
    assert not isinstance(file_names, str)
    assert not isinstance(searchpath, str)
    if isinstance(env_vars, str):
        env_vars = env_vars.split()
    yielded = False

    # File exists, no magic
    for alternative in file_names:
        path_to_file = os.path.join(filename, alternative)
        if os.path.isfile(path_to_file):
            if verbose:
                print(f"[Found {filename}: {path_to_file}]")
            yielded = True
            yield path_to_file
        # Check the bare alternatives
        if os.path.isfile(alternative):
            if verbose:
                print(f"[Found {filename}: {alternative}]")
            yielded = True
            yield alternative
        # Check if the alternative is inside a 'file' directory
        path_to_file = os.path.join(filename, "file", alternative)
        if os.path.isfile(path_to_file):
            if verbose:
                print(f"[Found {filename}: {path_to_file}]")
            yielded = True
            yield path_to_file

    # Check environment variables
    for env_var in env_vars:
        if env_var in os.environ:
            if finding_dir:  # This is to find a directory instead of file
                for env_dir in os.environ[env_var].split(os.pathsep):
                    env_dir = os.path.expanduser(env_dir)
                    if env_dir:
                        yielded = True
                        yield env_dir

            for env_dir in os.environ[env_var].split(os.pathsep):
                env_dir = os.path.expanduser(env_dir)
                # Check if the environment variable contains a direct path to the bin
                if os.path.isfile(env_dir):
                    if verbose:
                        print(f"[Found {filename}: {env_dir}]")
                    yielded = True
                    yield env_dir
                # Check if the possible bin names exist inside the environment variable directories
                for alternative in file_names:
                    path_to_file = os.path.join(env_dir, alternative)
                    if os.path.isfile(path_to_file):
                        if verbose:
                            print(f"[Found {filename}: {path_to_file}]")
                        yielded = True
                        yield path_to_file
                    # Check if the alternative is inside a 'file' directory
                    # path_to_file = os.path.join(env_dir, 'file', alternative)

                    # Check if the alternative is inside a 'bin' directory
                    path_to_file = os.path.join(env_dir, "bin", alternative)

                    if os.path.isfile(path_to_file):
                        if verbose:
                            print(f"[Found {filename}: {path_to_file}]")
                        yielded = True
                        yield path_to_file

    # Check the path list.
    for directory in searchpath:
        for alternative in file_names:
            path_to_file = os.path.join(directory, alternative)
            if os.path.isfile(path_to_file):
                yielded = True
                yield path_to_file

    # If we're on a POSIX system, then try using the 'which' command
    # to find the file.
    if os.name == "posix":
        for alternative in file_names:
            try:
                p = subprocess.Popen(
                    ["which", alternative],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = p.communicate()
                path = _decode_stdoutdata(stdout).strip()
                if path.endswith(alternative) and os.path.exists(path):
                    if verbose:
                        print(f"[Found {filename}: {path}]")
                    yielded = True
                    yield path
            except (KeyboardInterrupt, SystemExit, OSError):
                raise
            finally:
                pass

    if not yielded:
        msg = (
            "NLTK was unable to find the %s file!"
            "\nUse software specific "
            "configuration parameters" % filename
        )
        if env_vars:
            msg += " or set the %s environment variable" % env_vars[0]
        msg += "."
        if searchpath:
            msg += "\n\n  Searched in:"
            msg += "".join("\n    - %s" % d for d in searchpath)
        if url:
            msg += f"\n\n  For more information on {filename}, see:\n    <{url}>"
        div = "=" * 75
        raise LookupError(f"\n\n{div}\n{msg}\n{div}")


def find_file(
    filename, env_vars=(), searchpath=(), file_names=None, url=None, verbose=False
):
    return next(
        find_file_iter(filename, env_vars, searchpath, file_names, url, verbose)
    )


def find_dir(
    filename, env_vars=(), searchpath=(), file_names=None, url=None, verbose=False
):
    return next(
        find_file_iter(
            filename, env_vars, searchpath, file_names, url, verbose, finding_dir=True
        )
    )


def find_binary_iter(
    name,
    path_to_bin=None,
    env_vars=(),
    searchpath=(),
    binary_names=None,
    url=None,
    verbose=False,
):
    """
    Search for a file to be used by nltk.

    :param name: The name or path of the file.
    :param path_to_bin: The user-supplied binary location (deprecated)
    :param env_vars: A list of environment variable names to check.
    :param file_names: A list of alternative file names to check.
    :param searchpath: List of directories to search.
    :param url: URL presented to user for download help.
    :param verbose: Whether or not to print path when a file is found.
    """
    # Searching by a *bare* tool name (no explicit ``path_to_bin`` and no
    # directory component in ``name``) is the insecure case: ``find_file_iter``
    # probes the current working directory for ``<name>/<name>`` and the bare
    # name before the configured ``env_vars`` / ``searchpath``, so a planted
    # ``./<name>/...`` could be returned and -- because it contains a separator
    # -- run relative to the CWD rather than looked up on PATH: arbitrary code
    # execution (CWE-426 / CWE-427). Only in that case do we refuse CWD-relative
    # matches and accept solely a trusted absolute location (env var / searchpath
    # / ``which``). An explicit path supplied via ``path_to_bin`` or via ``name``
    # itself (e.g. ``tools/prover9``) is the caller's own choice and is honored
    # as before. ``not path_to_bin`` (rather than ``is None``) so an empty-string
    # path_to_bin -- which ``path_to_bin or name`` already falls back to ``name``
    # for -- cannot bypass the check.
    searching_bare_name = not path_to_bin and os.path.dirname(name) == ""
    safe_match = False
    for path in find_file_iter(
        path_to_bin or name, env_vars, searchpath, binary_names, url, verbose
    ):
        if searching_bare_name and not os.path.isabs(path):
            continue
        safe_match = True
        yield path
    if searching_bare_name and not safe_match:
        # ``find_file_iter`` itself raises ``LookupError`` when nothing matches,
        # so reaching here means it found only untrusted CWD-relative
        # executables, which were rejected above.
        raise LookupError(
            f"NLTK found {name!r} only in the current working directory, which "
            "is not a trusted location for executables. Install it on PATH or in "
            "a configured location, or pass an explicit path_to_bin."
        )


def find_binary(
    name,
    path_to_bin=None,
    env_vars=(),
    searchpath=(),
    binary_names=None,
    url=None,
    verbose=False,
):
    return next(
        find_binary_iter(
            name, path_to_bin, env_vars, searchpath, binary_names, url, verbose
        )
    )


def find_jar_iter(
    name_pattern,
    path_to_jar=None,
    env_vars=(),
    searchpath=(),
    url=None,
    verbose=False,
    is_regex=False,
):
    """
    Search for a jar that is used by nltk.

    :param name_pattern: The name of the jar file
    :param path_to_jar: The user-supplied jar location, or None.
    :param env_vars: A list of environment variable names to check
                     in addition to the CLASSPATH variable which is
                     checked by default.
    :param searchpath: List of directories to search.
    :param is_regex: Whether name is a regular expression.
    """

    assert isinstance(name_pattern, str)
    assert not isinstance(searchpath, str)
    if isinstance(env_vars, str):
        env_vars = env_vars.split()
    yielded = False

    # Make sure we check the CLASSPATH first
    env_vars = ["CLASSPATH"] + list(env_vars)

    # If an explicit location was given, then check it, and yield it if
    # it's present; otherwise, complain.
    if path_to_jar is not None:
        if os.path.isfile(path_to_jar):
            yielded = True
            yield path_to_jar
        else:
            raise LookupError(
                f"Could not find {name_pattern} jar file at {path_to_jar}"
            )

    # Check environment variables
    for env_var in env_vars:
        if env_var in os.environ:
            if env_var == "CLASSPATH":
                classpath = os.environ["CLASSPATH"]
                for cp in classpath.split(os.path.pathsep):
                    cp = os.path.expanduser(cp)
                    if os.path.isfile(cp):
                        filename = os.path.basename(cp)
                        if (
                            is_regex
                            and re.match(name_pattern, filename)
                            or (not is_regex and filename == name_pattern)
                        ):
                            if verbose:
                                print(f"[Found {name_pattern}: {cp}]")
                            yielded = True
                            yield cp
                    # The case where user put directory containing the jar file in the classpath
                    if os.path.isdir(cp):
                        if not is_regex:
                            if os.path.isfile(os.path.join(cp, name_pattern)):
                                if verbose:
                                    print(f"[Found {name_pattern}: {cp}]")
                                yielded = True
                                yield os.path.join(cp, name_pattern)
                        else:
                            # Look for file using regular expression
                            for file_name in os.listdir(cp):
                                if re.match(name_pattern, file_name):
                                    if verbose:
                                        print(
                                            "[Found %s: %s]"
                                            % (
                                                name_pattern,
                                                os.path.join(cp, file_name),
                                            )
                                        )
                                    yielded = True
                                    yield os.path.join(cp, file_name)

            else:
                jar_env = os.path.expanduser(os.environ[env_var])
                jar_iter = (
                    (
                        os.path.join(jar_env, path_to_jar)
                        for path_to_jar in os.listdir(jar_env)
                    )
                    if os.path.isdir(jar_env)
                    else (jar_env,)
                )
                for path_to_jar in jar_iter:
                    if os.path.isfile(path_to_jar):
                        filename = os.path.basename(path_to_jar)
                        if (
                            is_regex
                            and re.match(name_pattern, filename)
                            or (not is_regex and filename == name_pattern)
                        ):
                            if verbose:
                                print(f"[Found {name_pattern}: {path_to_jar}]")
                            yielded = True
                            yield path_to_jar

    # Check the path list.
    for directory in searchpath:
        if is_regex:
            for filename in os.listdir(directory):
                path_to_jar = os.path.join(directory, filename)
                if os.path.isfile(path_to_jar):
                    if re.match(name_pattern, filename):
                        if verbose:
                            print(f"[Found {filename}: {path_to_jar}]")
                yielded = True
                yield path_to_jar
        else:
            path_to_jar = os.path.join(directory, name_pattern)
            if os.path.isfile(path_to_jar):
                if verbose:
                    print(f"[Found {name_pattern}: {path_to_jar}]")
                yielded = True
                yield path_to_jar

    if not yielded:
        # If nothing was found, raise an error
        msg = "NLTK was unable to find %s!" % name_pattern
        if env_vars:
            msg += " Set the %s environment variable" % env_vars[0]
        msg = textwrap.fill(msg + ".", initial_indent="  ", subsequent_indent="  ")
        if searchpath:
            msg += "\n\n  Searched in:"
            msg += "".join("\n    - %s" % d for d in searchpath)
        if url:
            msg += "\n\n  For more information, on {}, see:\n    <{}>".format(
                name_pattern,
                url,
            )
        div = "=" * 75
        raise LookupError(f"\n\n{div}\n{msg}\n{div}")


def find_jar(
    name_pattern,
    path_to_jar=None,
    env_vars=(),
    searchpath=(),
    url=None,
    verbose=False,
    is_regex=False,
):
    return next(
        find_jar_iter(
            name_pattern, path_to_jar, env_vars, searchpath, url, verbose, is_regex
        )
    )


def find_jars_within_path(path_to_jars):
    return [
        os.path.join(root, filename)
        for root, dirnames, filenames in os.walk(path_to_jars)
        for filename in fnmatch.filter(filenames, "*.jar")
    ]


def _decode_stdoutdata(stdoutdata):
    """Convert data read from stdout/stderr to unicode"""
    if not isinstance(stdoutdata, bytes):
        return stdoutdata

    encoding = getattr(sys.__stdout__, "encoding", locale.getpreferredencoding())
    if encoding is None:
        return stdoutdata.decode()
    return stdoutdata.decode(encoding)


##########################################################################
# Import Stdlib Module
##########################################################################


def import_from_stdlib(module):
    """
    When python is run from within the nltk/ directory tree, the
    current directory is included at the beginning of the search path.
    Unfortunately, that means that modules within nltk can sometimes
    shadow standard library modules.  As an example, the stdlib
    'inspect' module will attempt to import the stdlib 'tokenize'
    module, but will instead end up importing NLTK's 'tokenize' module
    instead (causing the import to fail).
    """
    old_path = sys.path
    sys.path = [d for d in sys.path if d not in ("", ".")]
    m = __import__(module)
    sys.path = old_path
    return m


##########################################################################
# Wrapper for ElementTree Elements
##########################################################################


class ElementWrapper:
    """
    A wrapper around ElementTree Element objects whose main purpose is
    to provide nicer __repr__ and __str__ methods.  In addition, any
    of the wrapped Element's methods that return other Element objects
    are overridden to wrap those values before returning them.

    This makes Elements more convenient to work with in
    interactive sessions and doctests, at the expense of some
    efficiency.
    """

    # Prevent double-wrapping:
    def __new__(cls, etree):
        """
        Create and return a wrapper around a given Element object.
        If ``etree`` is an ``ElementWrapper``, then ``etree`` is
        returned as-is.
        """
        if isinstance(etree, ElementWrapper):
            return etree
        else:
            return object.__new__(ElementWrapper)

    def __init__(self, etree):
        r"""
        Initialize a new Element wrapper for ``etree``.

        If ``etree`` is a string, then it will be converted to an
        Element object using ``nltk.xmlsec.fromstring()`` first, which
        refuses documents that declare XML entities:

            >>> ElementWrapper("<test></test>")
            <Element "<?xml version='1.0' encoding='utf8'?>\n<test />">

        """
        if isinstance(etree, str):
            # nltk.xmlsec refuses entity declarations, so a hostile string
            # cannot expand to exhaust memory (CWE-776).
            from nltk.xmlsec import fromstring as safe_fromstring

            etree = safe_fromstring(etree)
        self.__dict__["_etree"] = etree

    def unwrap(self):
        """
        Return the Element object wrapped by this wrapper.
        """
        return self._etree

    ##////////////////////////////////////////////////////////////
    # { String Representation
    ##////////////////////////////////////////////////////////////

    def __repr__(self):
        s = ElementTree.tostring(self._etree, encoding="utf8").decode("utf8")
        if len(s) > 60:
            e = s.rfind("<")
            if (len(s) - e) > 30:
                e = -20
            s = f"{s[:30]}...{s[e:]}"
        return "<Element %r>" % s

    def __str__(self):
        """
        :return: the result of applying ``ElementTree.tostring()`` to
        the wrapped Element object.
        """
        return (
            ElementTree.tostring(self._etree, encoding="utf8").decode("utf8").rstrip()
        )

    ##////////////////////////////////////////////////////////////
    # { Element interface Delegation (pass-through)
    ##////////////////////////////////////////////////////////////

    def __getattr__(self, attrib):
        return getattr(self._etree, attrib)

    def __setattr__(self, attr, value):
        return setattr(self._etree, attr, value)

    def __delattr__(self, attr):
        return delattr(self._etree, attr)

    def __setitem__(self, index, element):
        self._etree[index] = element

    def __delitem__(self, index):
        del self._etree[index]

    def __setslice__(self, start, stop, elements):
        self._etree[start:stop] = elements

    def __delslice__(self, start, stop):
        del self._etree[start:stop]

    def __len__(self):
        return len(self._etree)

    ##////////////////////////////////////////////////////////////
    # { Element interface Delegation (wrap result)
    ##////////////////////////////////////////////////////////////

    def __getitem__(self, index):
        return ElementWrapper(self._etree[index])

    def __getslice__(self, start, stop):
        return [ElementWrapper(elt) for elt in self._etree[start:stop]]

    def getchildren(self):
        return [ElementWrapper(elt) for elt in self._etree]

    def getiterator(self, tag=None):
        return (ElementWrapper(elt) for elt in self._etree.getiterator(tag))

    def makeelement(self, tag, attrib):
        return ElementWrapper(self._etree.makeelement(tag, attrib))

    def find(self, path):
        elt = self._etree.find(path)
        if elt is None:
            return elt
        else:
            return ElementWrapper(elt)

    def findall(self, path):
        return [ElementWrapper(elt) for elt in self._etree.findall(path)]


######################################################################
# Helper for Handling Slicing
######################################################################


def slice_bounds(sequence, slice_obj, allow_step=False):
    """
    Given a slice, return the corresponding (start, stop) bounds,
    taking into account None indices and negative indices.  The
    following guarantees are made for the returned start and stop values:

      - 0 <= start <= len(sequence)
      - 0 <= stop <= len(sequence)
      - start <= stop

    :raise ValueError: If ``slice_obj.step`` is not None.
    :param allow_step: If true, then the slice object may have a
        non-None step.  If it does, then return a tuple
        (start, stop, step).
    """
    start, stop = (slice_obj.start, slice_obj.stop)

    # If allow_step is true, then include the step in our return
    # value tuple.
    if allow_step:
        step = slice_obj.step
        if step is None:
            step = 1
        # Use a recursive call without allow_step to find the slice
        # bounds.  If step is negative, then the roles of start and
        # stop (in terms of default values, etc), are swapped.
        if step < 0:
            start, stop = slice_bounds(sequence, slice(stop, start))
        else:
            start, stop = slice_bounds(sequence, slice(start, stop))
        return start, stop, step

    # Otherwise, make sure that no non-default step value is used.
    elif slice_obj.step not in (None, 1):
        raise ValueError(
            "slices with steps are not supported by %s" % sequence.__class__.__name__
        )

    # Supply default offsets.
    if start is None:
        start = 0
    if stop is None:
        stop = len(sequence)

    # Handle negative indices.
    if start < 0:
        start = max(0, len(sequence) + start)
    if stop < 0:
        stop = max(0, len(sequence) + stop)

    # Make sure stop doesn't go past the end of the list.  Note that
    # we avoid calculating len(sequence) if possible, because for lazy
    # sequences, calculating the length of a sequence can be expensive.
    if stop > 0:
        try:
            sequence[stop - 1]
        except IndexError:
            stop = len(sequence)

    # Make sure start isn't past stop.
    start = min(start, stop)

    # That's all folks!
    return start, stop


######################################################################
# Permission Checking
######################################################################


def is_writable(path):
    # Ensure that it exists.
    if not os.path.exists(path):
        return False

    # If we're on a posix system, check its permissions.
    if hasattr(os, "getuid"):
        statdata = os.stat(path)
        perm = stat.S_IMODE(statdata.st_mode)
        # is it world-writable?
        if perm & 0o002:
            return True
        # do we own it?
        elif statdata.st_uid == os.getuid() and (perm & 0o200):
            return True
        # are we in a group that can write to it?
        elif (statdata.st_gid in [os.getgid()] + os.getgroups()) and (perm & 0o020):
            return True
        # otherwise, we can't write to it.
        else:
            return False

    # Otherwise, we'll assume it's writable.
    # [xx] should we do other checks on other platforms?
    return True


######################################################################
# NLTK Error reporting
######################################################################


def raise_unorderable_types(ordering, a, b):
    raise TypeError(
        "unorderable types: %s() %s %s()"
        % (type(a).__name__, ordering, type(b).__name__)
    )
