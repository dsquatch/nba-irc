from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.static import players

# Basic Request
name = 'James Harden'
players = players.find_players_by_full_name(name)
id = players[0]['id']

player_info = commonplayerinfo.CommonPlayerInfo(player_id=id)

print(player_info.get_normalized_json())
