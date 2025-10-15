"""
MLB Player Hometowns Mapping Tool

This module scrapes MLB team rosters from mlb.com, extracts players' information, geocodes their 
home town locations using Nominatim, and generates both HTML (Google Maps) and KML (Google Earth)
visualization files showing the geographical distribution of players' hometowns. Users can 
generate maps for individual teams or all MLB teams at once.
"""

# pylint: disable=import-error

import os
import re
from datetime import datetime
import requests
import bs4
from geopy.geocoders import Nominatim
import folium
from constants import State, TEAM_REGISTRY


START_TIME = datetime.now()
LOG_NAME = f"MLB_player_hometowns_{START_TIME.strftime('%Y%m%d_%H%M')}.txt"
GEOLOCATOR = Nominatim(user_agent="mlb_player_hometowns_app")
ALL_TEAMS = False


class Team:
    """
    Represents an MLB team with associated data and methods for processing roster information.

    Stores team identifiers (full name, URL code, short code) and display properties (web color).
    Provides functionality to process team rosters and extract player information from MLB.com.
    """

    player_pages_not_reached = 0
    players_not_geocoded = 0

    def __init__(self, fullname, url_code, short_code, web_color):
        """
        Initialize a Team object with team identifiers and display properties.
        """
        self.full_name = fullname
        self.url_code = url_code
        self.short_code = short_code
        self.web_color = web_color

    def process_team(self, res, team_name):
        """
        Process team roster from MLB.com response and extract player information.
        """

        player_pages_not_reached = 0
        players_with_null_hometown = 0
        players_not_geocoded = 0

        soup = bs4.BeautifulSoup(res.text, "html.parser")
        player_anchors = soup.find_all("a", href=re.compile("^/player/"))
        player_list = []


        for anchor in player_anchors:
            player = Player(anchor.text)
            url = "https://www.mlb.com" + anchor.get("href")
            # go to each player page
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                soup = bs4.BeautifulSoup(res.text, "html.parser")
                player, null_hometown, not_geocoded = player.get_player_info(soup)
                player_list.append(player)
            except requests.exceptions.RequestException as err:
                write_log_and_or_console(
                    f"ERROR:  {player.player_name}'s page could not be located."
                )
                write_log_and_or_console(str(err))
                write_log_and_or_console(
                    "----------------------------------------------------------------------------"
                )
                player_pages_not_reached += 1
                continue
            players_with_null_hometown += null_hometown
            players_not_geocoded += not_geocoded

            write_log_and_or_console(
                "----------------------------------------------------------------------------"
            )

        total_players_not_mappable = (
            player_pages_not_reached + players_with_null_hometown + players_not_geocoded
        )

        write_log_and_or_console(
            f"Number of players in {team_name} roster: ..... {str(len(player_anchors))}"
        )
        write_log_and_or_console(
            f"Number whose page not available, or whose hometown not available, "
            f"or who didn't geocode: ..... {str(total_players_not_mappable)}\n"
        )
        return player_list, total_players_not_mappable


class Player:
    """
    Represents an MLB player with associated biographical and location data.

    Stores player information including name, position, hometown, and geocoded coordinates.
    Provides methods to extract and process player information from MLB.com player pages.
    """

    def __init__(self, player_name):
        """
        Initialize a Player object with name and default values.
        """
        self.player_name = player_name
        self.position = "NULL (no position found on page)"
        self.hometown = "NULL (no hometown found on page)"
        self.hometown_lat = -1
        self.hometown_long = -1

    def get_player_info(self, soup):
        """
        Extract player information from their MLB.com page and attempt to geocode hometown.
        """
        players_with_null_hometowns = 0
        players_not_geocoded = 0
        li_tags = soup.find_all("li")

        for tag in li_tags:
            if str(tag).find("B/T: ") > -1:
                prior_tag = li_tags[
                    li_tags.index(tag) - 1
                ]  # (need the one right before "B/T:" tag)
                self.position = str(prior_tag)[4 : str(prior_tag).find("</l")]

            if str(tag).find("Born:") > -1:

                tag_string = str(tag)
                self.hometown = (
                    tag_string[tag_string.find(" in ") + 4 : tag_string.find("</li>")]
                ).strip()
                self.hometown = prep_place_name_for_geocode(self.hometown)
                try:
                    location = GEOLOCATOR.geocode(self.hometown, timeout=10)
                    self.hometown_lat = round(location.latitude, 7)
                    self.hometown_long = round(location.longitude, 7)

                except (AttributeError, ValueError, TypeError) as e:
                    # AttributeError: location is None (no geocoding result)
                    # ValueError: invalid coordinate values
                    # TypeError: unexpected data type issues
                    write_log_and_or_console(
                        f"ERROR: Failed to geocode {self.hometown} for {self.player_name}: {e}"
                    )
                    players_not_geocoded += 1
                    continue

        if self.hometown == "NULL (no hometown found on page)":
            players_with_null_hometowns += 1

        write_log_and_or_console(
            f"NAME & POSITION:  {self.player_name} ({self.position})"
        )
        home_town_output = f"HOME TOWN:        {self.hometown}"
        if self.hometown_lat != -1 and self.hometown_long != -1:
            home_town_output += (
                " (" + str(self.hometown_lat) + ", " + str(self.hometown_long) + ")"
            )
        write_log_and_or_console(home_town_output)

        if (
            self.hometown_lat == -1 and self.hometown_lat == -1
        ) and self.hometown != "NULL (no hometown found on page)":
            write_log_and_or_console("ERROR:  Cannot geocode.")
        return self, players_with_null_hometowns, players_not_geocoded


def initial_setup():
    """
    Create output directory if needed and clean up any existing log files.
    """
    # Create 'output' sub folder if it doesn't exist
    try:
        os.mkdir("output")
    except OSError:
        pass
    # Delete log if already exists (used for scenario of script run/cancelled/rerun in same minute)
    try:
        os.remove(os.path.join("output", LOG_NAME))
    except OSError:
        pass


def prompt_user():
    """
    Display team options and get user selection for processing.
    """
    global ALL_TEAMS
    teams = read_teams()
    while True:
        print("\nPick an MLB team to see a map of its players' home towns: \n")

        for team in teams:
            print(f"{team.full_name:<25}{team.short_code}")
        user_input = input(
            "\nEnter the 2-3 letter team code shown above, OR, for maps of all 30 teams "
            "simply hit [Enter] "
        )
        if user_input == "":
            ALL_TEAMS = True
            return teams  # (all teams)
        for team in teams:
            if team.short_code == user_input.lower():
                team = [team]
                return team

        print(
            "ERROR:  Invalid entry; please enter one of the codes above or [Enter] for maps of "
            "all 30 teams."
        )


def process_list_of_teams(teams):
    """
    Called by if-name-main, which passes teams, a list of Team objects.
    For each Team, it calls process_team to get list of players.
    Then calls the method to create gmplot and kml files.
    """

    for team in teams:

        team_url = f"https://www.mlb.com/{team.url_code}/roster/"
        write_log_and_or_console("----------------------------------------------")
        write_log_and_or_console(f"***** {team.full_name.upper()} *****")
        write_log_and_or_console("----------------------------------------------")
        try:
            res = requests.get(
                team_url, timeout=10
            )  # "downloads" the web page; returns a response object
            res.raise_for_status()  # checks to see if download worked; raises exception if fail
        except requests.exceptions.RequestException:
            write_log_and_or_console(f"ERROR:  URL {team_url} could not be located.\n")
            continue
        player_list, total_players_not_mappable = team.process_team(res, team.full_name)

        make_folium_map(
            player_list, team.url_code, team.web_color, total_players_not_mappable
        )


def read_teams():
    return [
        Team(meta.full_name, meta.url_code, meta.short_code, meta.web_color)
        for meta in TEAM_REGISTRY.values()
    ]


def prep_place_name_for_geocode(player_hometown):
    """
    Clean and standardize hometown strings to improve geocoding success.
    """
    # Most players' 2-letter US state codes worked but for some, "CA" ended up in Canada,
    # and there were a few other random errors, so, replace 2-letter state code with name.
    names = [member.name for member in State]
    if player_hometown[-2:] in names:
        code = player_hometown[-2:]
        player_hometown = player_hometown.replace(code, State[code].value)
    # MLB.com misspelled Wiesbaden for one player's bio
    if player_hometown.find("Weisbaden") != -1:
        player_hometown = player_hometown.replace("Weisbaden", "Wiesbaden")
    # Google search didn't turn up much for Mundo-Novo; however, Andrelton Simmons's Wiki page
    # indicates it's a neighborhood of Willemstad.
    if player_hometown.find("Mundo-Novo") != -1:
        player_hometown = player_hometown.replace("Mundo-Novo", "Willemstad")
    # Centro is unneeded/redundant; not sure why some MLB.com bios for players from there have it
    if player_hometown.find("Santo Domingo Centro") != -1:
        player_hometown = player_hometown.replace(" Centro", "")

    return player_hometown



def make_folium_map(players, team_code, team_color_hex, num_missing):
    """
    Generate a Leaflet (Folium) HTML map of player hometowns for one team.
    Saves a single standalone .html into ./output
    """

    # --- Basemap switcher (OSM + CartoDB Positron + CartoDB Dark) ---
    m = folium.Map(location=[19, -111], zoom_start=3, tiles=None, prefer_canvas=True)

    # OpenStreetMap (default)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        control=True,
        show=True,  # make this the default visible basemap
    ).add_to(m)

    # CartoDB Positron (light gray)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors © CARTO",
        name="CartoDB Positron",
        subdomains=["a", "b", "c", "d"],
        control=True,
        show=False,
    ).add_to(m)

    # CartoDB Dark Matter
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors © CARTO",
        name="CartoDB Dark Matter",
        subdomains=["a", "b", "c", "d"],
        control=True,
        show=False,
    ).add_to(m)

    # # Layer control (upper-right toggle)
    # folium.LayerControl(position="topright").add_to(m)

    for p in players:
        if (
            getattr(p, "hometown_lat", -1) != -1
            and getattr(p, "hometown_long", -1) != -1
        ):
            # popup_html = folium.Popup(f"<b>{p.player_name}</b> ({p.position}) -- {p.hometown}"
            #     f"<br>TO DO: eventually add ERA for pitchers, batting avg for others, etc",
            #     max_width=400
            # )

            # Folium expects color names for CircleMarker; for strict hex, we set fill=True.
            folium.CircleMarker(
                location=[p.hometown_lat, p.hometown_long],
                radius=6,
                color="black",
                weight=1,
                fill=True,
                fill_opacity=0.9,
                fill_color=team_color_hex,
                # popup=popup_html,
                tooltip=folium.Tooltip(
                    f"<div style='font-size:12px'><b>{p.player_name}</b> ({p.position}) -- "
                    f"{p.hometown}</div>"
                ),
            ).add_to(m)

    # Optional legend-ish control
    folium.LayerControl().add_to(m)

    filename = (
        f"MLB_player_hometowns_{team_code.upper()}_{START_TIME.strftime('%Y%m%d_%H%M')}"
    )
    if num_missing > 0:
        filename = f"{filename}__{str(num_missing)}_missing"

    m.save(os.path.join("output", filename + ".html"))


def write_log_and_or_console(text):
    """
    Output text to console and optionally to log file when processing all teams.
    """
    print(text)
    if ALL_TEAMS:
        with open(os.path.join("output", LOG_NAME), "a", encoding="utf-8") as text_file:
            text_file.write(text + "\n")


if __name__ == "__main__":
    initial_setup()
    process_list_of_teams(prompt_user())
    write_log_and_or_console(
        f"Total time for script to run, in H:M:S.....{str(datetime.now() - START_TIME)[:-3]}"
    )
