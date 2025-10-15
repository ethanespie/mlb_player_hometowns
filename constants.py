from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamSpec:
    full_name: str
    url_code: str
    short_code: str
    webcolor: str
    readable_color: str


TEAM_REGISTRY: dict[str, TeamSpec] = {
    "ARI": TeamSpec("Arizona Diamondbacks", "dbacks", "ari", "#808080", "grey"),
    "ATH": TeamSpec("Athletics", "athletics", "ath", "#008000", "green"),
    "ATL": TeamSpec("Atlanta Braves", "braves", "atl", "#FF0000", "red"),
    "BAL": TeamSpec("Baltimore Orioles", "orioles", "bal", "#FF6347", "tomato"),
    "BOS": TeamSpec("Boston Red Sox", "redsox", "bos", "#FF0000", "red"),
    "CHC": TeamSpec("Chicago Cubs", "cubs", "chc", "#0000FF", "blue"),
    "CWS": TeamSpec("Chicago White Sox", "whitesox", "cws", "#000000", "black"),
    "CIN": TeamSpec("Cincinnati Reds", "reds", "cin", "#FF0000", "red"),
    "CLE": TeamSpec("Cleveland Guardians", "guardians", "cle", "#0000FF", "blue"),
    "COL": TeamSpec("Colorado Rockies", "rockies", "col", "#800080", "purple"),
    "DET": TeamSpec("Detroit Tigers", "tigers", "det", "#000080", "navy"),
    "HOU": TeamSpec("Houston Astros", "astros", "hou", "#FF8C00", "dark orange"),
    "KC": TeamSpec("Kansas City Royals", "royals", "kc", "#DAA520", "goldenrod"),
    "LAA": TeamSpec("Los Angeles Angels", "angels", "laa", "#FF0000", "red"),
    "LAD": TeamSpec("Los Angeles Dodgers", "dodgers", "lad", "#1E90FF", "dodger blue"),
    "MIA": TeamSpec("Miami Marlins", "marlins", "mia", "#FF8C00", "dark orange"),
    "MIL": TeamSpec("Milwaukee Brewers", "brewers", "mil", "#F0E68C", "khaki"),
    "MIN": TeamSpec("Minnesota Twins", "twins", "min", "#0000FF", "blue"),
    "NYM": TeamSpec("New York Mets", "mets", "nym", "#FF6347", "tomato"),
    "NYY": TeamSpec("New York Yankees", "yankees", "nyy", "#2F4F4F", "dark slate grey"),
    "PHI": TeamSpec("Philadelphia Phillies", "phillies", "phi", "#FF0000", "red"),
    "PIT": TeamSpec("Pittsburgh Pirates", "pirates", "pit", "#FFD700", "gold"),
    "SD": TeamSpec("San Diego Padres", "padres", "sd", "#000080", "navy"),
    "SF": TeamSpec("San Francisco Giants", "giants", "sf", "#FF8C00", "dark orange"),
    "SEA": TeamSpec("Seattle Mariners", "mariners", "sea", "#008080", "teal"),
    "STL": TeamSpec("St. Louis Cardinals", "cardinals", "stl", "#FF0000", "red"),
    "TB": TeamSpec("Tampa Bay Rays", "rays", "tb", "#4B0082", "indigo"),
    "TEX": TeamSpec("Texas Rangers", "rangers", "tex", "#FF0000", "red"),
    "TOR": TeamSpec("Toronto Blue Jays", "bluejays", "tor", "#1E90FF", "dodger blue"),
    "WAS": TeamSpec("Washington Nationals", "nationals", "was", "#FF0000", "red"),
}


class State(Enum):
    AK = "Alaska"
    AL = "Alabama"
    AR = "Arkansas"
    AS = "American Samoa"
    AZ = "Arizona"
    CA = "California"
    CO = "Colorado"
    CT = "Connecticut"
    DC = "District of Columbia"
    DE = "Delaware"
    FL = "Florida"
    GA = "Georgia"
    GU = "Guam"
    HI = "Hawaii"
    IA = "Iowa"
    ID = "Idaho"
    IL = "Illinois"
    IN = "Indiana"
    KS = "Kansas"
    KY = "Kentucky"
    LA = "Louisiana"
    MA = "Massachusetts"
    MD = "Maryland"
    ME = "Maine"
    MI = "Michigan"
    MN = "Minnesota"
    MO = "Missouri"
    MP = "Northern Mariana Islands"
    MS = "Mississippi"
    MT = "Montana"
    NC = "North Carolina"
    ND = "North Dakota"
    NE = "Nebraska"
    NH = "New Hampshire"
    NJ = "New Jersey"
    NM = "New Mexico"
    NV = "Nevada"
    NY = "New York"
    OH = "Ohio"
    OK = "Oklahoma"
    OR = "Oregon"
    PA = "Pennsylvania"
    PR = "Puerto Rico"
    RI = "Rhode Island"
    SC = "South Carolina"
    SD = "South Dakota"
    TN = "Tennessee"
    TX = "Texas"
    UT = "Utah"
    VA = "Virginia"
    VI = "Virgin Islands"
    VT = "Vermont"
    WA = "Washington"
    WI = "Wisconsin"
    WV = "West Virginia"
    WY = "Wyoming"