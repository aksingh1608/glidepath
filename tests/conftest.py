import pytest

from pipeline import synthetic
from pipeline.data import build_arrivals, clean, load_raw, split_flights


@pytest.fixture(scope="session")
def synthetic_arrivals(tmp_path_factory):
    out = tmp_path_factory.mktemp("syn")
    synthetic.generate(str(out), seed=3)
    pts = split_flights(clean(load_raw(str(out))))
    arrivals, points, stats = build_arrivals(pts)
    return arrivals, points, stats
