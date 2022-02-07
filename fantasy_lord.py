from stone import TEAMS
import random
import pprint as pp

SEED = 2019


def round_robin(teams):
    n = len(teams)
    assert(n % 2 == 0)
    half = int(n/2)
    top = list(teams[:half])
    bot = list(teams[half:])
    schedule = []
    for i in range(n-1):
        curr = {}
        for j in range(half):
            curr[top[j]] = {"opponent": bot[j],
                            "match": j}
            curr[bot[j]] = {"opponent": top[j],
                            "match": j}
        temp_top = top.pop()
        temp_bot = bot.pop(0)
        top.insert(1, temp_bot)
        bot.append(temp_top)
        schedule.append(curr)
    return schedule


def create_schedule(teams, weeks, seed):
    random.seed(seed)
    teams = random.sample(teams, len(teams))
    rr = round_robin(teams)
    stupid = rr*weeks
    return stupid[:weeks]


SCHEDULE = create_schedule(TEAMS, 17, SEED)

# TODO(Alex.R) Move this out into a proper test.
if False:
    print("Doing some testing")
    print("Testing round_robin")
    res = round_robin(TEAMS)
    if True:
        pp.pprint(res)
    for team in TEAMS:
        opponents = [x[team]["opponent"] for x in res]
        assert(set(opponents + [team]) == set(TEAMS))
    print("Looks like round_robin works!")
