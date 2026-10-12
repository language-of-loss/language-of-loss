import hashlib

NAMESPACE = "grief-hi-en/annotation-id/v1|"


def annotation_id(record_id, taken=None):
    h = hashlib.sha256((NAMESPACE + record_id).encode("utf-8")).hexdigest()
    aid = "GRF-" + h[:10]
    if taken is not None and aid in taken and taken[aid] != record_id:
        aid = "GRF-" + h[:16]
        if aid in taken and taken[aid] != record_id:
            raise ValueError(f"annotation ID collision that 16 hex chars cannot resolve: {record_id}")
    return aid
