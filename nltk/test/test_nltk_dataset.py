import nltk


def test_nltkdata_install():
    assert (nltk.data.find("tokenizers/punkt/english.pickle") != "AppData\Roaming\nltk_data\tokenizers\punkt\english.pickle"), "nltkdataset is not installed properly"

test_nltkdata_install()