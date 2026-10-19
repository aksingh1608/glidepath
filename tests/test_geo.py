from pipeline.data import haversine_nm


def test_one_degree_of_latitude_is_about_60_nm():
    d = haversine_nm(50.0, 8.57, 51.0, 8.57)
    assert abs(d - 60.0) < 0.1


def test_zero_distance():
    assert haversine_nm(50.0333, 8.5706, 50.0333, 8.5706) == 0
