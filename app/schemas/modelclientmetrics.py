from typing import List


class TimeToFirstTokenBucket:
    time: float
    number_of_requests: float


class ModelClientMetrics:
    time_to_first_token_seconds_buckets: List[TimeToFirstTokenBucket] = []
