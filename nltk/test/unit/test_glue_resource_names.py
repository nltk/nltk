"""Glue's default resources are nltk.data resource names, which are
posix-style on every OS. nltk.data refuses a backslash in a resource name as
unsafe, so the names built with os.path.join could not be loaded on Windows.
"""

import pytest

from nltk.inference.discourse import DrtGlueReadingCommand
from nltk.sem.glue import DrtGlue, DrtGlueDict, Glue, GlueDict


@pytest.mark.parametrize(
    "make_glue, dict_class",
    [
        (Glue, GlueDict),
        (DrtGlue, DrtGlueDict),
        (lambda: DrtGlueReadingCommand()._glue, DrtGlueDict),
    ],
    ids=["Glue", "DrtGlue", "DrtGlueReadingCommand"],
)
def test_default_semtype_file_is_a_resource_name_that_loads(make_glue, dict_class):
    semtype_file = make_glue().semtype_file
    assert "\\" not in semtype_file
    assert len(dict_class(semtype_file)) > 0


def test_default_training_file_is_a_resource_name_that_is_found():
    class TrainingRecorder:
        def train_from_file(self, path):
            self.path = path

    recorder = TrainingRecorder()
    Glue(depparser=recorder).train_depparser()
    assert str(recorder.path).endswith("glue_train.conll")
