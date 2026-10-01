from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import tostring

import nltk.pathsec
from nltk.corpus.reader.toolbox import ToolboxCorpusReader


def test_toolbox_xss_mitigation():
    malicious_corpus = r"""\_sh v3.0  400  Rotokas Dictionary
\lx kaa
\script globalThis.XSS=1337;
\123_invalid_start
"""
    with TemporaryDirectory() as d:
        root = Path(d)
        corpus_path = root / "malicious.txt"
        corpus_path.write_text(malicious_corpus, encoding="utf-8")

        # Register temporary root with pathsec so the corpus reader accepts it
        nltk.data.path.append(str(root))

        try:
            reader = ToolboxCorpusReader(str(root), ["malicious.txt"])
            xml_tree = reader.xml(["malicious.txt"])
            xml_str = tostring(xml_tree).decode("utf-8")

            # Validate hazardous HTML tags are neutralized with a safe prefix
            assert "<script>" not in xml_str
            assert "<tb_script>" in xml_str
            assert "globalThis.XSS=1337;" in xml_str

            # Validate XML compliance (tags cannot start with numbers)
            assert "<123_invalid_start>" not in xml_str
            assert "<_123_invalid_start" in xml_str
        finally:
            if str(root) in nltk.data.path:
                nltk.data.path.remove(str(root))
