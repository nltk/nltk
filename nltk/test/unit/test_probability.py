from nltk.probability import CrossValidationProbDist, FreqDist


def test_cross_validation_prob_dist():
    freqdists = [FreqDist("aab"), FreqDist("aab"), FreqDist("abc")]
    probdist = CrossValidationProbDist(freqdists, bins=3)

    assert probdist.samples() == {"a", "b", "c"}
    assert probdist.prob("a") > probdist.prob("b") > probdist.prob("c")
    assert probdist.max() == "a"
