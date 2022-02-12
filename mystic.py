import requests as r
import json
import utils as u
from collections import namedtuple, Counter
from datetime import datetime, timedelta
import unidecode
from bs4 import BeautifulSoup
from stone import ID_TOKEN, TIEBREAKERS, START_DATE, WEEK_OVERRIDES, OFF_WEEK

start_time = datetime.strptime(START_DATE, '%Y-%m-%d')

def get_week(ts, game_id=None):
    if ts < start_time:
        return -1
    res = WEEK_OVERRIDES.get(game_id, (ts - start_time).days//7 + 1)    
    if OFF_WEEK:
        if res == OFF_WEEK:
            return "off"
        elif res > OFF_WEEK:
            return res - 12
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
    player_stats = []
    game_time = fix_time(game['gameCreation'])
    team_id_to_name = {}
    fast = game["gameDuration"]/60 < 30
    for par in game["participants"]:
        player_name = par["summonerName"]
        minions = par['totalMinionsKilled'] + par['neutralMinionsKilled']
        player_stats.append(PlayerGameRecord(player_name.split()[1],
                                             game_time,
                                             # NOTE(Alex.R) We include the game id for float week.
                                             get_week(game_time, game["gameId"]),
                                             game['gameId'],
                                             par['kills'],
                                             par['assists'],
                                             par['deaths'],
                                             par['doubleKills'],
                                             par['tripleKills'],
                                             par['quadraKills'],
                                             par['pentaKills'],
                                             minions))
        team_id_to_name[par['teamId']] = player_name.split()[0]
    team_stats = []
    for team in game["teams"]:
        team_name = team_id_to_name[team['teamId']]
        objectives = team["objectives"]
        team_stats.append(TeamGameRecord(team_name,
                                         game_time,
                                         # NOTE(Alex.R) We include the game id for float week.
                                         get_week(game_time, game["gameId"]),
                                         game['gameId'],
                                         team['win'],
                                         objectives["champion"]["first"],
                                         objectives["tower"]["kills"],
                                         objectives["dragon"]["kills"],
                                         objectives["baron"]["kills"],
                                         fast and team['win']))
    return player_stats + team_stats


def old_process_game(game):
    #print(game)
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
                                             get_week(game_time, game["gameId"]),
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
                                         get_week(game_time, game["gameId"]),
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
        pentas = r.penta
        quadras = r.quadra - pentas
        triples = r.triple - quadras - pentas
        cs = 0.01*r.total_minions
        bonus = 2 if r.kills > 9 or r.assists > 9 else 0
        return k + a - d + 2*triples + 5*quadras + 10*pentas + cs + bonus
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

def get_game_counts(week, all_records):
    res = Counter()
    for record in [x for x in all_records if x.game_week == week]:
        r_name = unidecode.unidecode(record.name.lower())
        res[r_name] += 1
    return res


# NOTE(Alex.R) Keeping this around in case the riot api is needed again.
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



def get_game_info_from_url(url):
    split_up = url.split("/")
    last_part = split_up[-1]
    _id, rest = last_part.split("?")
    hash_part = rest.split("&")[0]
    _hash = hash_part.split("=")[1]
    return {"realm": split_up[5],
            "hash": _hash,
            "matchHistoryId": _id}    

def stats_from_leaguepedia(stats_page):
    URL = "https://lol.fandom.com/api.php"
    params = {"action": "query",
              "format": "json",
              "prop": "revisions",
              "titles": stats_page,
              "rvprop": "content",
              "rvslots": "main"}

    resp = r.get(URL, params)

    pages = resp.json()["query"]["pages"]
    if len(pages.keys()) != 1:
        print("Something is off don't have right return from leaguepedia")
    the_page = list(pages.values())[0]
    stats = json.loads(the_page["revisions"][0]["slots"]["main"]["*"])
    return stats


def stats_page_from_url(url,version="V5"):
    _id = url.split(":")[1]
    return "{}_data:".format(version)+ _id


def get_from_leaguepedia(verbose=False):
    #llec = r.get("https://lol.gamepedia.com/LEC/2019_Season/Summer_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2019_Season/Summer_Season")
    #llec = r.get("https://lol.gamepedia.com/LEC/2020_Season/Spring_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2020_Season/Spring_Season")
    #llec = r.get("https://lol.gamepedia.com/LEC/2020_Season/Summer_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2020_Season/Summer_Season")
    #llec = r.get("https://lol.gamepedia.com/LEC/2021_Season/Spring_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2021_Season/Spring_Season")
    #llec = r.get("https://lol.gamepedia.com/LEC/2021_Season/Summer_Season")
    #llcs = r.get("https://lol.gamepedia.com/LCS/2021_Season/Summer_Season")
    llec = r.get("https://lol.gamepedia.com/LEC/2022_Season/Spring_Season")
    llcs = r.get("https://lol.gamepedia.com/LCS/2022_Season/Spring_Season")
    lcs_soup = BeautifulSoup(llcs.text, 'html.parser')
    lec_soup = BeautifulSoup(llec.text, 'html.parser')
    stats_pages = []
    game_infos = []
    for link in lcs_soup.find_all('a') + lec_soup.find_all('a'):
        link = link.get('href')
        if link and "/wiki/V5_metadata:ESPORTS" in link:
            stats_page = stats_page_from_url(link)
            if verbose:
                print(link)
                print(stats_page)
            if stats_page not in TIEBREAKERS:
                stats_pages.append({"page": stats_page, "version": "V5"})
    #stats_pages = list(set(stats_pages))
    for link in lcs_soup.find_all('a') + lec_soup.find_all('a'):
        link = link.get('href')
        if link and "/wiki/V4_metadata:ESPORTS" in link:
            stats_page = stats_page_from_url(link,version="V4")
            if verbose:
                print(link)
                print(stats_page)
            if stats_page not in TIEBREAKERS:
                stats_pages.append({"page": stats_page, "version": "V4"})
    for link in lcs_soup.find_all('a') + lec_soup.find_all('a'):
        link = link.get('href')
        if link and 'matchhistory.' in link:
            game_info = get_game_info_from_url(link)
            if verbose:
                print(link)
                print(game_info)
            if game_info not in TIEBREAKERS:
                game_infos.append(game_info)
    return stats_pages, game_infos


def build_leaguepedia_mystic_library():
    stats_pages, game_infos = get_from_leaguepedia()
    game_stats = []
    old_stats = []
    for stats_page in stats_pages:
        version = stats_page["version"]
        stats_page = stats_page["page"]
        stats = stats_from_leaguepedia(stats_page)
        if stats:
            stats["id"] = stats["gameId"]
            if version == "V5":
                game_stats.append(stats)
            elif version == "V4":
                old_stats.append(stats)
            else:
                print("Wrong version passed")
    for game_info in game_infos:
        stats = get_game_stats(game_info)
        old_stats.append(stats)
    processed_games = [process_game(x) for x in game_stats]
    old_processed_games = [old_process_game(x) for x in old_stats]
    all_records = u.flatten(processed_games + old_processed_games)
    return all_records


def points_me_now(week):
    mystic_library = build_leaguepedia_mystic_library()
    return get_points(week, mystic_library), get_game_counts(week, mystic_library)


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
