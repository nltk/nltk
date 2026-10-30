# -*- coding: utf-8 -*-
"""
Regression tests for the security fixes of the 3.4 maintenance line.

One test per vulnerability class of the security ledger, each exercising the
real code path on this interpreter (Python 2.7 or 3): a refused input raises,
an ordinary input still works. Run with ``pytest nltk/test/unit/test_security_backport.py``.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import io
import os
import pickle
import shutil
import tempfile
import time
import zipfile

import pytest

from nltk import csvsec, jsontags, pathsec, picklesec, xmlsec
from nltk.internals import _decode_string_literal, _validate_java_options


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------


@pytest.fixture
def tmpdir_path():
    path = tempfile.mkdtemp(prefix="nltk-sec-")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class TestRestrictedPickle(object):
    def test_containers_load(self):
        data = pickle.dumps({"a": set([1, 2]), "b": (1.5, "x"), "c": [None, True]}, protocol=2)
        assert picklesec.restricted_pickle_loads(data) == {"a": set([1, 2]), "b": (1.5, "x"), "c": [None, True]}

    def test_global_outside_the_allowlist_is_refused(self):
        # the pickle opcode that names a global: nothing outside NLTK's
        # resource classes may be looked up (CWE-502)
        with pytest.raises(pickle.UnpicklingError):
            picklesec.restricted_pickle_loads(b"cposix\nsystem\np0\n.")
        with pytest.raises(pickle.UnpicklingError):
            picklesec.restricted_pickle_loads(b"c__builtin__\neval\np0\n.")

    def test_nltk_class_loads(self):
        from nltk.probability import FreqDist

        fd = FreqDist("abracadabra")
        assert picklesec.restricted_pickle_loads(pickle.dumps(fd, protocol=2)) == fd


class TestPathContainment(object):
    def test_inside_root_passes(self, tmpdir_path):
        inner = os.path.join(tmpdir_path, "a", "b")
        os.makedirs(inner)
        assert pathsec.validate_path(inner, required_root=tmpdir_path) == inner

    @pytest.mark.parametrize("rel", ["../x", "a/../../y", "/etc/passwd"])
    def test_escapes_are_refused(self, tmpdir_path, rel):
        bad = rel if os.path.isabs(rel) else os.path.join(tmpdir_path, rel)
        with pytest.raises(pathsec.SecurityError):
            pathsec.validate_path(bad, required_root=tmpdir_path)

    def test_symlink_out_of_root_is_refused(self, tmpdir_path):
        outside = tempfile.mkdtemp(prefix="nltk-sec-out-")
        try:
            link = os.path.join(tmpdir_path, "link")
            os.symlink(outside, link)
            with pytest.raises(pathsec.SecurityError):
                pathsec.validate_path(os.path.join(link, "x"), required_root=tmpdir_path)
        finally:
            shutil.rmtree(outside, ignore_errors=True)


class TestDataFind(object):
    def test_traversal_out_of_a_data_root_is_refused(self):
        from nltk import data

        with pytest.raises((pathsec.SecurityError, LookupError)):
            data.find("../../../../etc/passwd")
        with pytest.raises((pathsec.SecurityError, LookupError)):
            data.find("corpora/../../../../../etc/passwd")

    def test_pointer_join_cannot_escape(self, tmpdir_path):
        from nltk.data import FileSystemPathPointer

        open(os.path.join(tmpdir_path, "f.txt"), "w").close()
        ptr = FileSystemPathPointer(tmpdir_path)
        assert ptr.join("f.txt").path.endswith("f.txt")
        with pytest.raises(pathsec.SecurityError):
            ptr.join("../f.txt")

    def test_yaml_resource_is_safe_loaded(self, tmpdir_path):
        from nltk import data

        path = os.path.join(tmpdir_path, "r.yaml")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("a: 1\nb: [x, y]\n")
        assert data.load("file:" + path, format="yaml", cache=False) == {"a": 1, "b": ["x", "y"]}
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("!!python/object/apply:os.system ['true']\n")
        import yaml

        with pytest.raises(yaml.YAMLError):
            data.load("file:" + path, format="yaml", cache=False)

    def test_remote_resource_scheme_is_http_only(self):
        from nltk import data

        with pytest.raises(pathsec.SecurityError):
            data._open("ftp://host/x")


class TestZipMembers(object):
    @pytest.mark.parametrize("name", ["../evil", "/abs", "C:\\x", "pkg/ok/../../evil", "a\x00b", "other/f.txt"])
    def test_bad_members_are_refused(self, tmpdir_path, name):
        with pytest.raises(pathsec.SecurityError):
            pathsec.validate_zip_member(name, tmpdir_path, "pkg")

    def test_owned_member_passes(self, tmpdir_path):
        target = pathsec.validate_zip_member("pkg/a/b.txt", tmpdir_path, "pkg")
        assert target.endswith(os.path.join("pkg", "a", "b.txt"))

    def test_downloader_refuses_the_whole_archive(self, tmpdir_path):
        from nltk import downloader

        archive = os.path.join(tmpdir_path, "pkg.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("pkg/ok.txt", "fine")
            zf.writestr("../escape.txt", "outside")
        out = os.path.join(tmpdir_path, "out")
        messages = list(downloader._unzip_iter(archive, out, verbose=False, expected_root="pkg"))
        assert any(isinstance(m, downloader.ErrorMessage) for m in messages)
        assert not os.path.exists(os.path.join(out, "pkg", "ok.txt"))

    def test_downloader_extracts_a_clean_archive(self, tmpdir_path):
        from nltk import downloader

        archive = os.path.join(tmpdir_path, "good.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("pkg/a/b.txt", "fine")
        out = os.path.join(tmpdir_path, "out2")
        messages = list(downloader._unzip_iter(archive, out, verbose=False, expected_root="pkg"))
        assert not [m for m in messages if isinstance(m, downloader.ErrorMessage)]
        with io.open(os.path.join(out, "pkg", "a", "b.txt")) as fh:
            assert fh.read() == "fine"


class TestUrlScheme(object):
    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://h/x", "data:text/plain,x", "javascript:1"])
    def test_other_schemes_are_refused(self, url):
        with pytest.raises(pathsec.SecurityError):
            pathsec.urlopen(url)

    def test_http_is_the_allowed_scheme(self):
        assert pathsec._ALLOWED_SCHEMES == ("http", "https")


class TestLiteralsAndOptions(object):
    def test_string_literal_is_decoded_not_evaluated(self):
        from nltk.internals import read_str

        assert read_str("x 'a\\tb' y", 2) == ("a\tb", 8)
        value, _ = read_str("'__import__(\"os\").system(\"id\")'", 0)
        assert value.startswith("__import__")

    def test_non_literal_is_refused(self):
        with pytest.raises(ValueError):
            _decode_string_literal("__import__('os')")

    def test_java_options_allowlist(self):
        assert _validate_java_options(["-Xmx512m", "-server"]) == ["-Xmx512m", "-server"]
        for bad in (["-jar", "x.jar"], ["@args"], ["-XX:OnError=ls"], ["-Xmx1g; ls"]):
            with pytest.raises(ValueError):
                _validate_java_options(bad)

    def test_config_java_applies_the_allowlist(self):
        from nltk import internals

        if pathsec.find_on_path("java") is None and not os.environ.get("JAVA_HOME"):
            pytest.skip("no JVM on this machine")
        internals.config_java(options="-Xmx512m -server")
        assert internals._java_options == ["-Xmx512m", "-server"]
        with pytest.raises(ValueError):
            internals.config_java(options=["-jar", "x.jar"])

    def test_relative_binary_is_untrusted(self):
        assert pathsec.untrusted_executable_reason("bin/ls") is not None

    def test_system_binary_is_trusted(self):
        path = pathsec.find_on_path("ls")
        if path is None:
            pytest.skip("no ls on PATH")
        assert pathsec.untrusted_executable_reason(path) is None


class TestWordnetApp(object):
    def test_reference_round_trip_is_json(self):
        from nltk.app import wordnet_app as w

        ref = w.Reference("dog<script>", {"dog.n.01": set(["hypernyms", "hyponyms"])})
        back = w.Reference.decode(ref.encode())
        assert back.word == ref.word and back.synset_relations == ref.synset_relations
        with pytest.raises(ValueError):
            w.Reference.decode("gASVAQAAAAAAAACMAnh4lC4=")  # not JSON: never unpickled

    def test_output_is_escaped_and_shutdown_is_tokened(self):
        from nltk.app import wordnet_app as w

        assert "&lt;script&gt;" in w.pg("dog<script>", "")
        assert len(w._SHUTDOWN_TOKEN) == 32
        assert w._SHUTDOWN_TOKEN in w.get_static_upper_page(True)


class TestDecoratorFence(object):
    def test_decorators_still_work(self):
        from nltk.decorators import decorator, memoize

        @decorator
        def trace(f, *a, **k):
            return f(*a, **k)

        @trace
        def add(x, y=2, *rest, **kw):
            return x + y

        assert add(1) == 3 and add(1, 5) == 6

        @memoize
        def sq(n):
            return n * n

        assert sq(4) == 16

    @pytest.mark.parametrize("sig", ["x, y=__import__('os')", "x); import os; (y", "_wrapper_", "x, *, y"])
    def test_hostile_signatures_are_refused(self, sig):
        from nltk.decorators import _assert_safe_signature

        with pytest.raises(ValueError):
            _assert_safe_signature(sig)


class TestProver9Fence(object):
    @pytest.mark.parametrize("formula", ["end_of_list.", "P(x) % x", "P(x).\nformulas(goals)"])
    def test_injection_is_refused(self, formula):
        from nltk.inference.prover9 import _assert_prover9_safe

        with pytest.raises(ValueError):
            _assert_prover9_safe(formula)

    def test_converted_formula_passes(self):
        from nltk.inference.prover9 import _assert_prover9_safe, convert_to_prover9
        from nltk.sem import Expression

        converted = convert_to_prover9(Expression.fromstring("all x.(P(x) -> Q(x))"))
        assert _assert_prover9_safe(converted) == converted


class TestResourceBounds(object):
    def test_confusion_matrix_is_sparse_and_correct(self):
        from nltk.metrics import ConfusionMatrix

        ref = "DET NN VB DET JJ NN NN IN DET NN".split()
        test = "DET VB VB DET NN NN NN IN DET NN".split()
        cm = ConfusionMatrix(ref, test)
        assert cm["NN", "VB"] == 1 and cm["NN", "NN"] == 3
        assert isinstance(cm._confusion, dict)
        assert "DET" in cm.pretty_format(sort_by_count=True)

    def test_valuation_split_is_linear(self):
        from nltk.sem import evaluate as ev

        assert ev._read_valuation_line("chase => {(b1, g1), (b2, g1)}")[1] == set([("b1", "g1"), ("b2", "g1")])
        started = time.time()
        ev._VAL_SPLIT_RE.split("x " + "=" * 200000 + " y")
        assert time.time() - started < 2.0

    def test_satisfy_refuses_deep_nesting(self):
        from nltk.sem import Expression
        from nltk.sem import evaluate as ev

        dom = set("abcdefghij")
        model = ev.Model(dom, ev.Valuation([("P", set([("a",)]))]))
        assert model.satisfy(Expression.fromstring("exists x. P(x)"), ev.Assignment(dom))
        deep = "all x1." + "".join("all x%d." % i for i in range(2, 9)) + "P(x1)"
        with pytest.raises(ValueError):
            model.satisfy(Expression.fromstring(deep), ev.Assignment(dom))

    def test_anaphora_budget(self):
        from nltk.sem import drt

        expr = drt.DrtExpression.fromstring("([x,y],[dog(x), PRO(y), bark(x)])")
        assert "(y = x)" in str(expr.resolve_anaphora())
        budget = drt._AnaphoraBudget(1)
        budget.charge()
        with pytest.raises(drt.AnaphoraResolutionException):
            budget.charge()

    def test_parse_tree_budget(self, monkeypatch):
        from nltk import CFG, ChartParser
        from nltk.parse import chart as chart_module

        grammar = CFG.fromstring("S -> S S | 'a'")
        assert len(list(ChartParser(grammar).parse(["a"] * 5))) == 14
        monkeypatch.setattr(chart_module, "MAX_PARSE_TREES", 2000)
        with pytest.raises(ValueError):
            list(ChartParser(grammar).parse(["a"] * 12))

    def test_variable_rename_fails_fast(self):
        from nltk.featstruct import FeatStruct

        fs = FeatStruct("[a=?x" + "0" * 50000 + "z, b=?y]")
        started = time.time()
        assert fs.rename_variables()
        assert time.time() - started < 5.0

    def test_distance_caps(self):
        from nltk.metrics.distance import edit_distance, jaro_similarity

        assert edit_distance("kitten", "sitting") == 3
        assert abs(jaro_similarity("MARTHA", "MARHTA") - 0.944) < 0.01
        with pytest.raises(ValueError):
            edit_distance("a" * 3000, "b")
        with pytest.raises(ValueError):
            jaro_similarity("a" * 3000, "b" * 3000)

    def test_ngram_counter_bound(self, monkeypatch):
        from nltk.lm import counter as counter_module
        from nltk.lm import NgramCounter

        c = NgramCounter([[("a",), ("a", "b"), ("a", "b"), ("b", "c")]])
        assert c["a"] == 1 and c[("a",)]["b"] == 2 and c._distinct == 3
        monkeypatch.setattr(counter_module, "MAX_NGRAMS", 2)
        with pytest.raises(ValueError):
            NgramCounter([[("a",), ("b",), ("c",)]])

    def test_meteor_matching(self):
        from nltk.translate import meteor_score as ms

        matches = sorted(ms.exact_match(str("the cat sat on the mat"), str("the cat sat on a mat"))[0])
        assert matches == [(1, 1), (2, 2), (3, 3), (4, 0), (5, 5)]

    def test_chomsky_normal_form_uses_a_deque(self):
        from nltk.tree import Tree
        from nltk.treetransforms import chomsky_normal_form

        tree = Tree.fromstring("(S (A a) (B b) (C c) (D d))")
        chomsky_normal_form(tree, factor="right")
        assert tree.pformat(margin=200) == "(S (A a) (S|<B-C-D> (B b) (S|<C-D> (C c) (D d))))"

    def test_alignment_index_is_sparse(self):
        from nltk.translate import Alignment

        a = Alignment.fromstring("0-0 100000000-1 1-2")
        assert a[100000000] == [(100000000, 1)] and a[5] == []
        assert sorted(a.invert())[:2] == [(0, 0), (1, 100000000)]

    def test_cistem_is_linear(self):
        from nltk.stem.cistem import Cistem

        st = Cistem()
        assert st.segment("Grenzpostens") == ("grenzpost", "ens")
        assert st.stem("Ausgefeiltere") == "ausgefeilt"
        started = time.time()
        st.stem("e" * 100000)
        assert time.time() - started < 5.0

    def test_hungarian_empty_word(self):
        from nltk.stem.snowball import HungarianStemmer

        assert HungarianStemmer().stem("") == ""

    def test_ccg_lexicon_by_position(self):
        from nltk.ccg import lexicon

        lex = lexicon.fromstring(":- S, NP\nx => (S\\NP)/NP\n")
        assert str(lex.categories("x")[0].categ()) == "((S\\NP)/NP)"
        started = time.time()
        lexicon.fromstring(":- S\nx => " + "/".join(["S"] * 3000) + "\n")
        assert time.time() - started < 5.0


class TestEvalSites(object):
    def test_texttiling_window_allowlist(self):
        numpy = pytest.importorskip("numpy")
        from nltk.tokenize.texttiling import smooth

        signal = numpy.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        assert len(smooth(signal, 3, "hanning")) >= 8
        with pytest.raises(ValueError):
            smooth(signal, 3, "__import__('os').system('id')")

    def test_collocations_named_measure(self):
        from nltk.collocations import _named_measure

        assert _named_measure("pmi").__name__ == "pmi"
        with pytest.raises(ValueError):
            _named_measure("__class__")


class TestCsvAndJson(object):
    def test_formula_leads_are_neutralised(self):
        assert csvsec.sanitize_csv_field("=cmd()") == "'=cmd()"
        assert csvsec.sanitize_csv_field("+1-2") == "'+1-2"
        assert csvsec.sanitize_csv_field("-3.5") == "-3.5"
        assert csvsec.sanitize_csv_field("plain") == "plain"
        assert csvsec.sanitize_csv_field(7) == 7

    def test_json_depth_bound(self):
        assert jsontags.safe_json_loads('{"a": [1, {"b": "]"}]}') == {"a": [1, {"b": "]"}]}
        with pytest.raises(ValueError):
            jsontags.safe_json_loads("[" * 200 + "]" * 200)


class TestXml(object):
    def test_plain_document_parses(self):
        root = xmlsec.fromstring(b"<a xmlns='urn:x'><b x='1'>t&amp;u</b><c/></a>")
        assert root.tag == "{urn:x}a" and root[0].attrib == {"x": "1"} and root[0].text == "t&u"

    def test_entity_declaration_is_refused(self):
        bomb = b"<?xml version='1.0'?><!DOCTYPE a [<!ENTITY e 'xxxx'>]><a>&e;</a>"
        with pytest.raises(xmlsec.EntitiesForbidden):
            xmlsec.fromstring(bomb)

    def test_deep_tree_is_refused(self):
        with pytest.raises(xmlsec.StructureForbidden):
            xmlsec.fromstring(b"<a>" * 1500 + b"</a>" * 1500)

    def test_parse_from_path_and_stream(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "f.xml")
        with open(path, "wb") as fh:
            fh.write(b"<r><s>1</s></r>")
        assert xmlsec.parse(path).getroot()[0].text == "1"
        with io.open(path, "rb") as fh:
            assert xmlsec.parse(fh).getroot().tag == "r"


class TestToolPaths(object):
    def test_plain_and_relative_paths_pass(self, tmpdir_path):
        target = os.path.join(tmpdir_path, "m.model")
        open(target, "w").close()
        assert pathsec.validate_tool_path(target) == target
        assert os.path.isabs(pathsec.validate_tool_path("rel.model"))

    def test_links_traversal_and_hardlinks_are_refused(self, tmpdir_path):
        target = os.path.join(tmpdir_path, "m.model")
        open(target, "w").close()
        link = os.path.join(tmpdir_path, "l.model")
        os.symlink(target, link)
        hard = os.path.join(tmpdir_path, "h.model")
        os.link(target, hard)
        with pytest.raises(pathsec.SecurityError):
            pathsec.validate_tool_path(link)
        with pytest.raises(pathsec.SecurityError):
            pathsec.validate_tool_path(os.path.join(tmpdir_path, "..", "x"))
        with pytest.raises(pathsec.SecurityError):
            pathsec.validate_tool_path(hard, for_write=True)
