import sys
import os
import re
import csv
from datetime import datetime
import requests
import bs4
from geopy.geocoders import Nominatim
import geocoder
import gmplot
import simplekml
from mlb_player_hometowns_enums import US_STATES


# TODO: use f-strings for string formatting
# TODO: when doing all teams, create subfolder within "output" folder for them
# TODO: more/better exception handling, and other pylint-requested stuff
# TODO: get rid of CSV; create list of dicts for teams, in mlb_player_hometowns_enums.py
# TODO: fix issue of some characters ("enye", etc) not showing correctly in tooltips on html maps
# TODO: unit tests
# TODO: implement class(es)


START_TIME = datetime.now()
YYYY_MM_DD = "{:04d}".format(START_TIME.year) + "_{:02d}".format(START_TIME.month) + \
             "_{:02d}".format(START_TIME.day)
LOG_NAME = "MLB_player_hometowns_" + YYYY_MM_DD + "_{:02d}".format(START_TIME.hour) + \
           "{:02d}".format(START_TIME.minute) + ".txt"
GEOLOCATOR = Nominatim(user_agent="mlb_player_hometowns_app")
ALL_TEAMS = False


def initial_setup():
    # Create 'output' sub folder if it doesn't exist
    try:
        os.mkdir('output')
    except OSError:
        pass
    # Delete log if already exists (used for scenario of script run/cancelled/rerun in same minute)
    try:
        os.remove(os.path.join('output', LOG_NAME))
    except OSError:
        pass


def prompt_user():
    global ALL_TEAMS
    teams = get_team_info()
    while True:
        print("\nWhich team would you like to see a map of the players' home towns?\n")

        for team in teams:
            print('{:<25s}{:<20s}'.format(team["fullname"], team["short_code"]))
        user_input = \
            input("\nEnter the 2-3 letter team code shown above, OR, for maps of all 30 teams "
                  "simply hit [Enter] ")
        if user_input == "":
            ALL_TEAMS = True
            return teams  # (all teams)
        for team in teams:
            if team["short_code"] == user_input:
                team = [team]
                return team

        print("ERROR:  Invalid entry; please enter one of the codes above or [Enter] for maps of "
              "all 30 teams.")


def get_team_info():
    """
    Reads CSV of team info (team names, codes, and colors for map markers) into a list of dicts
    """
    teams = []
    try:
        with open("mlb_teams.csv", newline='', encoding='utf-8-sig') as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                team = {"fullname": row[0], "url_code": row[1], "short_code": row[2],
                        "webcolor": row[3]}
                teams.append(team)
            return teams
    except:
        write_log_and_or_console("ERROR:  There was a problem reading mlb_teams.csv. Check the "
                                 "file and try again.")
        sys.exit()


def display_team_not_found_message(single_team, teams):
    write_log_and_or_console("ERROR:  Team name or code \"" + single_team + "\" not found.")
    write_log_and_or_console("Use team name (just the name, without the city) or one of these 2-3 "
                             "letter team codes.")
    write_log_and_or_console("For two word names, put in quotes (\"red sox\").\n")
    for team in teams:
        write_log_and_or_console('{:<25s}{:<20s}'.format(team["fullname"], team["short_code"]))


def process_list_of_teams(teams):
    for team in teams:
        player_pages_not_reached = 0
        players_not_geocoded = 0
        team_url = "https://www.mlb.com/" + team["url_code"] + "/roster/"
        write_log_and_or_console("----------------------------------------------")
        write_log_and_or_console("*****  " + team["fullname"].upper() + " *****")
        write_log_and_or_console("----------------------------------------------")
        try:
            res = requests.get(team_url)  # "downloads" the web page; returns a response object
            res.raise_for_status()  # checks to see if download worked; raises exception if fail
        except requests.exceptions.RequestException:
            write_log_and_or_console("ERROR:  URL " + team_url + " could not be located.\n")
            continue
        player_list, total_players_not_mappable = process_team(res, team["fullname"])
        make_gmplot_and_kml(player_list, team["url_code"], team["webcolor"],
                            total_players_not_mappable)


def process_team(res, team_name):

    player_pages_not_reached = 0
    players_with_null_hometown = 0
    players_not_geocoded = 0

    soup = bs4.BeautifulSoup(res.text, "html.parser")
    view_player_anchors = soup.find_all('a', href=re.compile('^/player/'))
    player_list = []
    for anch in view_player_anchors:
        player = {"name": anch.text}
        url = "https://www.mlb.com" + anch.get("href")
        # go to each player page
        try:
            res = requests.get(url)
            res.raise_for_status()
            soup = bs4.BeautifulSoup(res.text, "html.parser")
            player, null_hometown, not_geocoded = get_player_info(
                player, soup)
            player_list.append(player)
        except requests.exceptions.RequestException as err:
            write_log_and_or_console("ERROR:  " + player["name"] + "\'s page could not be located.")
            write_log_and_or_console(str(err))
            write_log_and_or_console(
                "----------------------------------------------------------------------------")
            player_pages_not_reached += 1
            continue
        players_with_null_hometown += null_hometown
        players_not_geocoded += not_geocoded

        write_log_and_or_console(
            "----------------------------------------------------------------------------")

    total_players_not_mappable = player_pages_not_reached + players_with_null_hometown + \
                                 players_not_geocoded

    write_log_and_or_console("Number of players in " + team_name + " roster: ..... " +
                             str(len(view_player_anchors)))
    write_log_and_or_console("Number whose page not available, or whose hometown not available, "
                             "or who didn't geocode: ..... " +
                             str(total_players_not_mappable) + "\n")
    return player_list, total_players_not_mappable


def get_player_info(player, soup):
    players_with_null_hometowns = 0
    players_not_geocoded = 0
    li_tags = soup.find_all("li")  # TODO: build regex into this; might improve perf

    # ---------------  get player position, hometown, and lat/long of hometown ---------------
    # Need to enter default values, for when player's page loads but there's no actual content
    player["position"] = "NULL (no position found on page)"
    player["hometown"] = "\n\tNULL (no hometown found on page)"
    player["hometown_lat"] = -1
    player["hometown_long"] = -1

    for tag in li_tags:

        if str(tag).find("B/T: ") > -1:
            prior_tag = li_tags[li_tags.index(tag) - 1]  # (need the one right before "B/T:" tag)
            player["position"] = str(prior_tag)[4:str(prior_tag).find("</l")]

        if str(tag).find("Born:") > -1:

            tag_string = str(tag)
            player["hometown"] = \
                (tag_string[tag_string.find(" in ") + 4:tag_string.find("</li>")]).strip()
            # TODO: improve ^^^
            player["hometown"] = prep_place_name_for_geocode(player["hometown"])
            try:
                location = GEOLOCATOR.geocode(player["hometown"], timeout=10)
                player["hometown_lat"] = round(location.latitude, 7)
                player["hometown_long"] = round(location.longitude, 7)

                # location = geocoder.arcgis(player["hometown"])
                # player["hometown_lat"] = round(location.lat, 7)
                # player["hometown_long"] = round(location.lng, 7)

            except:
                players_not_geocoded += 1
                continue

    if player["hometown"] == "\n\tNULL (no hometown found on page)":
        players_with_null_hometowns += 1

    write_log_and_or_console("NAME & POSITION:  " + player["name"] + " (" +
                             player["position"] + ")")
    home_town_output = "HOME TOWN:        " + player["hometown"]
    if player["hometown_lat"] != -1 and player["hometown_lat"] != -1:
        home_town_output += " (" + str(player["hometown_lat"]) + ", " + \
                            str(player["hometown_long"]) + ")"
    write_log_and_or_console(home_town_output)

    if (player["hometown_lat"] == -1 and player["hometown_lat"] == -1) and \
        player["hometown"] != "\n\tNULL (no hometown found on page)":
        write_log_and_or_console("\tERROR:  Cannot geocode.")
    return player, players_with_null_hometowns, players_not_geocoded


def prep_place_name_for_geocode(player_hometown):
    # Most players' 2-letter state codes worked but for some, "CA" ended up in Canada, and there
    # were a few other random similar errors, so:
    if player_hometown[-2:] in US_STATES.keys():
        code = player_hometown[-2:]
        player_hometown = player_hometown.replace(code, US_STATES.get(code))
    # TODO: maybe check to see if these are still issues (created 2017 or 2018 I think):
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


def make_gmplot_and_kml(players, team_code, team_color, num_missing):
    kml = simplekml.Kml()
    gmap = gmplot.GoogleMapPlotter(19, -111, 3)  # (Lat/Long for center of map;  3 for zoom level)
    # Reason for 19 N, 111 W: to have North/South America in the center of the map, since most MLB
    # players from those two continents
    gmap.coloricon = "http://www.googlemapsmarkers.com/v1/%s/"
    # ^^^ (https://github.com/vgm64/gmplot/issues/18, comment from 12/5/16)

    for player in players:
        if player["hometown_lat"] != -1 and player["hometown_long"] != -1:

            # For KML file, for loading in Google Earth:
            pnt = kml.newpoint(name=player["name"] + " (" + player["position"] + ") - " +
                               player["hometown"], coords=[(player["hometown_long"],
                                                            player["hometown_lat"])])
            pnt.style.iconstyle.scale = 3
            # TODO: this next line doesn't always work, need to improve this part of system
            pnt.style.iconstyle.icon.href = \
                "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png"
            # ^^^ taken from http://kml4earth.appspot.com/icons.html

            # For gmplot HTML file:
            gmap.marker(player["hometown_lat"], player["hometown_long"], team_color, None,
                        player["name"] + " (" + player["position"] + ") - " + player["hometown"])

    filename = "MLB_player_hometowns_" + team_code.upper() + "_" + YYYY_MM_DD
    if num_missing > 0:
        filename = filename + "__" + str(num_missing) + "_missing"

    kml.save(os.path.expanduser(os.path.join('output', (filename + ".kml"))))
    # TODO: figure how why the KML needs this os.path.expanduser stuff ^^^ but the HTML doesn't
    gmap.draw(os.path.join('output', (filename + ".html")))


def write_log_and_or_console(text):
    print(text)
    if ALL_TEAMS:
        with open(os.path.join('output', LOG_NAME), "a") as text_file:
            text_file.write(text + "\n")


if __name__ == "__main__":
    initial_setup()
    process_list_of_teams(prompt_user())
    write_log_and_or_console("Total time for script to run, in H:M:S....." +
                             str(datetime.now() - START_TIME)[:-3])
