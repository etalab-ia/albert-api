import difflib


def assert_snapshot_almost_equal(actual, expected_snapshot, threshold=0.90):
    """
    Assert that the actual value is almost equal to the expected snapshot.

    :param actual: The actual value returned by the OCR.
    :param expected_snapshot: The expected snapshot value.
    :param threshold: The similarity threshold (default: 0.99).
    :raises AssertionError: If the similarity is below the threshold.
    """
    similarity = difflib.SequenceMatcher(None, actual, expected_snapshot).ratio()
    if similarity < threshold:
        raise AssertionError(
            f"Snapshot mismatch: Similarity {similarity:.2%} is below the threshold of {threshold:.2%}.\n"
            f"Actual: {actual}\n"
            f"Expected: {expected_snapshot}"
        )
