from fantasy_lord import SCHEDULE
from google_monk import read_weekly_results

# This is a file to handle writing the weekly reports


def write_weekly_report(week, report):
    matches = {}
    for k, v in SCHEDULE[week - 1].items():
        matches[v["match"]] = [v["opponent"], k]
    # NOTE (Alex.R) Should always have even number of players.
    with open("week{}_newsletter.txt".format(week), "w") as f:
        f.write("Week {} Notes:\n".format(week))
        f.write("\n")
        f.write("Scores--")
        f.write("\n")
        f.write("\n")
        big_win = -1
        big_win_val = 0
        close_win = -1
        close_win_val = 100000
        for i, match in matches.items():
            pts1 = report[match[0]]["score"]
            pts2 = report[match[1]]["score"]
            if abs(pts1 - pts2) > big_win_val:
                big_win_val = abs(pts1 - pts2)
                big_win = i
            if abs(pts1 - pts2) < close_win_val:
                close_win_val = abs(pts1 - pts2)
                close_win = i
        for i, match in matches.items():
            f.write("Match {}".format(i+1))
            if i == big_win:
                f.write(" -- BIGGEST WIN")
            if i == close_win:
                f.write(" -- CLOSEST MATCH")
            f.write("\n")
            f.write("{} - {}".format(match[0], report[match[0]]["score"]))
            f.write("\n")
            f.write("{} - {}".format(match[1], report[match[1]]["score"]))
            f.write("\n")
            f.write("\n")
        f.write("Team Highlights - \n")
        high_score = -1
        high_score_val = 0
        low_score = -1
        low_score_val = 100000
        for team, scores in report.items():
            score = scores["score"]
            if score > high_score_val:
                high_score = team
                high_score_val = score
            if score < low_score_val:
                low_score = team
                low_score_val = score
        for team, scores in report.items():
            f.write("{} ({})".format(team, scores["score"]))
            if team == high_score:
                f.write(': (HIGHEST SCORE) -- NEEDS QUOTE + BOOZE!')
            if team == low_score:
                f.write(': (LOWEST SCORE) -- NEEDS QUOTE')
            f.write("\n")
            m = max(scores["roster"], key=lambda x: x["score"])
            mi = min(scores["roster"], key=lambda x: x["score"])
            f.write('       Best Player: {} ({})\n'.format(
                m["name"], m["score"]))
            f.write('       Worst Player: {} ({})\n'.format(
                mi["name"], mi["score"]))


if True:
    week = 12
    weekly_report = read_weekly_results(week)
    write_weekly_report(week, weekly_report)
    with open("week{}_newsletter.txt".format(week), "r") as f:
        print(f.read())
