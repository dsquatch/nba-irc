# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime

import irc3
import pytz
from dateutil import parser
from irc3.plugins.command import command

from scores_helpers import (avg, h2h_date, opp_from_matchup, pct, rank,
                            schedule_date, short_date, shorten, small_date,
                            today)


@irc3.plugin
class Plugin:

    def __init__(self, bot):
        from nba_api.live.nba.endpoints import boxscore, playbyplay
        from nba_api.live.nba.endpoints import scoreboard as livescoreboard
        from nba_api.stats.endpoints import (commonplayerinfo,
                                             commonteamroster,
                                             leaguegamefinder, leaguestandings,
                                             playercareerstats, playergamelogs,
                                             scoreboard, teamdetails,
                                             teamgamelog, teamgamelogs,
                                             winprobabilitypbp)
        from nba_api.stats.static import players, teams

        self.bot = bot
        self.commonplayerinfo = commonplayerinfo
        self.commonteamroster = commonteamroster
        self.leaguegamefinder = leaguegamefinder
        self.leaguestandings = leaguestandings
        self.scoreboard = scoreboard
        self.teamgamelog = teamgamelog
        self.live_scoreboard = livescoreboard
        self.playbyplay = playbyplay
        self.playergamelogs = playergamelogs
        self.playercareerstats = playercareerstats
        self.teamdetails = teamdetails
        self.teamgamelogs = teamgamelogs
        self.winprobabilitypbp = winprobabilitypbp
        self.boxscore = boxscore
        self.players = players
        self.teams = teams
        self.CURRENT_SEASON = "2021-22"  # TODO this should not be hardcoded
        self.TEAM_SCORES_GAMES = 7  # number of games to show on -scores <team>

    @classmethod
    def reload(cls, old):
        """this method should return a ready to use plugin instance.
        cls is the newly reloaded class. old is the old instance.
        """
        return cls(old.bot)

    def _get_season(self, season_text):
        year_match  = re.search('^[0-9][0-9][0-9][0-9]', season_text)
        year = None
        if year_match:
            year = int(year_match[0])
        if not year_match:
            year_match  = re.search('^[0-9][0-9]', season_text)
            if year_match:
                short_year = int(year_match[0])
                if short_year > 35:
                    year = int(f"19{short_year}")
                else:
                    year = int(f"20{short_year}")
        if not year:
            return None
        next_year = f"{year + 1}"[-2:]
        season = f"{year}-{next_year}"
        return season

    def _player_name_to_id(self, name):
        nicknames = {
            'steph': 'stephen curry',
            'steph curry': 'stephen curry',
            'cp3': 'chris paul',
            'pg': 'paul george',
            'dame': 'damian lillard',
            'shaq': 'shaquille o\'neal',
            'freedom': 'enes kanter'

        }
        if name in nicknames:
            name = nicknames[name]
        players = self.players.find_players_by_full_name(name)
        id = None
        if not players:
            return id
        for player in players:
            if player['is_active']:
                return player['id']
        if not id:
            return players[0]['id']

    @command(permission='view')
    def player(self, mask, target, args):
        """Player

            %%player <name>...
        """
        name = ' '.join(args['<name>'])
        id = self._player_name_to_id(name)
        if not id:
            yield "Player not found."

        player = self.commonplayerinfo.CommonPlayerInfo(
            player_id=id).get_normalized_dict()
        player_info = player['CommonPlayerInfo'][0]
        if player['PlayerHeadlineStats']:
            stats = player['PlayerHeadlineStats'][0]
        else:
            stats = None
        player_string = f"{player_info['DISPLAY_FIRST_LAST']} {small_date(player_info['BIRTHDATE'])} ({player_info['TEAM_NAME']} {player_info['POSITION']}  #{player_info['JERSEY']}) - {player_info['HEIGHT']} {player_info['WEIGHT']}lbs - {player_info['SCHOOL']}  "
        if player_info['DRAFT_YEAR'] == "Undrafted":
            player_string += f" (Undrafted) "
        else:
            player_string += f"(#{player_info['DRAFT_NUMBER']} R{player_info['DRAFT_ROUND']} {player_info['DRAFT_YEAR']})"
        if player_info['FROM_YEAR']:
            player_string += f" ({player_info['FROM_YEAR']}-{player_info['TO_YEAR']})"
        if stats:
            player_string += f" | {stats['TimeFrame']}: {stats['PTS']}pts {stats['AST']}ast {stats['REB']}reb"
        yield player_string

    @command(permission='view')
    def career(self, mask, target, args):
        """Career stats

            %%career [(all-star | playoffs | college)] <name>...
        """
        name = ' '.join(args['<name>'])
        player_id = self._player_name_to_id(name)
        if not player_id:
            yield "Player not found."
            return

        player = self.players.find_player_by_id(player_id)
        stats = self.playercareerstats.PlayerCareerStats(
            player_id=player_id).get_normalized_dict()
        if args['all-star']:
            logs = stats['CareerTotalsAllStarSeason']
        elif args['college']:
            logs = stats['CareerTotalsCollegeSeason']
        elif args['playoffs']:
            logs = stats['CareerTotalsPostSeason']
        else:
            logs = stats['CareerTotalsRegularSeason']

        for log in logs:
            log_str= self.print_season(player, log)
            yield log_str

    def print_season(self, player,  log):
        print(log)
        log_str = f" {player['full_name']}"
        log_str += f" {avg(log['PTS'], log['GP'])} PT "
        for stat in [['FG', log['FGM'], log['FGA']], ['FT', log['FTM'], log['FTA']], ['3P', log['FG3M'], log['FG3A']]]:
            log_str += f" {pct(stat[1],stat[2])} of {avg(stat[2],log['GP'])} {stat[0]} "
        for stat in [['RB', log['REB']], ['AS', log['AST']], ['BLK', log['BLK']], ['ST', log['STL']], ['TO', log['TOV']], ['PF', log['PF']], ['MIN', log['MIN']]]:
            log_str += f" {avg(stat[1],log['GP'])} {stat[0]} "
        log_str += f" {log['GS']}/{log['GP']} GS"
        if 'SEASON_ID' in log:
            log_str += f"  ({log['SEASON_ID']}"
            if 'TEAM_ABBREVIATION' in log:
                log_str += f" {log['TEAM_ABBREVIATION']}"
            if 'SCHOOL_NAME' in log:
                log_str += f" {log['SCHOOL_NAME']}"
            log_str += ")"
        return log_str

    @command(permission='view')
    def seasonstats(self, mask, target, args):
        """Season stats

            %%seasonstats [(all-star | playoffs | college)] (<name>... | -s <season> <name>...)
        """
        name = ' '.join(args['<name>'])
        player_id = self._player_name_to_id(name)
        if not player_id:
            yield "Player not found."
            return

        if args['<season>']:
            season = self._get_season(args['<season>'])
        else:
            season = None


        player = self.players.find_player_by_id(player_id)
        stats = self.playercareerstats.PlayerCareerStats(
            player_id=player_id).get_normalized_dict()
        if args['all-star']:
            logs = stats['SeasonTotalsAllStarSeason']
        elif args['college']:
            logs = stats['SeasonTotalsCollegeSeason']
        elif args['playoffs']:
            logs = stats['SeasonTotalsPostSeason']
        else:
            logs = stats['SeasonTotalsRegularSeason']

        log_str = ""
        if season:
            for log in logs:
                if log['SEASON_ID'] == season:
                    log_str = self.print_season(player, log)
                    yield log_str
        if log_str == "":
            yield self.print_season(player, logs[-1])

    def print_ranks(self, player,  log):
        print(log)
        # {'PLAYER_ID': 203081, 'SEASON_ID': '2021-22', 'LEAGUE_ID': '00', 'TEAM_ID': 1610612757, 'TEAM_ABBREVIATION': 'POR', 'PLAYER_AGE': 'NR', 'GP': 'NR', 'GS': 'NR', 'RANK_MIN': 53, 'RANK_FGM': 33, 'RANK_FGA': 20, 'RANK_FG_PCT': 113, 'RANK_FG3M': 19, 'RANK_FG3A': 10, 'RANK_FG3_PCT': 125, 'RANK_FTM': 14, 'RANK_FTA': 19, 'RANK_FT_PCT': 8, 'RANK_OREB': 250, 'RANK_DREB': 131, 'RANK_REB': 164, 'RANK_AST': 12, 'RANK_STL': 204, 'RANK_BLK': 159, 'RANK_TOV': 33, 'RANK_PTS': 19, 'RANK_EFF': 41}
        log_str = f" {player['full_name']}"
        for stat in ['PTS',  'FGM', 'FGA','FG_PCT', 'FTM', 'FTA','FT_PCT', 'FG3M', 'FG3A','FG3_PCT','REB','AST', 'BLK', 'STL', 'TOV','EFF' ]:
            log_str += f" {rank(stat,log['RANK_'+stat])} "
        if 'SEASON_ID' in log:
            log_str += f"  ({log['SEASON_ID']}"
            if 'TEAM_ABBREVIATION' in log:
                log_str += f" {log['TEAM_ABBREVIATION']}"
            log_str += ")"
        return log_str

    @command(permission='view')
    def seasonranks(self, mask, target, args):
        """Season ranks

            %%seasonranks [(playoffs)] (<name>... | -s <season> <name>...)
        """
        name = ' '.join(args['<name>'])
        player_id = self._player_name_to_id(name)
        if not player_id:
            yield "Player not found."
            return

        if args['<season>']:
            season = self._get_season(args['<season>'])
        else:
            season = None


        player = self.players.find_player_by_id(player_id)
        stats = self.playercareerstats.PlayerCareerStats(
            player_id=player_id).get_normalized_dict()
        if args['playoffs']:
            logs = stats['SeasonRankingsPostSeason']
        else:
            logs = stats['SeasonRankingsRegularSeason']

        log_str = ""
        if season:
            for log in logs:
                if log['SEASON_ID'] == season:
                    log_str = self.print_ranks(player, log)
                    yield log_str
        if log_str == "":
            yield self.print_ranks(player, logs[-1])




    @command(permission='view')
    def stats(self, mask, target, args):
        """Game stats

            %%stats (<name>... | -l <number_of_games> <name>... | -d <date> <name>...)
        """
        name = ' '.join(args['<name>'])
        player_id = self._player_name_to_id(name)
        if not player_id:
            yield "Player not found."
            return

        player_info = self.commonplayerinfo.CommonPlayerInfo(
            player_id=player_id)
        team_id = player_info.get_normalized_dict(
        )['CommonPlayerInfo'][0]['TEAM_ID']

        season = self.CURRENT_SEASON
        number_of_games = 1
        game_date = None
        if args['<date>']:
            game_date = args['<date>']
            game_datetime = parser.parse(game_date)
            if game_datetime.month < 7:
                season = self._get_season(str(game_datetime.year -1))
            else:
                season = self._get_season(str(game_datetime.year))
            number_of_games = 0
        elif args['<number_of_games>']:
            number_of_games = args['<number_of_games>']

        if number_of_games == 1:
            day_offset = 0
            if datetime.now().hour >= 1 and datetime.now().hour < 8:
                day_offset = -1

            today_date = datetime.now(pytz.timezone('US/Pacific')).strftime("%m/%d/%Y")
            scores = self.scoreboard.Scoreboard(game_date=today_date)

            games = scores.get_normalized_dict()['GameHeader']
            live_game_id = None
            home_or_away = None
            for game in games:
                if game['HOME_TEAM_ID'] == team_id or game['VISITOR_TEAM_ID'] == team_id:
                    if int(game['GAME_STATUS_ID']) >= 2:
                        if game['HOME_TEAM_ID'] == team_id:
                            home_or_away = "home"
                        else:
                            home_or_away = "away"

                        live_game_id = game['GAME_ID']
                        game_status = game['GAME_STATUS_TEXT']
                        break
                    else:
                        break

            log_str = None
            if live_game_id:
                box = self.boxscore.BoxScore(game_id=live_game_id)
                game = box.game.get_dict()

                if home_or_away == "home":
                    players = box.home_team_player_stats.get_dict()
                else:
                    players = box.away_team_player_stats.get_dict()
                for player in players:
                    if player['personId'] == player_id:
                        log = player['statistics']
                        game_clock = game['gameStatusText']
                        minutes = log['minutesCalculated'].replace(
                            "PT0", "").replace("PT", "").replace("M", "")
                        plus_minus = log['plusMinusPoints']
                        if plus_minus > 0:
                            plus_minus = f"+{plus_minus}"
                        log_str = f"{player['name']}"
                        log_str += f" {log['points']} PT  {log['fieldGoalsMade']}-{log['fieldGoalsAttempted']} FG  {log['freeThrowsMade']}-{log['freeThrowsAttempted']} FT "
                        log_str += f" {log['threePointersMade']}-{log['threePointersAttempted']} 3P  {log['reboundsTotal']}/{log['reboundsOffensive']} RB "
                        log_str += f" {log['assists']} AS  {log['blocks']} BL  {log['steals']} ST  {log['turnovers']} TO  {log['foulsPersonal']} PF  {minutes} MN "
                        log_str += f" ({plus_minus}) ({game_clock})"
                        yield log_str
                        return

        logs = self.playergamelogs.PlayerGameLogs(player_id_nullable=player_id,
                                                  last_n_games_nullable=number_of_games, date_to_nullable=game_date, date_from_nullable=game_date,
                                                  season_nullable=season).get_normalized_dict()

        if len(logs['PlayerGameLogs']) == 0:
            yield "No games found."
            return
        elif len(logs['PlayerGameLogs']) == 1:
            log = logs['PlayerGameLogs'][0]
            name = log['PLAYER_NAME']
            matchup = opp_from_matchup(log['MATCHUP'])
            game_date = short_date(log['GAME_DATE'])
            minutes = int(log['MIN'])
            if log['PLUS_MINUS'] > 0:
                plus_minus = f"+{log['PLUS_MINUS']}"
            else:
                plus_minus = log['PLUS_MINUS']

            log_str = f"{name} {log['PTS']} PT  {log['FGM']}-{log['FGA']} FG  {log['FTM']}-{log['FTA']} FT "
            log_str += f" {log['FG3M']}-{log['FG3A']} 3P  {log['REB']}/{log['OREB']} RB "
            log_str += f" {log['AST']} AS  {log['BLK']} BL  {log['STL']} ST  {log['TOV']} TO  {log['PF']} PF  {minutes} MN "
            log_str += f" ({plus_minus}) ({game_date} {matchup})"
            yield log_str
        else:
            log_count = len(logs['PlayerGameLogs'])
            pts = fgm = fga = fg3m = fg3a = reb = ftm = fta = ast = blk = stl = tov = pf = minutes = 0
            for log in logs['PlayerGameLogs']:
                pts += log['PTS']
                fgm += log['FGM']
                fga += log['FGA']
                ftm += log['FTM']
                fta += log['FTA']
                fg3m += log['FG3M']
                fg3a += log['FG3A']
                reb += log['REB']
                ast += log['AST']
                blk += log['BLK']
                stl += log['STL']
                tov += log['TOV']
                pf += log['PF']
                minutes += int(log['MIN'])
            log_str = f"{logs['PlayerGameLogs'][0]['PLAYER_NAME']}  {avg(pts,log_count)} PT "
            for stat in [['FG', fgm, fga], ['FT', ftm, fta], ['3P', fg3m, fg3a]]:
                log_str += f" {pct(stat[1],stat[2])} of {avg(stat[2],log_count)} {stat[0]} "
            for stat in [['RB', reb], ['AS', ast], ['BLK', blk], ['ST', stl], ['TO', tov], ['PF', pf], ['MN', minutes]]:
                log_str += f" {avg(stat[1],log_count)} {stat[0]} "
            log_str += f" (last {log_count} games)"
            yield log_str

    @command(permission='view')
    def team(self, mask, target, args):
        """Team

            %%team <name>
        """
        name = args['<name>']
        teams = self.teams.find_teams_by_full_name(name)
        if not teams[0]:
            yield "Team not found."
            return
        team_id = teams[0]['id']
        team = self.teamdetails.TeamDetails(
            team_id=team_id).get_normalized_dict()
        championships = [
            f"{championship['YEARAWARDED']}"
            for championship in team['TeamAwardsChampionships']
        ]
        if len(championships) == 0:
            str_championships = ""
        else:
            str_championships = f" | 🏆 {','.join(championships)}"

        history = team['TeamHistory']
        list_history = []
        for era in history:
            year_until = era['YEARACTIVETILL']
            if year_until == 2019:
                year_until = ""
            list_history.append(
                f"{era['CITY']} {era['NICKNAME']} {era['YEARFOUNDED']}-{year_until}")

        str_history = ""
        if len(list_history):
            str_history = f" ({','.join(list_history)}) "

        bg = team['TeamBackground'][0]
        team_str = f"{teams[0]['full_name']}:"
        capacity = ""
        if bg['ARENACAPACITY']:
            capacity = f" {int(bg['ARENACAPACITY']):,} "
        team_str += f" {bg['ARENA']}{capacity}{str_history}| o: {bg['OWNER']} gm: {bg['GENERALMANAGER']} c: {bg['HEADCOACH']}{str_championships}"
        yield team_str

    def _team_scores(self, team_name, number_of_games):
        teams = self.teams.find_teams_by_full_name(team_name)
        if not teams[0]:
            return "Team not found."
        team_id = teams[0]['id']
        logs = self.teamgamelogs.TeamGameLogs(season_nullable=self.CURRENT_SEASON, team_id_nullable=team_id,
                                              last_n_games_nullable=number_of_games).get_normalized_dict()['TeamGameLogs']
        log_list = []
        for log in logs:
            print(log)
            pts = log['PTS']
            opts = pts + int(log['PLUS_MINUS'])
            log_list.append(
                f" {small_date(log['GAME_DATE'])} {opp_from_matchup(log['MATCHUP'])} {log['WL']} {pts}-{opts} ")

        log_str = f" {' | '.join(log_list)} "
        return log_str

    def _get_scoreboard(self, date_diff=None, score_date=None, topic: bool = False):
        if score_date:
            scores = self.scoreboard.Scoreboard(game_date=score_date)

        else:
            scores = self.scoreboard.Scoreboard(day_offset=date_diff)
        games = scores.get_normalized_dict()['GameHeader']
        score_text = ""
        topic_text = ""
        game_status = {}
        for game in games:
            if game['GAME_STATUS_ID'] == 1 or (topic and game['GAME_STATUS_ID'] == 2):
                if score_text != "":
                    score_text += " | "
                    topic_text += " "
                else:
                    score_text = f"🏀{short_date(game['GAME_DATE_EST'])}: "
                home_team_id = game["HOME_TEAM_ID"]
                home_team = self.teams.find_team_name_by_id(home_team_id)
                visitor_team_id = game["VISITOR_TEAM_ID"]
                visitor_team = self.teams.find_team_name_by_id(visitor_team_id)
                score_text += f"{home_team['nickname']} vs {visitor_team['nickname']} {game['GAME_STATUS_TEXT']}"
                topic_text += f"{home_team['abbreviation']}@{visitor_team['abbreviation']}"
                tv = game['NATL_TV_BROADCASTER_ABBREVIATION']
                if tv:
                    if tv.strip() == "TNT":
                        score_text += f" \x0304,08\x02TNT\x02\x0f"
                    else:
                        score_text += f" \x02{game['NATL_TV_BROADCASTER_ABBREVIATION']}\x02"

        if not date_diff or date_diff == 0:
            board = self.live_scoreboard.ScoreBoard().games.get_dict()

            for score in board:
                if score['gameStatus'] != 1:
                    if score_text != "":
                        score_text += " | "
                        topic_text += " "
                    else:
                        score_text = f"Today: "

                    t1_name = score['homeTeam']['teamTricode']
                    t1_pts = score['homeTeam']['score']
                    t2_name = score['awayTeam']['teamTricode']
                    t2_pts = score['awayTeam']['score']
                    if score['gameLeaders']['homeLeaders']['points'] > score['gameLeaders']['awayLeaders']['points']:
                        scorer_id = score['gameLeaders']['homeLeaders']['personId']
                        stats = f" {score['gameLeaders']['homeLeaders']['points']}/{score['gameLeaders']['homeLeaders']['rebounds']}/{score['gameLeaders']['homeLeaders']['assists']}"
                    else:
                        scorer_id = score['gameLeaders']['awayLeaders']['personId']
                        stats = f" {score['gameLeaders']['awayLeaders']['points']}/{score['gameLeaders']['awayLeaders']['rebounds']}/{score['gameLeaders']['awayLeaders']['assists']}"
                    player = self.players.find_player_by_id(scorer_id)

                    score_text += f"{t1_name} {t1_pts} {t2_name} {t2_pts}"
                    if player:
                        score_text += f" {shorten(player['last_name'],8)}{stats} "
                    if score['gameStatus'] == 2:
                        score_text += f" \x02{score['gameStatusText']}\x02"
                    if t1_pts > t2_pts:
                        topic_text += f"{t1_name}>{t2_name}"
                    else:
                        topic_text += f"{t1_name}<{t2_name}"
        else:
            linescore = scores.get_normalized_dict()['LineScore']
            last_game_id = ""
            for score in linescore:
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
                            score_text = f"🏀{short_date(score['GAME_DATE_EST'])}: "
                        score_text += f"{t1_name} {t1_pts} {t2_name} {t2_pts}"
                        if score['GAME_ID'] in game_status:
                            score_text += f" \x02{game_status[score['GAME_ID']].replace(' - ','').strip()}\x02"
        if topic:
            return topic_text
        return score_text

    @command(permission='view')
    def scores(self, mask, target, args):
        """Scores

            %%scores [(-l <number_of_games> <team> | <team> | -a <days_ago>  | -f <days_in_future>| -d <date> | --topic )]
        """

        score_date = None
        date_diff = None
        team_name = None
        topic = False
        if args['<days_ago>']:
            date_diff = -1 * int(args['<days_ago>'])
        elif args['<days_in_future>']:
            date_diff = int(args['<days_in_future>'])
        elif args['<date>']:
            score_date = args['<date>']
        elif args['--topic']:
            date_diff = 0
            topic = True
        else:
            date_diff = 0
            score_date = datetime.now(pytz.timezone('US/Pacific')).strftime("%m/%d/%Y")

        #if date_diff == 0 and datetime.now().hour > 1 and datetime.now().hour < 8:
        #    date_diff = -1

        if args['<team>']:
            team_name = args['<team>']
            if args['<number_of_games>']:
                number_of_games = args['<number_of_games>']
            else:
                number_of_games = self.TEAM_SCORES_GAMES

            yield self._team_scores(team_name=team_name, number_of_games=number_of_games)
        else:
            yield self._get_scoreboard(date_diff=date_diff, score_date=score_date, topic=topic)

    @command(permission='view')
    def standings(self, mask, target, args):
        """Standings

            %%standings [(-s <season> | -s <season> <east_or_west> | <east_or_west>)]
        """
        conf = None
        if args['<east_or_west>'] == 'east':
            conf = "East"
        if args['<east_or_west>'] == 'west':
            conf = "West"


       
        season = self.CURRENT_SEASON
        if args['<season>']:
            season = self._get_season(args['<season>'])
        
        print(season)

        standings = self.leaguestandings.LeagueStandings(
            league_id="00", season=season, season_type="Regular Season").get_normalized_dict()['Standings']

        standings = sorted(standings, key = lambda i: i['WinPCT'], reverse=True)
        row_count = 1
        teams = []
        for row in standings:
            if not conf or row['Conference'] == conf:
                win_pct = f"{row['WinPCT']:.3F}"[1:]
                streak = str(row['strCurrentStreak']).replace(' ', '')
                if streak == "None":
                    streak = ""
                else:
                    streak = f"({streak})"
                teams.append(
                    f" {row_count}. {row['TeamName']} {row['WINS']}-{row['LOSSES']} {win_pct} {streak}")
                row_count += 1
                if row_count > 12:
                    break
        if not conf:
            conf = "NBA"
        season_text = ""
        if season != self.CURRENT_SEASON:
            season_text = f"{season} "

        yield f"{season_text}{conf} Standings: {' '.join(teams)}"

    @command(permission='view')
    def winchance(self, mask, target, args):
        """Win probability

            %%winchance <team>
        """

        team_name = args['<team>']
        teams = self.teams.find_teams_by_full_name(team_name)
        if not teams[0]:
            yield "Team not found."
            return
        team_id = teams[0]['id']
        today_date = datetime.now(pytz.timezone('US/Pacific')).strftime("%m/%d/%Y")
        scores = self.scoreboard.Scoreboard(game_date=today_date)

        games = scores.get_normalized_dict()['GameHeader']
        live_game_id = None
        home_or_away = None
        score_text = ""
        for game in games:
            if game['HOME_TEAM_ID'] == team_id or game['VISITOR_TEAM_ID'] == team_id:
                if game['HOME_TEAM_ID'] == team_id:
                    home_or_away = "home"
                    stat = 'HOME_PCT'
                else:
                    home_or_away = "away"
                    stat = 'VISITOR_PCT'

                live_game_id = game['GAME_ID']
                game_status = game['GAME_STATUS_TEXT']

                home_team_id = game["HOME_TEAM_ID"]
                home_team = self.teams.find_team_name_by_id(home_team_id)
                visitor_team_id = game["VISITOR_TEAM_ID"]
                visitor_team = self.teams.find_team_name_by_id(visitor_team_id)
                break
        if not live_game_id:
            yield "Live game not found."
            return

        prob = self.winprobabilitypbp.WinProbabilityPBP(game_id=live_game_id,run_type='each second').get_normalized_dict()['WinProbPBP']
        win_chance = 0
        i = 0
        print(prob)
        while win_chance == 0 and i < len(prob):
            i = i +1
            if prob[i*-1][stat]:
                win_chance = prob[i*-1][stat]
        if home_or_away == "home":
            str_team = home_team['nickname']
        else:
            str_team = visitor_team['nickname']

        msg = f"{home_team['nickname']} {prob[i*-1]['HOME_PTS']} - {visitor_team['nickname']} {prob[i*-1]['VISITOR_PTS']} |   {str_team} win chance: {round(win_chance * 100,2)}%"
        yield msg

    @command(permission='view')
    def playbyplay(self, mask, target, args):
        """Play by play

            %%playbyplay <team>
        """

        team_name = args['<team>']
        teams = self.teams.find_teams_by_full_name(team_name)
        if not teams[0]:
            yield "Team not found."
            return
        team_id = teams[0]['id']
        today_date = datetime.now(pytz.timezone('US/Pacific')).strftime("%m/%d/%Y")
        scores = self.scoreboard.Scoreboard(game_date=today_date)

        games = scores.get_normalized_dict()['GameHeader']
        live_game_id = None
        home_or_away = None
        score_text = ""
        for game in games:
            if game['HOME_TEAM_ID'] == team_id or game['VISITOR_TEAM_ID'] == team_id:
                if game['HOME_TEAM_ID'] == team_id:
                    home_or_away = "home"
                else:
                    home_or_away = "away"

                live_game_id = game['GAME_ID']
                game_status = game['GAME_STATUS_TEXT']

                home_team_id = game["HOME_TEAM_ID"]
                home_team = self.teams.find_team_name_by_id(home_team_id)
                visitor_team_id = game["VISITOR_TEAM_ID"]
                visitor_team = self.teams.find_team_name_by_id(visitor_team_id)
                break
        if not live_game_id:
            yield "Live game not found."
            return
        end_period=4
        start_period=1
        pbp = self.playbyplay.PlayByPlay(game_id=live_game_id).get_dict()['game']['actions']
        print(pbp)
        msg = ""
        for i in [-3, -2, -1]:
            if 'description' in pbp[i]:
                msg += f" | {pbp[i]['description']} "
                clock = pbp[i]['clock']
                period = pbp[i]['period']
                if period in [1,2,3,4]:
                    period = f"Q{period}"
                # 'clock': 'PT08M17.00S',
                clock = clock.replace('PT','').replace('M',':').replace('.00S','')

                score_text = f"{home_team['nickname']} {pbp[i]['scoreHome']} - {visitor_team['nickname']} {pbp[i]['scoreAway']} ({clock} {period}) "
                
        yield score_text + msg




    @command(permission='view')
    def record(self, mask, target, args):
        """Team Record

            %%record (<team> | -s <season> <team>)
        """

        if args['<season>']:
            season = self._get_season(args['<season>'])
        else:
            season = self.CURRENT_SEASON
        team_name = args['<team>']
        teams = self.teams.find_teams_by_full_name(team_name)
        if not teams[0]:
            yield "Team not found."
            return
        team_id = teams[0]['id']

        standings = self.leaguestandings.LeagueStandings(
            league_id="00", season=season, season_type="Regular Season").get_normalized_dict()['Standings']
        record = ""
        for row in standings:
            if row['TeamID'] == team_id:
                win_pct = f"{row['WinPCT']:.3F}"[1:]
                streak = str(row['strCurrentStreak']).replace(' ', '')
                if streak == "None":
                    streak = ""
                else:
                    streak = f"({streak})"
                if season == self.CURRENT_SEASON:
                    streaks = f" {row['L10'].strip()} L10  {streak}"
                else:
                    streaks = ""
                # <Ticket> Portland Blazers 10-10 (.500) 6-7 Conf 1-1 Div 9-1 Home 1-9 Away Lost 2
                record = f"{row['WINS']}-{row['LOSSES']}  ({win_pct})  {row['ConferenceRecord'].strip()} Conf  {row['HOME'].strip()} Home  {row['ROAD'].strip()} Road  {streaks}"
                break
        season_text = ""
        if season != self.CURRENT_SEASON:
            season_text = f" {season}"

        yield f"{teams[0]['full_name']}{season_text} (#{row['PlayoffRank']} Playoff): {record}"

    @command(permission='view')
    def lottery(self, mask, target, args):
        """Lottery

            %%lottery [<east_or_west>]
        """
        standings = self.leaguestandings.LeagueStandings(
            league_id="00", season=self.CURRENT_SEASON, season_type="Regular Season").get_normalized_dict()['Standings']

        conf = None
        if args['<east_or_west>'] == 'east':
            conf = "East"
        if args['<east_or_west>'] == 'west':
            conf = "West"

        reverse = False 
        if conf:
            reverse = True
        standings = sorted(standings, key = lambda i: i['WinPCT'], reverse=reverse)

        row_count = 1
        teams = []
        for row in standings:
            if not conf or row['Conference'] == conf:
                if not conf or (conf and row_count > 7):
                    win_pct = f"{row['WinPCT']:.3F}"[1:]
                    teams.append(
                        f" {row_count}. {row['TeamName']} {row['WINS']}-{row['LOSSES']} {win_pct}")
                if not conf and row_count >= 14:
                    break
                row_count += 1
        if not conf:
            conf = "NBA"
        yield f"{conf} Lottery: {'  '.join(teams)}"

    @command(permission='view')
    def roster(self, mask, target, args):
        """Team roster

            %%roster (<team> | -s <season> <team>)
        """

        if args['<season>']:
            season = self._get_season(args['<season>'])
        else:
            season = self.CURRENT_SEASON
        team_name = args['<team>']
        teams = self.teams.find_teams_by_full_name(team_name)
        if not teams[0]:
            yield "Team not found."
            return
        team_id = teams[0]['id']

        roster = self.commonteamroster.CommonTeamRoster(
            team_id=team_id, season=season).get_normalized_dict()
        coaches = roster['Coaches']
        players = roster['CommonTeamRoster']
        str_coaches = ""
        for coach in coaches:
            if coach['IS_ASSISTANT'] == 1:  # head coach
                str_coaches = f"Coach - {coach['COACH_NAME']} "
                break
        list_players = []
        for player in players:
            list_players.append(f"#{player['NUM']} {player['PLAYER']}")

        season_text = ""
        if season != self.CURRENT_SEASON:
            season_text = f" {season}"

        yield f"{teams[0]['full_name']}{season_text}: {str_coaches} {' '.join(list_players)}"

    @command(permission='view')
    def headtohead(self, mask, target, args):
        """Head to head games

            %%headtohead <team1> <team2>
        """

        team1_name = args['<team1>']
        teams1 = self.teams.find_teams_by_full_name(team1_name)
        if not teams1[0]:
            yield "Team 1 not found."
            return
        team1_id = teams1[0]['id']
        team1_name = teams1[0]['nickname']

        team2_name = args['<team2>']
        teams2 = self.teams.find_teams_by_full_name(team2_name)
        if not teams2[0]:
            yield "Team 2 not found."
            return
        team2_name = teams2[0]['nickname']
        team2_abbrev = teams2[0]['abbreviation']
        games = self.leaguegamefinder.LeagueGameFinder(team_id_nullable=team1_id, season_type_nullable='Regular Season',
                                                       season_nullable=self.CURRENT_SEASON).get_normalized_dict()['LeagueGameFinderResults']
        # games = self.teamgamelog.TeamGameLog(team_id=team1_id,season=self.CURRENT_SEASON,season_type_all_star="Regular Season").get_normalized_dict()['TeamGameLog']
        list_games = []
        total_w = total_l = 0
        for game in games:
            if game['MATCHUP'][-3:] == team2_abbrev:
                pts = game['PTS']
                o_pts = int(game['PTS'] + game['PLUS_MINUS'])
                if game['WL'] == 'W':
                    total_w += 1
                else:
                    total_l += 1

                list_games.append(
                    f"{h2h_date(game['GAME_DATE'])} {opp_from_matchup(game['MATCHUP'])} {game['WL']} {pts}-{o_pts}")
        yield f"{team1_name} vs {team2_name} {total_w}-{total_l} | {' | '.join(list_games)}"
