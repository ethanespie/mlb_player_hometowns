# mlb_player_hometowns

This was my second-ever personal (non-work, non-school) coding project; I did most of the initial work on this in 2018.  

**What does this do?** 

It uses the _requests_ and _bs4_ libraries to web-scrape the player pages on the various team pages of https://www.mlb.com/, to get each player's birth place, and then for a given MLB team (or for all 30 teams if you like):
* uses _folium_ to make a html/javascript file for viewing in a browser
* ~~uses _gmplot_ to make a html/javascript file for viewing in a browser~~ (Deprecated, for now.)
* ~~uses _simplekml_ to make a kml file for viewing in Google Earth~~ (Deprecated, for now.)

Example: locations of Seattle Mariners' hometowns, as of October 2025: 
<img width="1684" height="1230" alt="Screenshot 2025-10-15 170105" src="https://github.com/user-attachments/assets/255a0d09-925f-40f0-9a10-b8bfd0ecfcf4" />


**Why MLB player hometowns?**  

I've always loved baseball and I always thought it was kind of cool how many MLB players come from foreign countries, especially Latin America. I wanted to see a map of all of their home towns; and as far as I could tell at the time there wasn't one out there. 

There is this, but it's only of the US:
http://www.slate.com/articles/sports/culturebox/2014/10/baseball_player_map_a_new_u_s_map_based_on_where_baseball_players_were_born.html

And then there's this, but the map/site mentioned seems to no longer exist.
https://www.cbssports.com/mlb/news/map-of-the-day-birthplace-of-all-professional-baseball-players/
