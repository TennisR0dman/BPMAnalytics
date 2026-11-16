"""Chart parsers and Deezer match scores. No network."""

from bpm_analytics.charts import parse_billboard_rb_hiphop, parse_kworb_daily
from bpm_analytics.deezer_match import pick_match

KW_HTML = """
<span class="pagetitle">Spotify Daily Chart - Nigeria - 2026/11/14 |</span>
<table><tbody>
<tr><td class="np">1</td><td class="np">=</td>
<td><div><a href="../artist/abc.html">Peruzzi</a> - <a href="../track/3FCIOA44iYIDsjDNeXthc1.html">INFERNO</a> (w/ <a href="../artist/z.html">Zlatan</a>)</div></td>
</tr>
<tr><td class="np">51</td><td class="np">+1</td>
<td><div><a href="../artist/x.html">Someone</a> - <a href="../track/zzzz.html">Too Low</a></div></td>
</tr>
</tbody></table>
"""

BB_HTML = """
<span>Week of November 14, 2026</span>
<ul data-detail-target="1">
<h3 id="title-of-a-story">I Just Might</h3>
<span class="c-label">Bruno Mars</span>
</ul>
<ul data-detail-target="2">
<h3 id="title-of-a-story">What You Need</h3>
<span class="c-label">Don Toliver</span>
</ul>
""" + "".join(
    f'<ul data-detail-target="{pos}"><h3 id="title-of-a-story">Song {pos}</h3><span>Artist {pos}</span></ul>'
    for pos in range(3, 12)
)


def test_kworb_keeps_the_lead_artist_and_the_top_50_cut():
    rows = parse_kworb_daily(KW_HTML, "Nigeria", "https://kworb.net/spotify/country/ng_daily.html", "2026-11-16", top_n=50)
    assert len(rows) == 1
    assert rows[0]["primary_artist"] == "Peruzzi"
    assert rows[0]["track_name"] == "INFERNO"
    assert rows[0]["spotify_track_id"] == "3FCIOA44iYIDsjDNeXthc1"
    assert rows[0]["chart_date"] == "2026-11-14"
    assert rows[0]["chart_position"] == 1


def test_billboard_reads_week_title_and_artist():
    rows = parse_billboard_rb_hiphop(BB_HTML, "https://www.billboard.com/charts/r-b-hip-hop-songs/", "2026-11-16")
    assert rows[0]["track_name"] == "I Just Might"
    assert rows[0]["primary_artist"] == "Bruno Mars"
    assert rows[0]["chart_date"] == "November 14, 2026"
    assert rows[1]["chart_position"] == 2
    assert len(rows) == 11


def test_match_accepts_a_close_title_and_rejects_a_different_song():
    hits = [
        {"id": 10, "title": "Inferno", "title_short": "Inferno", "artist": {"name": "Peruzzi"}, "preview": "http://example.test/a.mp3"},
        {"id": 11, "title": "Calm Down", "title_short": "Calm Down", "artist": {"name": "Rema"}, "preview": "http://example.test/b.mp3"},
    ]
    chosen = pick_match("Peruzzi", "INFERNO", hits)
    assert chosen is not None
    assert chosen["deezer_id"] == 10
    assert pick_match("Peruzzi", "INFERNO", hits[1:]) is None


def test_match_tolerates_a_featured_credit_on_the_service_side():
    hits = [
        {
            "id": 22,
            "title": "Essence (feat. Tems)",
            "title_short": "Essence",
            "artist": {"name": "Wizkid"},
            "preview": "http://example.test/c.mp3",
        }
    ]
    chosen = pick_match("Wizkid", "Essence", hits)
    assert chosen is not None
    assert chosen["deezer_id"] == 22
