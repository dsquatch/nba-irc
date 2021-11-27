# -*- coding: utf-8 -*-
import json

import irc3
from irc3.plugins.command import command


@irc3.plugin
class Plugin:

    def __init__(self, bot):
        from nba_api.stats.endpoints import commonplayerinfo, scoreboard
        from nba_api.stats.static import players, teams

        self.bot = bot
        self.commonplayerinfo = commonplayerinfo
        self.players = players
        self.teams = teams
        self.scoreboard = scoreboard

    @classmethod
    def reload(cls, old):
        """this method should return a ready to use plugin instance.
        cls is the newly reloaded class. old is the old instance.
        """
        return cls(old.bot)

    @command(permission='view')
    def player(self, mask, target, args):
        """Player

            %%player <name>...
        """
        name = ' '.join(args['<name>'])
        players = self.players.find_players_by_full_name(name)
        if not players:
            yield "No players found."

        for player in players:
            if player['is_active']:
                id = player['id']
                break
        if not id:
            id = players[0]['id']
        player = self.commonplayerinfo.CommonPlayerInfo(
            player_id=id).get_normalized_dict()
        player_info = player['CommonPlayerInfo'][0]
        stats = player['PlayerHeadlineStats'][0]
        player_string = f"{player_info['DISPLAY_FIRST_LAST']} ({player_info['TEAM_NAME']} {player_info['POSITION']} #{player_info['JERSEY']}) - {player_info['HEIGHT']} {player_info['WEIGHT']}lbs - {player_info['SCHOOL']}  (#{player_info['DRAFT_NUMBER']} {player_info['DRAFT_YEAR']})"
        player_string += f", {stats['TimeFrame']}: {stats['PTS']}pts {stats['AST']}ast {stats['REB']}reb"
        yield player_string

    @command(permission='view')
    def team(self, mask, target, args):
        """Team

            %%team <name>
        """
        name = args['<name>']
        team = self.teams.find_teams_by_full_name(name)
        print(team)
        yield json.dumps(team)

    def _get_scoreboard(self, date_diff, score_date): 
        if score_date:
            scores = self.scoreboard.Scoreboard(game_date=score_date)
        else:
            scores = self.scoreboard.Scoreboard(day_offset=date_diff)
        # print(scores.get_normalized_dict())
        games = scores.get_normalized_dict()['GameHeader']
        score_text = ""
        for game in games:
            if game['GAME_STATUS_ID'] == 1:
                if score_text != "":
                    score_text += " | "
                else:
                    score_text = f"🏀{game['GAME_DATE_EST'][:game['GAME_DATE_EST'].index('T')]}: "
                home_team_id = game["HOME_TEAM_ID"]
                home_team = self.teams.find_team_name_by_id(home_team_id)
                visitor_team_id = game["VISITOR_TEAM_ID"]
                visitor_team = self.teams.find_team_name_by_id(visitor_team_id)
                score_text += f"{home_team['nickname']} vs {visitor_team['nickname']} {game['GAME_STATUS_TEXT']}"
                if game['NATL_TV_BROADCASTER_ABBREVIATION']:
                    score_text += f" \x02{game['NATL_TV_BROADCASTER_ABBREVIATION']}\x02"

        linescore = scores.get_normalized_dict()['LineScore']
        last_game_id = ""
        for score in linescore:
            print(score)
            if score['PTS']:
                if last_game_id != score['GAME_ID']:
                    last_game_id = score['GAME_ID']
                    t1_name = score['TEAM_ABBREVIATION']
                    t1_pts = score['PTS']
                else:
                    t2_name = score['TEAM_ABBREVIATION']
                    t2_pts = score['PTS']
                    if score_text != "":
                        score_text += " | "
                    else:
                        score_text = f"🏀{score['GAME_DATE_EST'][:score['GAME_DATE_EST'].index('T')]}: "
                    score_text += f"{t1_name} {t1_pts}-{t2_name} {t2_pts}"

        return score_text

    @command(permission='view')
    def scores(self, mask, target, args):
        """Scores

            %%scores [(<days_ago> | -d <date>)]
        """

        score_date = None
        date_diff = None
        if args['<days_ago>']:
            date_diff = -1 * int(args['<days_ago>'])
        elif args['<date>']:
            score_date = args['<date>']
        else:
            date_diff = 0


        yield self._get_scoreboard(date_diff=date_diff,score_date=score_date)
