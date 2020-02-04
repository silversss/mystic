from stone import TEAMS, NAME_FIXES, SHEET_KEY
from fantasy_lord import SCHEDULE
import time
from mystic import points_me_now, get_this_week
import mystic
import utils as u
import gspread
import sys
from oauth2client.service_account import ServiceAccountCredentials


def get_session(cred_file="mystic_creds.json"):
    """ This will return the logged in sesson for the spreadsheet"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_file,
                                                                   scope)
    #print(credentials)
    gc = gspread.authorize(credentials)
    return gc


gc = get_session()
wks = gc.open_by_key(SHEET_KEY)

def get_active_roster(team, wks=wks):
    sp = wks.worksheet(team)
    # Columns to field
    # 1 - Region
    # 2 - Team
    # 3 - Position
    # 4 - Player
    # 5 - Starting
    cells = sp.range('A1:E11')
    active_rows = [x.row for x in cells if x.value.strip() == "TRUE"]
    players = [x.value for x in cells if x.row in active_rows and x.col == 1]
    regions = [x.value for x in cells if x.row in active_rows and x.col == 4]
    return sorted(list(zip(players, regions)), key=lambda x: x[1]+x[0])


def write_matchup(t1, t2, num, week_sheet, region):
    roster1 = get_active_roster(t1)
    roster2 = get_active_roster(t2)
    num_cols = 6
    num_rows = 10
    t1_col = 1
    t2_col = 4
    data_view = [[""]*num_cols for i in range(num_rows)]
    data_view[0][0] = "Match #{}".format(num + 1)
    for t, r, col in [(t1, roster1, t1_col), (t2, roster2, t2_col)]:
        data_view[1][col] = t
        for i, p in enumerate(r):
            both = region == "both"
            in_region = p[1] == region
            if both or in_region:
                data_view[3+i][col] = p[0]
    top_row = num*num_rows + 1
    cells = week_sheet.range(top_row, 1, top_row + num_rows, num_cols)
    for cell, val in zip(cells, u.flatten(data_view)):
        cell.value = val
    week_sheet.update_cells(cells)


def get_week_name(week, test=False):
    name = "Week {} Matchups".format(week)
    if test:
        name = "Test " + name
    return name


def write_week_matchups(week, check=False, test=False, create_sheet=False, region="both"):
    week_name = get_week_name(week, test)
    if create_sheet:
        wks.add_worksheet(title=week_name,
                          rows="100", cols="20")
    week_sheet = wks.worksheet(week_name)
    week_matches = SCHEDULE[week - 1]
    for team, opp in week_matches.items():
        write_matchup(team, opp["opponent"], opp["match"], week_sheet, region)
    if check:
        for i, team in enumerate(TEAMS):
            print(team)
            active_roster = get_active_roster(team, wks)
            print(active_roster)
            print(len(active_roster))


if False:
    write_week_matchups(3, check=True, test=True, create_sheet=False, region="NA")

def col_to_let(col):
    return chr(col + 64)


def update_scores(points, week, test=False):
    week_name = get_week_name(week, test)
    week_sheet = wks.worksheet(week_name)
    read_cells = week_sheet.range(1, 2, 40, 2) + week_sheet.range(1, 5, 40, 5)
    write_cells = week_sheet.range(1, 3, 40, 3) + week_sheet.range(1, 6, 40, 6)
    for read_cell, write_cell in zip(read_cells, write_cells):
        sheet_name = read_cell.value
        if sheet_name in TEAMS:
            col_let = col_to_let(write_cell.col)
            write_cell.value = "=SUM({}{}:{}{})".format(col_let,
                                                        write_cell.row + 2,
                                                        col_let,
                                                        write_cell.row + 8)

        pts = 0
        for sheet_name in sheet_name.split("/"):
            name = NAME_FIXES.get(sheet_name, sheet_name).lower().strip()
            pts += points.get(name, 0)
        if pts:
            write_cell.value = pts
        else:
            print(name)
    week_sheet.update_cells(read_cells + write_cells,
                            value_input_option='USER_ENTERED')


def read_weekly_results(week):
    week_name = get_week_name(week)
    week_sheet = wks.worksheet(week_name)
    # TODO(Alex.R) Don't hard code these
    name_cells = week_sheet.range(1, 2, 40, 2) + week_sheet.range(1, 5, 40, 5)
    score_cells = week_sheet.range(1, 3, 40, 3) + week_sheet.range(1, 6, 40, 6)
    res = {team: {"roster": [], "score": 0} for team in TEAMS}
    curr = ""
    for name_cell, score_cell in zip(name_cells, score_cells):
        name = name_cell.value
        score = score_cell.value
        if score == "":
            score = 0
        if name == "":
            pass
        elif name in TEAMS:
            curr = name
            res[curr]["score"] = float(score)
        else:
            res[curr]["roster"].append({"name": name, "score": float(score)})
    return res


def write_stats():
    print("loading the stats")
    stats = mystic.get_stats()
    print("loaded the stats")
    stats_sheet = wks.worksheet("Stats Page")
    num_players = len(stats.keys())
    cells = stats_sheet.range(2, 1, num_players+1, 9)
    curr_player = 0

    def get_ind(x, y):
        return x + y*9

    print("Updating the cells")
    for player, player_stats in stats.items():
        cells[get_ind(0, curr_player)].value = player
        for num, score in enumerate(player_stats):
            cells[get_ind(num+1, curr_player)].value = score
        curr_player += 1
    print("Updated the cells")
    print("Writing to the sheet")
    stats_sheet.update_cells(cells)
    print("Wrote to the sheet")


def write_weekly_points(points, week):
    points_sheet = wks.worksheet("Player Points")
    read_cells = points_sheet.range(2, 1, 121, 1)
    week_col = 5 + week
    write_cells = points_sheet.range(2, week_col, 121, week_col)
    for read_cell, write_cell in zip(read_cells, write_cells):
        sheet_name = read_cell.value
        pts = 0
        for sheet_name in sheet_name.split("/"):
            name = NAME_FIXES.get(sheet_name, sheet_name).lower().strip()
            pts += points.get(name, 0)
        if pts:
            write_cell.value = pts
        else:
            print("No Points?")
            print(name)
            print(sheet_name)
    points_sheet.update_cells(write_cells)


def end_of_season_results():
    standings = {team: {"win": 0, "loss": 0, "total": 0} for team in TEAMS}
    for i in range(1, 9):
        print("print for week {}".format(i))
        week_scores = read_weekly_results(i)
        matchups = SCHEDULE[i - 1]
        for team in TEAMS:
            opp = matchups[team]["opponent"]
            standings[team]["total"] += week_scores[team]["score"]
            if week_scores[opp]["score"] < week_scores[team]["score"]:
                standings[team]["win"] += 1
            else:
                standings[team]["loss"] += 1
    return standings


if __name__ == "__main__":
    print("THE ARGUMENTS ARE {}".format(sys.argv))
    if sys.argv[1] == "update_points":
        WEEK = get_this_week()
        if WEEK != "off":
            THE_POINTS = points_me_now(WEEK, use_leaguepedia=True)
            print(THE_POINTS)
            write_weekly_points(THE_POINTS, WEEK)
            update_scores(THE_POINTS, WEEK, test=False)
    if sys.argv[1] == "update_stats":
        WEEK = int(sys.argv[2])
        THE_POINTS = points_me_now(WEEK, use_leaguepedia=True)
        print(THE_POINTS)
        write_weekly_points(THE_POINTS, WEEK)
    if sys.argv[1] == "lock_in":
        WEEK = get_this_week()
        if WEEK != "off":
            write_week_matchups(WEEK, region=sys.argv[2])
    if sys.argv[1] == "start_season":
        # NOTE(Alex.R) Assuming 9 weeks in the season
        for i in range(9):
            time.sleep(110)
            write_week_matchups(i, test=False, create_sheet=True)
        
        
            
