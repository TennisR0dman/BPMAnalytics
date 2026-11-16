"""Cohort rules: primary artist, dedupe, popularity floor, and the hip-hop exclusion."""

import pandas as pd

from bpm_analytics.cohorts import build_analysis, prepare_catalog, primary_artist


def _row(**overrides):
    base = {
        "track_id": "t0",
        "artists": "Someone",
        "album_name": "Album",
        "track_name": "Song",
        "popularity": 80,
        "duration_ms": 200000,
        "explicit": False,
        "danceability": 0.7,
        "energy": 0.6,
        "loudness": -6.0,
        "speechiness": 0.1,
        "acousticness": 0.2,
        "valence": 0.5,
        "tempo": 100.0,
        "time_signature": 4,
        "track_genre": "pop",
    }
    base.update(overrides)
    return base


def _lookup():
    return pd.DataFrame(
        [
            {"artist_name": "Burna Boy", "country": "Nigeria", "region": "West Africa", "scene": "afrobeats"},
            {"artist_name": "Wizkid", "country": "Nigeria", "region": "West Africa", "scene": "afrobeats"},
            {"artist_name": "Rema", "country": "Nigeria", "region": "West Africa", "scene": "afrobeats"},
        ]
    )


def _analysis():
    raw = pd.DataFrame(
        [
            _row(track_id="b1", artists="Burna Boy", track_name="Last Last", popularity=80, tempo=100, track_genre="dancehall"),
            _row(track_id="b1", artists="Burna Boy", track_name="Last Last", popularity=70, tempo=100, track_genre="hip-hop"),
            _row(track_id="b-low", artists="Burna Boy", track_name="Deep Cut", popularity=30, tempo=110, track_genre="dancehall"),
            _row(track_id="b-zero", artists="Burna Boy", track_name="Broken Tempo", popularity=90, tempo=0, track_genre="dancehall"),
            _row(track_id="b-meter", artists="Burna Boy", track_name="Broken Meter", popularity=90, tempo=100, time_signature=1),
            _row(track_id="w1", artists="Wizkid", track_name="Essence", popularity=70, tempo=104, track_genre="dancehall"),
            _row(track_id="w2", artists="Wizkid", track_name="Essence", popularity=60, tempo=104, track_genre="pop"),
            _row(track_id="r1", artists="Rema", track_name="Calm Down", popularity=92, tempo=50, track_genre="pop"),
            _row(track_id="d1", artists="Drake;Burna Boy", track_name="Feature", popularity=90, tempo=160, track_genre="hip-hop"),
            _row(track_id="c1", artists="Calle 13", track_name="Atrévete", popularity=75, tempo=88, track_genre="afrobeat"),
        ]
    )
    catalog = prepare_catalog(raw)
    lookup = _lookup()
    lookup["name_key"] = lookup["artist_name"].str.casefold()
    return build_analysis(catalog, lookup, top_n=1, min_popularity=40)


def test_primary_artist_is_the_first_credit():
    assert primary_artist("Drake;Burna Boy") == "Drake"
    assert primary_artist("  Burna Boy ; Wizkid") == "Burna Boy"
    assert primary_artist(None) is None
    assert primary_artist("   ") is None


def test_featured_artist_does_not_enter_the_africa_cohort():
    analysis, _funnel = _analysis()
    feature = analysis[analysis["track_id"] == "d1"]
    assert len(feature) == 1
    assert feature.iloc[0]["cohort_id"] == "us_hiphop_genre"
    assert feature.iloc[0]["primary_artist"] == "Drake"
    assert feature.iloc[0]["tempo_corrected"] == pytest_approx(80)
    assert feature.iloc[0]["octave_direction"] == "halved"


def pytest_approx(value):
    from pytest import approx

    return approx(value)


def test_same_track_is_not_in_both_cohorts_and_label_noise_stays_out():
    analysis, funnel = _analysis()
    assert set(analysis.loc[analysis["cohort_id"] == "africa_popular", "track_id"]).isdisjoint(
        set(analysis.loc[analysis["cohort_id"] == "us_hiphop_genre", "track_id"])
    )
    assert "c1" not in set(analysis["track_id"])
    assert "b-low" not in set(analysis["track_id"])
    assert "b-zero" not in set(analysis["track_id"])
    assert "b-meter" not in set(analysis["track_id"])
    assert funnel["africa_eligible"] == 3


def test_title_dedupe_and_top_flag():
    analysis, _funnel = _analysis()
    essence = analysis[analysis["title_key"] == "essence"] if "title_key" in analysis.columns else analysis[analysis["track_name"] == "Essence"]
    essence = analysis[analysis["track_name"] == "Essence"]
    assert len(essence) == 1
    assert essence.iloc[0]["popularity"] == 70
    africa_top = analysis[(analysis["cohort_id"] == "africa_popular") & (analysis["is_top100"] == 1)]
    assert list(africa_top["primary_artist"]) == ["Rema"]
    rema = africa_top.iloc[0]
    assert rema["tempo_corrected"] == pytest_approx(100)
    assert rema["octave_direction"] == "doubled"
    assert rema["country"] == "Nigeria"


def test_duplicate_lookup_names_are_rejected(tmp_path):
    from bpm_analytics.cohorts import load_lookup

    path = tmp_path / "lookup.csv"
    path.write_text(
        "artist_name,country,region,scene\nRema,Nigeria,West Africa,afrobeats\nrema,Nigeria,West Africa,afrobeats\n",
        encoding="utf-8",
    )
    try:
        load_lookup(path)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("duplicate artist keys should fail")
