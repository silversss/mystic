import requests as r
import utils as u
from collections import namedtuple
from datetime import datetime, timedelta
import unidecode
from bs4 import BeautifulSoup
from stone import ID_TOKEN, TIEBREAKERS, START_DATE, WEEK_OVERRIDES, OFF_WEEK

start_time = datetime.strptime(START_DATE, '%Y-%m-%d')

def get_week(ts, game_id=None):
    res = WEEK_OVERRIDES.get(game_id, (ts - start_time).days//7 + 1)
    if OFF_WEEK:
        if res == OFF_WEEK:
            return "off"
        elif res > OFF_WEEK:
            return res - 1
    return res


def get_this_week():
    return get_week(datetime.now())


def fix_time(ts):
    return datetime.utcfromtimestamp(ts/1000)


PlayerGameRecord = namedtuple('PlayerGameRecord', ['name',
                                                   'game_time',
                                                   'game_week',
                                                   'game_id',
                                                   'kills',
                                                   'assists',
                                                   'deaths',
                                                   'double',
                                                   'triple',
                                                   'quadra',
                                                   'penta',
                                                   'total_minions'])

TeamGameRecord = namedtuple('TeamGameRecord', ['name',
                                               'game_time',
                                               'game_week',
                                               'game_id',
                                               'win',
                                               'first_blood',
                                               'towers',
                                               'dragons',
                                               'barons',
                                               'fast_win'])


def process_game(game):
    par_id_to_name = {x['participantId']: x['player']['summonerName'] for x in game['participantIdentities']}
    player_stats = []
    game_time = fix_time(game['gameCreation'])
    team_id_to_name = {}
    fast = game["gameDuration"]/60 < 30
    for par in game["participants"]:
        player_name = par_id_to_name[par['participantId']]
        stats = par['stats']
        minions = stats['totalMinionsKilled'] + stats['neutralMinionsKilled']
        player_stats.append(PlayerGameRecord(player_name.split()[1],
                                             game_time,
                                             # NOTE(Alex.R) We include the game id for float week.
                                             get_week(game_time, game["id"]),
                                             game['gameId'],
                                             stats['kills'],
                                             stats['assists'],
                                             stats['deaths'],
                                             stats['doubleKills'],
                                             stats['tripleKills'],
                                             stats['quadraKills'],
                                             stats['pentaKills'],
                                             minions))
        team_id_to_name[par['teamId']] = player_name.split()[0]
    team_stats = []
    for team in game["teams"]:
        team_name = team_id_to_name[team['teamId']]
        team_stats.append(TeamGameRecord(team_name,
                                         game_time,
                                         # NOTE(Alex.R) We include the game id for float week.                                        
                                         get_week(game_time, game["id"]),
                                         game['gameId'],
                                         team['win'] == "Win",
                                         team['firstBlood'],
                                         team['towerKills'],
                                         team['dragonKills'],
                                         team['baronKills'],
                                         fast and team['win'] == "Win"))
    return player_stats + team_stats


def calculate_points(r):
    if isinstance(r, PlayerGameRecord):
        k = 2*r.kills
        a = 1.5*r.assists
        d = 0.5*r.deaths
        t = 2*(r.triple - r.quadra - r.penta)
        q = 5*(r.quadra - r.penta)
        p = 10*r.penta
        cs = 0.01*r.total_minions
        bonus = 2 if r.kills > 9 or r.assists > 9 else 0
        return k + a - d + t + q + p + cs + bonus
    elif isinstance(r, TeamGameRecord):
        w = 2*r.win
        t = r.towers
        d = r.dragons
        b = 2*r.barons
        fb = 2 * r.first_blood
        fw = 2 * r.fast_win
        return w + t + d + b + fb + fw
    else:
        print("WTF is this you dummy")
        return 0


def get_points(week, all_records):
    res = {}
    for record in [x for x in all_records if x.game_week == week]:
        r_name = unidecode.unidecode(record.name.lower())
        res[r_name] = res.get(r_name, 0) + calculate_points(record)
    return res


def get_game_stats(game_info, retry=3):
    if not game_info.get("hash"):
        return None
    baseMatchHistoryStatsUrl = "https://acs.leagueoflegends.com/v1/stats/game/{}/{}?gameHash={}"
    url = baseMatchHistoryStatsUrl.format(game_info["realm"],
                                          game_info["matchHistoryId"],
                                          game_info["hash"])
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36', 'cookie': "id_token={}".format(ID_TOKEN)}
    resp = r.get(url, headers=headers)
    while retry > 0 and resp.status_code != 200:
        retry -= 1
        resp = r.get(url, headers=headers)
    if resp.status_code != 200:
        print("Bad game stats request error code {}".format(resp.status_code))
        return None
    return resp.json()



def get_all_stats(league, key, verbose=False):
    games = {}
    matches = []
    bracket = league["brackets"][key]
    for matchId in league["brackets"][key]["matches"]:
        match = bracket["matches"][matchId]
        for gameUuid in match['games']:
            game = match['games'][gameUuid]
            if 'gameId' in game:
                matches.append(matchId)
                games[gameUuid] = {"matchHistoryId": game['gameId'],
                                   "realm": game["gameRealm"]}
    if verbose:
        print("The games")
        print(len(games))
    tournamentId = league["id"]
    baseMatchUrl = "http://api.lolesports.com/api/v2/highlanderMatchDetails?tournamentId={}&matchId={}"
    for matchId in matches:
        url = baseMatchUrl.format(tournamentId, matchId)
        resp = r.get(url)
        matchData = resp.json()
        for i in matchData["gameIdMappings"]:
            games[i["id"]]["hash"] = i["gameHash"]
    if verbose:
        print("Games with gameHash")
        print(games)
    game_stats = []
    for k, game_info in games.items():
        stats = get_game_stats(game_info)
        if stats:
            game_stats.append(stats)
    return game_stats


def get_game_info_from_url(url):
    split_up = url.split("/")
    last_part = split_up[-1]
    _id, rest = last_part.split("?")
    hash_part = rest.split("&")[0]
    _hash = hash_part.split("=")[1]

    return {"realm": split_up[5],
            "hash": _hash,
            "matchHistoryId": _id}


def get_from_leaguepedia(verbose=False):
    #llec = r.get("https://lol.gamepedia.com/LEC/2019_Season/Summer_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2019_Season/Summer_Season")
    #llec = r.get("https://lol.gamepedia.com/LEC/2020_Season/Spring_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2020_Season/Spring_Season")
    llec = r.get("https://lol.gamepedia.com/LEC/2020_Season/Summer_Season")
    llcs = r.get("https://lol.gamepedia.com/LCS/2020_Season/Summer_Season")
    lcs_soup = BeautifulSoup(llcs.text, 'html.parser')
    lec_soup = BeautifulSoup(llec.text, 'html.parser')
    game_infos = []
    for link in lcs_soup.find_all('a') + lec_soup.find_all('a'):
        link = link.get('href')
        if link and "matchhistory." in link:
            game_info = get_game_info_from_url(link)
            if verbose:
                print(link)
                print(game_info)
            if game_info["hash"] not in TIEBREAKERS:
                game_infos.append(game_info)
    return game_infos


def build_leaguepedia_mystic_library():
    game_infos = get_from_leaguepedia()
    game_stats = []
    for game_info in game_infos:
        stats = get_game_stats(game_info)
        if stats:
            stats["id"] = game_info["hash"]
            game_stats.append(stats)
    processed_games = [process_game(x) for x in game_stats]
    all_records = u.flatten(processed_games)
    return all_records


def build_mystic_library():
    na = r.get(
        "http://api.lolesports.com/api/v1/scheduleItems?leagueId=2").json()
    eu = r.get(
        "http://api.lolesports.com/api/v1/scheduleItems?leagueId=3").json()
    # Spring 2019
    # lec = eu["highlanderTournaments"][8]
    # lcs = na["highlanderTournaments"][6]
    # Summer 2019
    lec = eu["highlanderTournaments"][9]
    lcs = na["highlanderTournaments"][7]

    # Spring 2019
    # lec_reg_season_key = 'd78b9f9d-0ae3-416d-b458-a048143a177c'
    # lcs_reg_season_key = '62ae61a3-7761-40a0-8a50-99d680b0ddea'

    # Summer 2019
    lec_reg_season_key = '5a554448-fd18-4539-89b5-6f36e3d9e310'
    lcs_reg_season_key = '11cbd265-9788-4034-a9d5-6c0b53c19fb7'

    lec_stats = get_all_stats(lec, lec_reg_season_key)
    lcs_stats = []
    try:
        lcs_stats = get_all_stats(lcs, lcs_reg_season_key)
    except:
        print("Looks like lcs has not started yet")
    all_stats = lec_stats + lcs_stats
    processed_games = [process_game(x) for x in all_stats]
    all_records = u.flatten(processed_games)
    return all_records


def points_me_now(week, use_leaguepedia=False):
    if use_leaguepedia:
        mystic_library = build_leaguepedia_mystic_library()
    else:
        mystic_library = build_mystic_library()
    return get_points(week, mystic_library)


def get_stats():
    res = {}
    stats = {}
    for i in range(1, get_this_week()):
        res[i] = points_me_now(i)
    players = list(set(u.flatten([x.keys() for x in res.values()])))
    for player in players:
        stats[player] = [0]*8
    for week, week_stats in res.items():
        for player, stat in week_stats.items():
            stats[player][week - 1] = stat
    return stats
