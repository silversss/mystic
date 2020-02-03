
draft_page = wks.worksheet("Draft Page")
player_page = wks.worksheet("Player Page")


player_page.update_acell("A1", "Player Name")
player_page.update_acell("B1", "Position")
player_page.update_acell("C1", "Team")
player_page.update_acell("D1", "Region")

        
        
na = draft_page.range("A7:K12")
na_labels = [x for x in na if x.col == 1]
na_players = [x for x in na if x.col != 1]

eu = draft_page.range("A15:K20")
eu_labels = [x for x in eu if x.col == 1]
eu_players = [x for x in eu if x.col != 1]

rosters = draft_page.range("B25:I35")
fantasy_players = [x for x in rosters if x.row == 25]
fantasy_picks = [x for x in rosters if x.row != 25]


def get_position(cell, labels):
    for label in labels:
        if cell.row == label.row:
            return label.value

def get_team(a_cell, cells, labels):
    for label in labels:
        if label.value.strip() == "TEAM":
            team_row = label.row
    for cell in cells:
        if cell.row == team_row and cell.col == a_cell.col:
            return cell.value

def get_region(a_cell):
    if a_cell in na_players:
        return "NA"
    else:
        return "EU"

def get_owner(a_cell):
    for pick in fantasy_picks:
        if a_cell.value == pick.value:
            for fantasy_player in fantasy_players:
                if fantasy_player.col == pick.col:
                    return fantasy_player.value
    return "Available"
    
cells_to_update = player_page.range("A2:E121")    

for num, player_cell in enumerate(na_players + eu_players):
    region = get_region(player_cell)
    labels = na_labels if region == "NA" else eu_labels
    cells = na_players if region == "NA" else eu_players
    team = get_team(player_cell, cells, labels)
    position = get_position(player_cell, labels)
    owner = get_owner(player_cell)
    num = num + 2
    for cell in cells_to_update:
        if cell.row == num and cell.col == 1:
            cell.value = player_cell.value
        if cell.row == num and cell.col == 2:
            cell.value = position
        if cell.row == num and cell.col == 3:            
            cell.value = team
        if cell.row == num and cell.col == 4:
            cell.value = region
        if cell.row == num and cell.col == 5:
            cell.value = owner
            
player_page.update_cells(cells_to_update)





for fantasy_player in fantasy_players:
    fantasy_player_name = fantasy_player.value
    roster_page = wks.worksheet(fantasy_player_name)
    roster_page.update_acell("A1", "Player Name")
    roster_page.update_acell("B1", "Position")
    roster_page.update_acell("C1", "Team")
    roster_page.update_acell("D1", "Region")
    roster_page.update_acell("E1", "Starting")
    roster_page.update_acell("A2", "=SORT(FILTER('Player Page'!$A$2:$D$121,'Player Page'!$E$2:$E$121=\"{}\"))".format(fantasy_player_name))








import requests as r
from bs4 import BeautifulSoup

llec = r.get("https://lol.gamepedia.com/LEC/2020_Season/Spring_Season")
llcs = r.get("https://lol.gamepedia.com/LCS/2020_Season/Spring_Season")
lcs_soup = BeautifulSoup(llcs.text, 'html.parser')
lec_soup = BeautifulSoup(llec.text, 'html.parser')


soup = lec_soup
all_matches = []
for week in range(1, 10):
    week_matches = []
    matches = soup.find_all(class_="mdv-allweeks mdv-week{}".format(week))
    if len(matches) == 0:
        matches = soup.find_all(class_="mdv-allweeks mdv-week{} toggle-section-hidden".format(week))
    for match in matches:
        match_teams = []        
        for team in match.find_all(class_="teamname"):
            match_teams.append(team.getText())
        week_matches.append(match_teams)
    all_matches.append(week_matches)
        

import google_monk as gm
schedule_page = gm.wks.worksheet("LEC Schedule")

cells = schedule_page.range("A1:C70")


def update_cell(row, col, value, cells):
    for cell in cells:
        if cell.row == row and cell.col == col:
            cell.value = value
    

row = 1
update_cell(row, 2, "Team 1", cells)
update_cell(row, 3, "Team 2", cells)
row += 1
for week, matches in enumerate(all_matches):
    update_cell(row, 1, "Week {}".format(week + 1), cells)
    row += 1
    for match in matches:
        update_cell(row, 2, match[0], cells)
        update_cell(row, 3, match[1], cells)
        row += 1

schedule_page.update_cells(cells)
        
        
        





    
