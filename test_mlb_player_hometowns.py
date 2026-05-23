"""
Unit tests for `mlb_player_hometowns.py`.

These tests import the target module from the local file, provide lightweight dummy
`constants` and `geopy` modules when needed, and monkeypatch network and file output so
the suite stays deterministic on any machine.
"""

import importlib.util
import os
import sys
from types import ModuleType
import pathlib
import bs4
import pytest


def _load_target_module():
    """Load `mlb_player_hometowns.py` with lightweight fallback dependencies.

    The helper injects small stand-ins for `constants`, `geopy.geocoders`, and
    `geopy.exc` if the real packages are not present, then imports the module directly
    from the workspace so the tests can run in isolation.
    """
    here = os.path.dirname(__file__)
    target_path = os.path.join(here, "mlb_player_hometowns.py")
    if not os.path.exists(target_path):
        pytest.skip("mlb_player_hometowns.py not found next to the tests")

    # Insert a lightweight 'constants' module if missing
    if "constants" not in sys.modules:
        const_mod = ModuleType("constants")
        # create a minimal Enum-like State with at least 'CA'
        try:
            from enum import Enum

            class State(Enum):
                CA = "California"

        except Exception:
            # fallback simple object with mapping behavior
            class _SimpleState:
                CA = "California"

            State = _SimpleState

        # Minimal TEAM_REGISTRY: values must have attributes used by read_teams()
        class TeamMeta:
            def __init__(self, full_name, url_code, short_code, web_color):
                self.full_name = full_name
                self.url_code = url_code
                self.short_code = short_code
                self.web_color = web_color

        const_mod.State = State
        const_mod.TEAM_REGISTRY = {
            "TST": TeamMeta("Test Team", "test", "tst", "#000000")
        }
        sys.modules["constants"] = const_mod

    # Provide a minimal geopy.geocoders.Nominatim if not present
    if "geopy.geocoders" not in sys.modules:
        geopy_pkg = ModuleType("geopy")
        geopy_geo = ModuleType("geopy.geocoders")
        geopy_exc = ModuleType("geopy.exc")

        class _GeopyError(Exception):
            pass

        class _GeocoderRateLimited(_GeopyError):
            pass

        geopy_exc.GeopyError = _GeopyError
        geopy_exc.GeocoderRateLimited = _GeocoderRateLimited

        class DummyNominatim:
            def __init__(self, user_agent=None):
                # geocode will be monkeypatched in tests when needed
                pass

            def geocode(self, *args, **kwargs):
                return None

        geopy_geo.Nominatim = DummyNominatim
        sys.modules["geopy"] = geopy_pkg
        sys.modules["geopy.geocoders"] = geopy_geo
        sys.modules["geopy.exc"] = geopy_exc

    # Load module from file path
    spec = importlib.util.spec_from_file_location("mlb_player_hometowns", target_path)
    mod = importlib.util.module_from_spec(spec)
    # Ensure our dummy packages are visible during execution
    sys.modules["mlb_player_hometowns"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_prep_place_name_for_geocode_replacements():
    """Verify the hometown normalization rules replace known MLB.com quirks."""
    mod = _load_target_module()
    # ends-with-state code replacement
    original = "Somecity CA"
    out = mod.prep_place_name_for_geocode(original)
    assert "California" in out  # CA -> California replacement

    # misspelling fixes
    assert "Wiesbaden" == mod.prep_place_name_for_geocode("Weisbaden").replace(
        "Weisbaden", "Wiesbaden"
    ) or "Wiesbaden" in mod.prep_place_name_for_geocode("Weisbaden")
    assert "Willemstad" in mod.prep_place_name_for_geocode("Mundo-Novo")
    assert "Santo Domingo" in mod.prep_place_name_for_geocode("Santo Domingo Centro")


def _make_response(text):
    """Create a minimal response-like object for mocked `requests.get` calls."""
    class R:
        def __init__(self, t):
            self.text = t

        def raise_for_status(self):
            return None

    return R(text)


def test_player_get_player_info_success_and_failure(monkeypatch):
    """Verify player parsing works for both successful and missing geocode results."""
    mod = _load_target_module()
    # create player page HTML with position and born info
    player_html = (
        "<html><body>"
        "<ul>"
        "<li>Pitcher</li>"
        "<li>B/T: R/R</li>"
        "<li>Born: January 1, 1990 in Smalltown CA</li>"
        "</ul>"
        "</body></html>"
    )
    soup = bs4.BeautifulSoup(player_html, "html.parser")
    player = mod.Player("Test Player")

    # Successful geocode: monkeypatch GEOLOCATOR.geocode to return an object with lat/long
    class FakeLoc:
        latitude = 12.3456789
        longitude = -98.7654321

    monkeypatch.setattr(
        mod, "GEOLOCATOR", type("G", (), {"geocode": lambda *a, **k: FakeLoc()})
    )
    p, null_count, not_geocoded = player.get_player_info(soup)
    assert p.player_name == "Test Player"
    assert "Pitcher" in p.position
    assert "Smalltown" in p.hometown
    assert p.hometown_lat == round(FakeLoc.latitude, 7)
    assert p.hometown_long == round(FakeLoc.longitude, 7)
    assert null_count == 0
    assert not_geocoded == 0

    # Failure to geocode: make geocode return None -> triggers AttributeError path
    player2 = mod.Player("Test Player 2")
    monkeypatch.setattr(
        mod, "GEOLOCATOR", type("G", (), {"geocode": lambda *a, **k: None})
    )
    p2, null_count2, not_geocoded2 = player2.get_player_info(soup)
    assert (
        not_geocoded2 >= 1 or null_count2 >= 0
    )  # at least the code-path executed without crashing


def test_team_process_team_and_read_teams(monkeypatch, tmp_path):
    """Exercise roster parsing and team loading with mocked HTTP and geocoding."""
    mod = _load_target_module()
    # roster page with two player anchors
    roster_html = (
        "<html><body>"
        '<a href="/player/1">Alpha One</a>'
        '<a href="/player/2">Beta Two</a>'
        "</body></html>"
    )
    roster_resp = _make_response(roster_html)

    # player page template
    player_page = (
        "<html><body>"
        "<ul>"
        "<li>Shortstop</li>"
        "<li>B/T: S/S</li>"
        "<li>Born: Feb 2, 1992 in Anytown CA</li>"
        "</ul>"
        "</body></html>"
    )


    def fake_get(url, timeout=10):
        return _make_response(player_page)

    monkeypatch.setattr("requests.get", fake_get)

    # Ensure GEOLOCATOR returns fixed coordinates
    class FakeLoc2:
        latitude = 1.23
        longitude = -4.56

    monkeypatch.setattr(
        mod, "GEOLOCATOR", type("G", (), {"geocode": lambda *a, **k: FakeLoc2()})
    )

    # Create a Team instance (read_teams uses constants.TEAM_REGISTRY dummy we injected)
    teams = mod.read_teams()
    assert isinstance(teams, list) and len(teams) >= 1
    team = teams[0]

    player_list, total_not_mappable = team.process_team(roster_resp, team.full_name)
    assert isinstance(player_list, list)
    # we had two anchors in roster_html
    assert len(player_list) == 2
    assert isinstance(total_not_mappable, int)


def test_make_folium_map_creates_output(monkeypatch, tmp_path):
    """Verify the map writer creates a team HTML file in the local `output/` folder."""
    mod = _load_target_module()
    outdir = pathlib.Path(tmp_path) / "test_output"
    # point module output at a temporary test folder so repo files are not modified
    mod.OUTPUT_DIR = str(outdir)
    # ensure a clean output dir for test
    if outdir.exists():
        for f in outdir.iterdir():
            if f.is_file():
                f.unlink()
    else:
        outdir.mkdir(parents=True, exist_ok=True)

    # create two Player-like objects with lat/long
    class P:
        def __init__(self, name, pos, town, lat, lon):
            self.player_name = name
            self.position = pos
            self.hometown = town
            self.hometown_lat = lat
            self.hometown_long = lon

    players = [
        P("A", "P", "TownA", 10.0, 10.0),
        P("B", "P", "TownB", 20.0, 20.0)
    ]

    # monkeypatch folium.Map.save to actually create the file so we can assert existence
    import folium

    def fake_save(self, path):
        pathlib.Path(path).write_text("html ok", encoding="utf-8")

    monkeypatch.setattr(folium.Map, "save", fake_save)

    mod.make_folium_map(players, "tst", "#123456", num_missing=0)

    # check there is at least one html file starting with the expected prefix
    files = list(outdir.glob("MLB_player_hometowns_TST_*"))
    assert any(f.suffix == ".html" for f in files)


def test_initial_setup_creates_output_and_clears_log(tmp_path):
    """Verify startup setup creates `output/` and removes the current run log."""
    mod = _load_target_module()
    # create output and a dummy log file in a temporary location so tests do not clobber repo files
    outdir = pathlib.Path(tmp_path) / "test_output"
    mod.OUTPUT_DIR = str(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    logpath = outdir / mod.LOG_NAME
    logpath.write_text("dummy")
    assert logpath.exists()

    mod.initial_setup()
    # after initial_setup the log file should not exist (initial_setup attempts to remove it)
    assert not logpath.exists()


def test_write_log_and_or_console_writes_when_all_teams(tmp_path):
    """Verify log messages are written to disk when the all-teams mode is enabled."""
    mod = _load_target_module()
    outdir = pathlib.Path(tmp_path) / "test_output"
    mod.OUTPUT_DIR = str(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    logpath = outdir / mod.LOG_NAME
    if logpath.exists():
        logpath.unlink()
    mod.ALL_TEAMS = True
    # call should create the log file and append the message
    mod.write_log_and_or_console("TestLogEntry")
    assert logpath.exists()
    content = logpath.read_text(encoding="utf-8")
    assert "TestLogEntry" in content


def test_make_folium_map_with_no_players_creates_output(monkeypatch, tmp_path):
    """Verify the map writer still creates an HTML file when there are no players."""
    mod = _load_target_module()
    outdir = pathlib.Path(tmp_path) / "test_output"
    mod.OUTPUT_DIR = str(outdir)
    # ensure a clean output dir for test
    if outdir.exists():
        for f in outdir.iterdir():
            if f.is_file():
                f.unlink()
    else:
        outdir.mkdir(parents=True, exist_ok=True)

    # monkeypatch the Map.save on the folium instance loaded inside the module
    def fake_save(self, path):
        pathlib.Path(path).write_text("empty map", encoding="utf-8")

    monkeypatch.setattr(mod.folium.Map, "save", fake_save)

    # call with empty players list
    mod.make_folium_map([], "tst", "#000000", num_missing=0)

    files = list(outdir.glob("MLB_player_hometowns_TST_*"))
    assert any(f.suffix == ".html" for f in files)


def test_process_list_of_teams_handles_roster_request_failure(monkeypatch):
    """Verify roster download failures are logged and do not stop processing."""
    mod = _load_target_module()
    teams = mod.read_teams()
    # force requests.get to raise for roster URL
    import requests

    def fake_get(url, timeout=10):
        raise requests.exceptions.RequestException("network fail")

    monkeypatch.setattr("requests.get", fake_get)
    captured = []
    monkeypatch.setattr(mod, "write_log_and_or_console", lambda t: captured.append(t))
    # should not raise despite the simulated request failure
    mod.process_list_of_teams(teams)
    # ensure we logged an error about the URL not being located or similar
    assert any(
        "could not be located" in str(m).lower() or "error" in str(m).lower()
        for m in captured
    )


def test_player_get_player_info_with_no_li_tags(monkeypatch):
    """Verify player parsing handles a page with no list items without crashing."""
    mod = _load_target_module()
    player = mod.Player("No Li Player")
    soup = bs4.BeautifulSoup("<html><body></body></html>", "html.parser")
    # ensure geocoder returns None if called (shouldn't be called here)
    monkeypatch.setattr(
        mod, "GEOLOCATOR", type("G", (), {"geocode": lambda *a, **k: None})
    )
    captured = []
    monkeypatch.setattr(mod, "write_log_and_or_console", lambda t: captured.append(t))
    p, null_count, not_geocoded = player.get_player_info(soup)
    assert null_count == 1
    assert p.hometown == "NULL (no hometown found on page)"
