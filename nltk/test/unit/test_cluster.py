import random

import pytest

from nltk.cluster import EMClusterer, GAAClusterer, KMeansClusterer, euclidean_distance

np = pytest.importorskip("numpy")


@pytest.mark.parametrize("normalise", [False, True])
@pytest.mark.parametrize("svd_dimensions", [None, 1, 2])
@pytest.mark.parametrize("assign_clusters", [False, True])
@pytest.mark.parametrize("algorithm", ["kmeans", "em"])
def test_cluster_assignments_after_preprocessing(
    normalise, svd_dimensions, assign_clusters, algorithm
):
    vectors = np.array(
        [[3.0, 1.0, 0.0], [4.0, 1.0, 0.0], [-3.0, -1.0, 0.0], [-4.0, -1.0, 0.0]]
    )
    original_vectors = vectors.copy()
    if algorithm == "kmeans":
        clusterer = KMeansClusterer(
            2,
            euclidean_distance,
            normalise=normalise,
            svd_dimensions=svd_dimensions,
            rng=random.Random(0),
        )
    else:
        means = np.zeros((2, svd_dimensions or vectors.shape[1]))
        means[:, 0] = [1.0, -1.0]
        clusterer = EMClusterer(
            means, normalise=normalise, svd_dimensions=svd_dimensions
        )

    assignments = clusterer.cluster(vectors, assign_clusters=assign_clusters)
    classifications = [clusterer.classify(vector) for vector in vectors]

    assert classifications[0] == classifications[1]
    assert classifications[2] == classifications[3]
    assert classifications[0] != classifications[2]
    if assign_clusters:
        assert assignments == classifications
    else:
        assert assignments is None
    np.testing.assert_array_equal(vectors, original_vectors)


@pytest.mark.parametrize("normalise", [False, True])
def test_gaac_cluster_assignments(normalise):
    vectors = np.array([[3.0, 1.0], [4.0, 1.0], [-3.0, -1.0], [-4.0, -1.0]])
    clusterer = GAAClusterer(2, normalise=normalise)

    assignments = clusterer.cluster(vectors, assign_clusters=True)

    assert assignments == [clusterer.classify(vector) for vector in vectors]
    assert assignments[0] == assignments[1]
    assert assignments[2] == assignments[3]
    assert assignments[0] != assignments[2]
