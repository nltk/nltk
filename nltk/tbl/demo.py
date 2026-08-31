# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

import os
import pickle
import random
import time

from nltk import redos
from nltk.corpus import treebank
from nltk.pathsec import open as pathsec_open
from nltk.pathsec import validate_path
from nltk.picklesec import AllowlistUnpickler
from nltk.redos import TimedPattern
from nltk.tag import BrillTaggerTrainer, RegexpTagger, UnigramTagger
from nltk.tag.brill import Pos, Word
from nltk.tbl import Template, error_list

# Exact ``(module, qualname)`` allowlist for the two model files this demo reads
# back: a baseline tagger cached by ``cache_baseline_tagger`` and a trained Brill
# tagger round-tripped by ``serialize_output``. Both are loaded from a
# caller/data-root path, so they are unpickled through an allowlisting unpickler
# (CWE-502): only the exact classes a legitimate trained tagger reconstructs may
# be built, and any other global (``os.system``, ``builtins.eval``,
# ``subprocess.Popen``, a scientific-stack file sink, ...) raises
# ``UnpicklingError`` instead of executing. Path containment is already enforced
# by ``pathsec.open`` (GHSA-8mgp-746c-j5xp); pinning the unpickler closes the
# remaining warn-only-unpickler gap under the same advisory umbrella.
#
# The set was derived by pickling a real trained ``BrillTagger`` (a
# ``UnigramTagger`` baseline over a ``RegexpTagger`` / ``DefaultTagger`` backoff,
# with learned transformation rules) and recording every ``(module, name)`` its
# pickle asks ``find_class`` to resolve. None of these is a code-execution
# primitive: ``regex._regex.compile`` only rebuilds a compiled regex (the
# pattern engine, not a code compiler), and the inert ``builtins.object``
# sentinel is handled in :class:`_TblModelUnpickler` below.
_TBL_MODEL_ALLOWED_GLOBALS = (
    # The trained tagger itself and its transformation rules / features.
    ("nltk.tag.brill", "BrillTagger"),
    ("nltk.tag.brill", "Word"),
    ("nltk.tag.brill", "Pos"),
    ("nltk.tbl.rule", "Rule"),
    # The baseline tagger and the backoff taggers it wraps.
    ("nltk.tag.sequential", "UnigramTagger"),
    ("nltk.tag.sequential", "RegexpTagger"),
    ("nltk.tag.sequential", "DefaultTagger"),
    # A RegexpTagger stores each pattern as a ReDoS-bounded TimedPattern wrapping
    # a compiled ``regex`` object, rebuilt from its source by regex._regex.compile.
    ("nltk.redos", "TimedPattern"),
    ("regex._regex", "compile"),
)


class _TblModelUnpickler(AllowlistUnpickler):
    """AllowlistUnpickler for the tbl demo's baseline / Brill tagger files.

    It permits exactly :data:`_TBL_MODEL_ALLOWED_GLOBALS` plus the single inert
    ``builtins.object`` primitive. A ``RegexpTagger`` stores each pattern's
    default timeout as the module-level ``nltk.redos._UNSET = object()``
    sentinel, so a legitimately pickled baseline reconstructs a bare
    ``object()``. ``object`` is not a code-execution primitive: NEWOBJ builds an
    empty, state-less instance and the type carries no ``__reduce__`` /
    ``__setstate__`` hook, so it cannot be ridden to a gadget. Every other guard
    of the base unpickler (denied modules, dotted / dunder names, extension
    opcodes, scientific-stack I/O sinks) still applies to all other globals.
    """

    def find_class(self, module, name):
        if (module, name) == ("builtins", "object"):
            return object
        return super().find_class(module, name)


# A generous ceiling on the number of nodes the post-load hardening walk will
# visit. Allowlisting only gates *which* classes a pickle may build; it does not
# bound the *state* those classes are handed, so a hostile file could stitch a
# very large object graph out of purely allowlisted nodes. The walk that
# re-derives every reconstructed regex (below) is itself bounded so it cannot be
# turned into the denial of service it exists to prevent. A real trained Brill
# tagger over the treebank is a few tens of thousands of nodes, so this cap is
# ~2 orders of magnitude of head-room while still finite.
_MAX_MODEL_NODES = 5_000_000


def _regex_source(pattern):
    """Return the *source string* of a reconstructed ``RegexpTagger`` pattern.

    A pattern reconstructed from an untrusted file may be a :class:`TimedPattern`
    (its wall-clock cap possibly disabled via an attacker-supplied
    ``_timeout=None``), a *raw* compiled ``regex`` object (no cap at all), or a
    plain string. Only the source string is trusted; the compiled object and the
    timeout are discarded and re-derived by the caller. A pattern that carries no
    string source is refused rather than silently kept.
    """
    if isinstance(pattern, str):
        return pattern
    # ``TimedPattern`` delegates ``.pattern`` to its wrapped regex; a raw regex
    # object exposes ``.pattern`` directly. ``getattr`` swallows the delegating
    # ``AttributeError`` a malformed wrapper (``_rx`` not a pattern) would raise.
    src = getattr(pattern, "pattern", None)
    if isinstance(src, bytes):
        src = src.decode("latin-1")
    if isinstance(src, str):
        return src
    raise pickle.UnpicklingError(
        "tbl model RegexpTagger holds a pattern with no string source; refusing "
        "to reconstruct an unbounded regex from an untrusted file"
    )


def _harden_reconstructed_model(root):
    """Neutralise ReDoS carried through the allowlisted regex surface.

    The allowlist lets an untrusted file build a :class:`RegexpTagger`,
    :class:`TimedPattern` and a raw compiled ``regex`` object because a genuine
    trained tagger needs them. Name-checking alone is *not* enough: the file also
    controls their *state / constructor args*, so it can plant a catastrophic
    pattern that either (a) lives raw in ``RegexpTagger._regexps`` with no cap, or
    (b) is wrapped in a ``TimedPattern`` whose ``_timeout`` is set to ``None``
    (cap disabled). Either one hangs the process the moment the reloaded tagger
    tags a crafted token (CWE-1333) even though every global was allowlisted.

    After load, walk the reconstructed graph (bounded) and, for every
    ``RegexpTagger``, rebuild ``_regexps`` from each pattern's *source string*
    through :func:`nltk.redos.compile`, which always yields a fresh
    ``TimedPattern`` bound by :data:`nltk.redos.DEFAULT_TIMEOUT`. The hostile raw
    object and the disabled timeout are thrown away; a legitimate pattern is
    re-derived byte-for-byte to the exact object ``RegexpTagger.__init__`` would
    have produced, so tagging is unchanged while a pathological pattern can no
    longer run unbounded. Any stray ``TimedPattern`` reached elsewhere in the
    graph has its ``_timeout`` reset to the module default for the same reason.
    """
    stack = [root]
    seen = set()
    visited = 0
    while stack:
        obj = stack.pop()
        oid = id(obj)
        if oid in seen:
            continue
        seen.add(oid)
        visited += 1
        if visited > _MAX_MODEL_NODES:
            raise pickle.UnpicklingError(
                "tbl model object graph exceeds the safety bound; refusing"
            )
        if isinstance(obj, TimedPattern):
            # Belt and suspenders: a TimedPattern reached anywhere must never
            # carry a disabled / oversized cap. Reset to the module default so
            # even a hand-placed wrapper is bounded. (__slots__, so set directly.)
            obj._timeout = redos._UNSET
            continue
        if isinstance(obj, RegexpTagger):
            rebuilt = []
            for entry in obj._regexps:
                # Each entry is a ``(pattern, tag)`` pair; re-derive the pattern
                # from its source so a raw / uncapped object cannot survive.
                pattern, tag = entry
                rebuilt.append((redos.compile(_regex_source(pattern)), tag))
            obj._regexps = rebuilt
            # Fall through to also descend into backoff taggers below.
        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
            continue
        if isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
            continue
        state = getattr(obj, "__dict__", None)
        if isinstance(state, dict):
            stack.extend(state.values())
    return root


def _load_tbl_model(file):
    """Unpickle a tbl demo model file through the allowlisting unpickler.

    ``file`` is an already pathsec-validated binary handle (its path was checked
    against the NLTK data sandbox by :func:`nltk.pathsec.open`). Only the exact
    globals a legitimate baseline / Brill tagger needs are reconstructed; any
    code-execution gadget raises ``pickle.UnpicklingError`` before it can run.

    The allowlist gates *which* classes are built, not the *state* they are
    handed, so the reconstructed model is then passed through
    :func:`_harden_reconstructed_model`, which re-derives every regex pattern
    under the ReDoS wall-clock cap. Together they close both the code-execution
    and the denial-of-service paths through the allowlisted surface.
    """
    model = _TblModelUnpickler(file, allowed_globals=_TBL_MODEL_ALLOWED_GLOBALS).load()
    return _harden_reconstructed_model(model)


def demo():
    """
    Run a demo with defaults. See source comments for details,
    or docstrings of any of the more specific demo_* functions.
    """
    postag()


def demo_repr_rule_format():
    """
    Exemplify repr(Rule) (see also str(Rule) and Rule.format("verbose"))
    """
    postag(ruleformat="repr")


def demo_str_rule_format():
    """
    Exemplify repr(Rule) (see also str(Rule) and Rule.format("verbose"))
    """
    postag(ruleformat="str")


def demo_verbose_rule_format():
    """
    Exemplify Rule.format("verbose")
    """
    postag(ruleformat="verbose")


def demo_multiposition_feature():
    """
    The feature/s of a template takes a list of positions
    relative to the current word where the feature should be
    looked for, conceptually joined by logical OR. For instance,
    Pos([-1, 1]), given a value V, will hold whenever V is found
    one step to the left and/or one step to the right.

    For contiguous ranges, a 2-arg form giving inclusive end
    points can also be used: Pos(-3, -1) is the same as the arg
    below.
    """
    postag(templates=[Template(Pos([-3, -2, -1]))])


def demo_multifeature_template():
    """
    Templates can have more than a single feature.
    """
    postag(templates=[Template(Word([0]), Pos([-2, -1]))])


def demo_template_statistics():
    """
    Show aggregate statistics per template. Little used templates are
    candidates for deletion, much used templates may possibly be refined.

    Deleting unused templates is mostly about saving time and/or space:
    training is basically O(T) in the number of templates T
    (also in terms of memory usage, which often will be the limiting factor).
    """
    postag(incremental_stats=True, template_stats=True)


def demo_generated_templates():
    """
    Template.expand and Feature.expand are class methods facilitating
    generating large amounts of templates. See their documentation for
    details.

    Note: training with 500 templates can easily fill all available
    even on relatively small corpora
    """
    wordtpls = Word.expand([-1, 0, 1], [1, 2], excludezero=False)
    tagtpls = Pos.expand([-2, -1, 0, 1], [1, 2], excludezero=True)
    templates = list(Template.expand([wordtpls, tagtpls], combinations=(1, 3)))
    print(
        "Generated {} templates for transformation-based learning".format(
            len(templates)
        )
    )
    postag(templates=templates, incremental_stats=True, template_stats=True)


def demo_learning_curve():
    """
    Plot a learning curve -- the contribution on tagging accuracy of
    the individual rules.
    Note: requires matplotlib
    """
    postag(
        incremental_stats=True,
        separate_baseline_data=True,
        learning_curve_output="learningcurve.png",
    )


def demo_error_analysis():
    """
    Writes a file with context for each erroneous word after tagging testing data
    """
    postag(error_output="errors.txt")


def demo_serialize_tagger():
    """
    Serializes the learned tagger to a file in pickle format; reloads it
    and validates the process.
    """
    postag(serialize_output="tagger.pcl")


def demo_high_accuracy_rules():
    """
    Discard rules with low accuracy. This may hurt performance a bit,
    but will often produce rules which are more interesting read to a human.
    """
    postag(num_sents=3000, min_acc=0.96, min_score=10)


def postag(
    templates=None,
    tagged_data=None,
    num_sents=1000,
    max_rules=300,
    min_score=3,
    min_acc=None,
    train=0.8,
    trace=3,
    randomize=False,
    ruleformat="str",
    incremental_stats=False,
    template_stats=False,
    error_output=None,
    serialize_output=None,
    learning_curve_output=None,
    learning_curve_take=300,
    baseline_backoff_tagger=None,
    separate_baseline_data=False,
    cache_baseline_tagger=None,
):
    """
    Brill Tagger Demonstration
    :param templates: how many sentences of training and testing data to use
    :type templates: list of Template

    :param tagged_data: maximum number of rule instances to create
    :type tagged_data: C{int}

    :param num_sents: how many sentences of training and testing data to use
    :type num_sents: C{int}

    :param max_rules: maximum number of rule instances to create
    :type max_rules: C{int}

    :param min_score: the minimum score for a rule in order for it to be considered
    :type min_score: C{int}

    :param min_acc: the minimum score for a rule in order for it to be considered
    :type min_acc: C{float}

    :param train: the fraction of the the corpus to be used for training (1=all)
    :type train: C{float}

    :param trace: the level of diagnostic tracing output to produce (0-4)
    :type trace: C{int}

    :param randomize: whether the training data should be a random subset of the corpus
    :type randomize: C{bool}

    :param ruleformat: rule output format, one of "str", "repr", "verbose"
    :type ruleformat: C{str}

    :param incremental_stats: if true, will tag incrementally and collect stats for each rule (rather slow)
    :type incremental_stats: C{bool}

    :param template_stats: if true, will print per-template statistics collected in training and (optionally) testing
    :type template_stats: C{bool}

    :param error_output: the file where errors will be saved
    :type error_output: C{string}

    :param serialize_output: the file where the learned tbl tagger will be saved
    :type serialize_output: C{string}

    :param learning_curve_output: filename of plot of learning curve(s) (train and also test, if available)
    :type learning_curve_output: C{string}

    :param learning_curve_take: how many rules plotted
    :type learning_curve_take: C{int}

    :param baseline_backoff_tagger: the file where rules will be saved
    :type baseline_backoff_tagger: tagger

    :param separate_baseline_data: use a fraction of the training data exclusively for training baseline
    :type separate_baseline_data: C{bool}

    :param cache_baseline_tagger: cache baseline tagger to this file (only interesting as a temporary workaround to get
                                  deterministic output from the baseline unigram tagger between python versions)
    :type cache_baseline_tagger: C{string}


    Note on separate_baseline_data: if True, reuse training data both for baseline and rule learner. This
    is fast and fine for a demo, but is likely to generalize worse on unseen data.
    Also cannot be sensibly used for learning curves on training data (the baseline will be artificially high).
    """

    # defaults
    baseline_backoff_tagger = baseline_backoff_tagger or REGEXP_TAGGER
    if templates is None:
        from nltk.tag.brill import brill24, describe_template_sets

        # some pre-built template sets taken from typical systems or publications are
        # available. Print a list with describe_template_sets()
        # for instance:
        templates = brill24()
    (training_data, baseline_data, gold_data, testing_data) = _demo_prepare_data(
        tagged_data, train, num_sents, randomize, separate_baseline_data
    )

    # creating (or reloading from cache) a baseline tagger (unigram tagger)
    # this is just a mechanism for getting deterministic output from the baseline between
    # python versions
    if cache_baseline_tagger:
        if not os.path.exists(cache_baseline_tagger):
            baseline_tagger = UnigramTagger(
                baseline_data, backoff=baseline_backoff_tagger
            )
            # ``cache_baseline_tagger`` is caller-supplied, so the model
            # write/read goes through the pathsec sandbox (GHSA-8mgp-746c-j5xp).
            with pathsec_open(
                cache_baseline_tagger, "wb", context="tbl.demo.cache_baseline_tagger"
            ) as print_rules:
                pickle.dump(baseline_tagger, print_rules)
            print(
                "Trained baseline tagger, pickled it to {}".format(
                    cache_baseline_tagger
                )
            )
        with pathsec_open(
            cache_baseline_tagger, "rb", context="tbl.demo.cache_baseline_tagger"
        ) as print_rules:
            baseline_tagger = _load_tbl_model(print_rules)
            print(f"Reloaded pickled tagger from {cache_baseline_tagger}")
    else:
        baseline_tagger = UnigramTagger(baseline_data, backoff=baseline_backoff_tagger)
        print("Trained baseline tagger")
    if gold_data:
        print(
            "    Accuracy on test set: {:0.4f}".format(
                baseline_tagger.accuracy(gold_data)
            )
        )

    # creating a Brill tagger
    tbrill = time.time()
    trainer = BrillTaggerTrainer(
        baseline_tagger, templates, trace, ruleformat=ruleformat
    )
    print("Training tbl tagger...")
    brill_tagger = trainer.train(training_data, max_rules, min_score, min_acc)
    print(f"Trained tbl tagger in {time.time() - tbrill:0.2f} seconds")
    if gold_data:
        print("    Accuracy on test set: %.4f" % brill_tagger.accuracy(gold_data))

    # printing the learned rules, if learned silently
    if trace == 1:
        print("\nLearned rules: ")
        for ruleno, rule in enumerate(brill_tagger.rules(), 1):
            print(f"{ruleno:4d} {rule.format(ruleformat):s}")

    # printing template statistics (optionally including comparison with the training data)
    # note: if not separate_baseline_data, then baseline accuracy will be artificially high
    if incremental_stats:
        print(
            "Incrementally tagging the test data, collecting individual rule statistics"
        )
        (taggedtest, teststats) = brill_tagger.batch_tag_incremental(
            testing_data, gold_data
        )
        print("    Rule statistics collected")
        if not separate_baseline_data:
            print(
                "WARNING: train_stats asked for separate_baseline_data=True; the baseline "
                "will be artificially high"
            )
        trainstats = brill_tagger.train_stats()
        if template_stats:
            brill_tagger.print_template_statistics(teststats)
        if learning_curve_output:
            _demo_plot(
                learning_curve_output, teststats, trainstats, take=learning_curve_take
            )
            print(f"Wrote plot of learning curve to {learning_curve_output}")
    else:
        print("Tagging the test data")
        taggedtest = brill_tagger.tag_sents(testing_data)
        if template_stats:
            brill_tagger.print_template_statistics()

    # writing error analysis to file
    if error_output is not None:
        with pathsec_open(
            error_output, "w", context="tbl.demo.error_output", encoding="utf-8"
        ) as f:
            f.write("Errors for Brill Tagger %r\n\n" % serialize_output)
            f.write("\n".join(error_list(gold_data, taggedtest)) + "\n")
        print(f"Wrote tagger errors including context to {error_output}")

    # serializing the tagger to a pickle file and reloading (just to see it works)
    if serialize_output is not None:
        taggedtest = brill_tagger.tag_sents(testing_data)
        with pathsec_open(
            serialize_output, "wb", context="tbl.demo.serialize_output"
        ) as print_rules:
            pickle.dump(brill_tagger, print_rules)
        print(f"Wrote pickled tagger to {serialize_output}")
        with pathsec_open(
            serialize_output, "rb", context="tbl.demo.serialize_output"
        ) as print_rules:
            brill_tagger_reloaded = _load_tbl_model(print_rules)
        print(f"Reloaded pickled tagger from {serialize_output}")
        taggedtest_reloaded = brill_tagger_reloaded.tag_sents(testing_data)
        if taggedtest == taggedtest_reloaded:
            print("Reloaded tagger tried on test set, results identical")
        else:
            print("PROBLEM: Reloaded tagger gave different results on test set")


def _demo_prepare_data(
    tagged_data, train, num_sents, randomize, separate_baseline_data
):
    # train is the proportion of data used in training; the rest is reserved
    # for testing.
    if tagged_data is None:
        print("Loading tagged data from treebank... ")
        tagged_data = treebank.tagged_sents()
    if num_sents is None or len(tagged_data) <= num_sents:
        num_sents = len(tagged_data)
    if randomize:
        random.seed(len(tagged_data))
        random.shuffle(tagged_data)
    cutoff = int(num_sents * train)
    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]
    if not separate_baseline_data:
        baseline_data = training_data
    else:
        bl_cutoff = len(training_data) // 3
        (baseline_data, training_data) = (
            training_data[:bl_cutoff],
            training_data[bl_cutoff:],
        )
    (trainseqs, traintokens) = corpus_size(training_data)
    (testseqs, testtokens) = corpus_size(testing_data)
    (bltrainseqs, bltraintokens) = corpus_size(baseline_data)
    print(f"Read testing data ({testseqs:d} sents/{testtokens:d} wds)")
    print(f"Read training data ({trainseqs:d} sents/{traintokens:d} wds)")
    print(
        "Read baseline data ({:d} sents/{:d} wds) {:s}".format(
            bltrainseqs,
            bltraintokens,
            "" if separate_baseline_data else "[reused the training set]",
        )
    )
    return (training_data, baseline_data, gold_data, testing_data)


def _demo_plot(learning_curve_output, teststats, trainstats=None, take=None):
    """Write the learning-curve plot to ``learning_curve_output``.

    The destination is caller-supplied and matplotlib writes it itself, so the
    path is checked against the NLTK data sandbox before any work is done
    (GHSA-8mgp-746c-j5xp); ``pathsec.open`` cannot wrap a ``savefig``.
    """
    validate_path(learning_curve_output, context="tbl.demo.learning_curve_output")
    testcurve = [teststats["initialerrors"]]
    for rulescore in teststats["rulescores"]:
        testcurve.append(testcurve[-1] - rulescore)
    testcurve = [1 - x / teststats["tokencount"] for x in testcurve[:take]]

    traincurve = [trainstats["initialerrors"]]
    for rulescore in trainstats["rulescores"]:
        traincurve.append(traincurve[-1] - rulescore)
    traincurve = [1 - x / trainstats["tokencount"] for x in traincurve[:take]]

    import matplotlib.pyplot as plt

    r = list(range(len(testcurve)))
    plt.plot(r, testcurve, r, traincurve)
    plt.axis([None, None, None, 1.0])
    plt.savefig(learning_curve_output)


NN_CD_TAGGER = RegexpTagger([(r"^-?[0-9]+(\.[0-9]+)?$", "CD"), (r".*", "NN")])

REGEXP_TAGGER = RegexpTagger(
    [
        (r"^-?[0-9]+(\.[0-9]+)?$", "CD"),  # cardinal numbers
        (r"(The|the|A|a|An|an)$", "AT"),  # articles
        (r".*able$", "JJ"),  # adjectives
        (r".*ness$", "NN"),  # nouns formed from adjectives
        (r".*ly$", "RB"),  # adverbs
        (r".*s$", "NNS"),  # plural nouns
        (r".*ing$", "VBG"),  # gerunds
        (r".*ed$", "VBD"),  # past tense verbs
        (r".*", "NN"),  # nouns (default)
    ]
)


def corpus_size(seqs):
    return (len(seqs), sum(len(x) for x in seqs))


if __name__ == "__main__":
    demo_learning_curve()
