# for sim behavior + sampling.
#
# Every magic number that controls *how the simulation behaves* is here
# Pipeline scripts (assign_behaviors), trip planner (sim/trip_planner.py),
# runner (sim/runner.py), and population generator all import from here
#
# Workflow:
#   1. Change a number here
#   2. Re-run pipeline/assign_behaviors.py (if changed a per-agent attribute)
#   3. Re-run sim/runner.py + eval/congestion.py
#   4. Compare outputs

# ---------- MULTIMODAL ROUTING (walk + bike networks) ----------

# Bikers route on the composed (walk + bike) graph prefer bike-allowed
# edges (cycleways, residential roads, shared paths) but can fall back to
# walk-only edges (footways, pedestrian zones)
# penalty multiplies the routing weight of walk-only edges for
# bikers
#   1.0 = no preference
#   1.5 = mild preference for bike 
#   3.0 = strongly avoid walk-only
#   inf = strict bike-only 
WALK_ON_BIKE_PENALTY = 1.5

BIKER_DISMOUNT_SPEED_MPS = 1.3


# ---------- SAMPLING ----------
SAMPLE_EVERY_SEC = 5


# ---------- COFFEE ----------

# p a student is a coffee drinker
COFFEE_DRINKER_RATE_BY_SCHOOL = {
    "engineering":   0.75,
    "hs_natural":    0.68,
    "hs_social":     0.62,
    "hs_humanities": 0.60,
    "hs_interdisc":  0.66,
    "doerr":         0.70,
}
COFFEE_DRINKER_RATE_DEFAULT = 0.66

# School -> coffee destination affinity multipliers (proxy for "first-class
# neighborhood" without needing schedules.csv at population gen time)
# at gen time
#   weight(dest) = exp(-dist_dorm_min / DECAY) * SCHOOL_COFFEE_AFFINITY[school].get(dest, 1.0)

SCHOOL_COFFEE_AFFINITY = {
    "engineering":   {"CODAB": 1.6, "Bytes": 1.5, "Coupa Y2E2": 1.4, "Forbes": 1.2},
    "hs_natural":    {"Coupa Y2E2": 1.3, "CODAB": 1.2, "Bytes": 1.1},
    "hs_social":     {"Coupa Green": 1.4, "CoHo": 1.2, "Coupa GSB": 1.3},
    "hs_humanities": {"Coupa Green": 1.6, "CoHo": 1.3},
    "hs_interdisc":  {"Coupa Green": 1.2, "CoHo": 1.2, "CODAB": 1.1},
    "doerr":         {"Coupa Y2E2": 1.5, "Bytes": 1.2},
}

EARLY_RISER_RATE = 0.40

# Candidate coffee shops
# agent -- pick 1 at gen time, weight by prox to dorm + first class
COFFEE_DESTINATIONS = [
    "CODAB",  # CoDA Coffee (CS/engineering north)
    "Coupa Green",  # Coupa @ Green Library (humanities)
    "Coupa Y2E2",  # Coupa @ Y2E2 (engineering quad)
    "Coupa GSB",  # Coupa @ GSB (business)
    "CoHo",  # Coffee House, Tresidder
    "Starbucks",  # Tresidder
    "Bytes",  # Gates / CS
    "Forbes",  # engineering quad cafe
]

COFFEE_DISTANCE_DECAY_SCALE_MIN = 10

# Duration in minutes for the two coffee modes
COFFEE_GRAB_DURATION_MIN_MEAN = 8  # grab-and-go
COFFEE_GRAB_DURATION_MIN_STD = 2

# Sit n sip mode
COFFEE_SIT_DURATION_MIN_DEFAULT = 30

# Decision table thresholds (hours, in 24h)
#   early riser + first class >= THIS -> sit n sip until class
#   late  riser + first class <  THIS -> skip morning, do afternoon coffee
COFFEE_EARLY_RISER_SIT_THRESHOLD_HR = 9.0
COFFEE_LATE_RISER_SKIP_THRESHOLD_HR = 10.5

# Where to put afternoon coffee trip (late risers w/ early class)
COFFEE_AFTERNOON_WINDOW_SEC = (13 * 3600, 16 * 3600)


# --------- LUNCH ----------

# Window where lunch trip can start
LUNCH_WINDOW_SEC = (11 * 3600, 14 * 3600)

# Duration per-agent sampled once from N(mean, std)
LUNCH_DURATION_MIN_MEAN = 30
LUNCH_DURATION_MIN_STD = 8

# Base p agent eats lunch on campus
LUNCH_ON_CAMPUS_RATE = 0.85

# Class-density adjustment: bump on tight days, drop on light days
#   tight = >= MIN_CLASSES between 10:00-15:00 w all gaps <= MAX_GAP_MIN
#   light = single class today OR last class ends before 11:00
LUNCH_TIGHT_DAY_MULTIPLIER = 1.12
LUNCH_LIGHT_DAY_MULTIPLIER = 0.70
LUNCH_TIGHT_DAY_MIN_CLASSES = 3
LUNCH_TIGHT_DAY_MAX_GAP_MIN = 90
LUNCH_ADJUSTED_RATE_CAP = 0.98  # ceiling after mult

# Base type weights -- combined w distance to current class to score
LUNCH_BASE_TYPE_WEIGHTS = {"eatery": 0.55, "dining_hall": 0.25, "dorm": 0.20}

LUNCH_WILL_GO_DORM_RATE = 0.70

LUNCH_DISTANCE_DECAY_SCALE_MIN = 12

# Candidate dest pools
# Each agent -> SUBSET as personal prefs, at gen time
LUNCH_EATERIES = [
    "TAP",  # The Axe and Palm
    "Forbes",  # Forbes Family Cafe
    "CODAB",  # CoDA
    "Coupa Y2E2",
    "Coupa Green",
    "Coupa GSB",
    "Olives",
    "Bytes",
    "Voyager",
    "Treehouse",  # Tresidder food court
    "Panda",  # Tresidder
    "Subway",  # Tresidder
    "CoHo",  # Tresidder, lunch + coffee
]
LUNCH_DINING_HALLS = [
    "Wilbur Dining",
    "Stern Dining",
    "Arrillaga",
    "EVGR Dining",
    "Lakeside",
    "Branner Dining",
    "FloMo Dining",
    "Ricker",
    "Casper",
]

# Per-agent pool size
LUNCH_EATERIES_PER_AGENT = 3
LUNCH_DINING_HALLS_PER_AGENT = 2

DORM_COMPLEX_PRIMARY_HALL = {
    "Branner":              "Branner Dining",
    "Crothers":             "Arrillaga",  # closest hall
    "Toyon":                "Branner Dining",
    "Mirrielees":           "EVGR Dining",
    "Florence Moore":       "FloMo Dining",
    "Stern":                "Stern Dining",
    "Wilbur":               "Wilbur Dining",
    "Lagunita":             "Lakeside",  # Lagunita has no own hall
    "Gerhard Casper Quad":  "Casper",
    "Governor's Corner":    "Ricker",
    "Roble Hall":           "Lakeside",
    "Row":                  "Stern Dining",  # fallback for row houses
}

AVANTI_DINING_HALL = "Suites Dining"
AVANTI_ELIGIBLE_DORMS = {"Govco Suites"}

YME_DINING_HALL = "YME"
YME_ELIGIBLE_DORMS = {"Yost", "Murray", "EAST"}


#---------------- HOME RETURN -----------------

# gap btwn classes at least this long to consider going home
HOME_RETURN_THRESHOLD_MEAN_MIN = 120
HOME_RETURN_THRESHOLD_STD_MIN = 30

# When a gap qual for both lunch AND home return:
#   p_home = clamp(1 - travel_home_min / DECAY_SCALE, 0.1, 0.9)
HOME_RETURN_TRAVEL_DECAY_SCALE_MIN = 20

# Don't go unless at least this long AT home
HOME_RETURN_MIN_STAY_MIN = 30


# ---------- LIBRARY / STUDY ---------
# p library
LIBRARY_USE_RATE_BASE = 0.50
LIBRARY_USE_RATE_SCHOOL_DELTA = {
    "hs_humanities": +0.15,
    "hs_social":     +0.15,
    "hs_natural":     0.00,
    "hs_interdisc":   0.00,
    "engineering":   -0.10,
    "doerr":          0.00,
}

LIBRARY_MIN_GAP_MIN = 45

LIBRARY_DURATION_CAP_MIN = 90

# Candidate libraries
LIBRARY_DESTINATIONS = [
    "Green",  # main library, biggest
    "Lathrop",
    "Lane",  # medical
    "Huang",  # engineering quad study lounge
    "Y2E2",  # eng / earth sciences study spaces
]

LIBRARY_SCHOOL_AFFINITY = {
    "engineering":   {"Huang": 1.6, "Y2E2": 1.5, "Green": 1.0, "Lathrop": 1.0, "Lane": 0.3},
    "hs_natural":    {"Green": 1.3, "Lathrop": 1.0, "Y2E2": 1.2, "Huang": 1.0, "Lane": 0.5},
    "hs_social":     {"Green": 1.7, "Lathrop": 1.3, "Y2E2": 0.7, "Huang": 0.7, "Lane": 0.4},
    "hs_humanities": {"Green": 1.8, "Lathrop": 1.4, "Y2E2": 0.5, "Huang": 0.5, "Lane": 0.3},
    "hs_interdisc":  {"Green": 1.3, "Lathrop": 1.2, "Y2E2": 1.0, "Huang": 1.0, "Lane": 0.6},
    "doerr":         {"Y2E2": 1.5, "Green": 1.2, "Lathrop": 1.0, "Huang": 1.0, "Lane": 0.5},
}

LIBRARY_DESTINATIONS_PER_AGENT = 2


# ------------ DINNER ---------
# Window where dinner trip can start
DINNER_WINDOW_SEC = (17 * 3600, 21 * 3600)

DINNER_ON_CAMPUS_RATE = 0.55

DINNER_DURATION_MIN_MEAN = 40
DINNER_DURATION_MIN_STD = 10

DINNER_BASE_TYPE_WEIGHTS = {"dining_hall": 0.55, "eatery": 0.25, "dorm": 0.20}

# ------------ GYM ---------
GYM_DAYS_PER_WEEK_DIST = {
    0: 0.30,
    1: 0.20,
    2: 0.18,
    3: 0.15,
    4: 0.10,
    5: 0.05,
    6: 0.02,
}

# Per-day roll for "is today a gym day" given weekly frequency:
#   is_gym_today = rng.uniform(0, 7) < gym_days_per_week

GYM_START_HOUR_WEIGHTS = {
    6:  0.05,  7:  0.10,  8:  0.07,  9:  0.04,  10: 0.02,
    11: 0.02,  12: 0.04,  13: 0.05,
    14: 0.04,  15: 0.10,  16: 0.18,  17: 0.20,  18: 0.16,
    19: 0.10,  20: 0.06,  21: 0.04,
}

GYM_DURATION_MIN_MEAN = 60
GYM_DURATION_MIN_STD = 20

GYM_DESTINATIONS = ["ACSR", "AOERC"]


# ------- RNG ---------

BEHAVIOR_RNG_SEED = 2026
