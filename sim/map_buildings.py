# buildings.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import COURSES_RAW, OUTPUTS

BUILDING_LOCATIONS = {
    # Numbered buildings
    "100":      ("Building 100",                        37.42825159081596,  -122.17084475876669),
    "110":      ("Building 110",                        37.428130039177994, -122.17050818474688),
    "120":      ("Wallenberg Hall",                     37.428458910621785, -122.16950813177937),
    "160":      ("Building 160",                        37.42843775051482,  -122.1690598606148),
    "20":       ("Building 20",                         37.427547220284765, -122.16924847116454),
    "200":      ("Main Quad",                           37.42847830983823,  -122.16845138945033),
    "240":      ("Geology Corner",                      37.42749761233302,  -122.1687933759568),
    "250":      ("Mitchell Earth Sciences",             37.42710387347879,  -122.16889770294404),
    "260":      ("Building 260",                        37.42650495469481,  -122.16906001643767),
    "300":      ("Building 300",                        37.426491074137715, -122.16970073177946),
    "320":      ("Building 320",                        37.42692481311556,  -122.17186431643763),
    "360":      ("Durand Building",                     37.42765873212261,  -122.17181631828588),
    "370":      ("Building 370",                        37.42810581150237,  -122.17159503177947),
    "380":      ("Building 380",                        37.428876949565,    -122.17133324527293),
    "40":       ("Building 40",                         37.427003513437775, -122.16958074712133),
    "420":      ("Building 420",                        37.42879787019937,  -122.17076495876667),
    "460":      ("Jordan Hall",                         37.42869664995507,  -122.17042374712126),
    "50":       ("Memorial Auditorium area",            37.42714418123728,  -122.16997102883546),
    "500":      ("Building 500",                        37.42607163543592,  -122.16957838760216),
    "530":      ("Li Ka Shing Center area",             37.426314834111096, -122.17095300294409),
    "540":      ("Building 540",                        37.42613971418772,  -122.17110345876674),
    "60":       ("Braun Music area",                    37.42729176086113,  -122.17073341349358),
    "70":       ("Building 70",                         37.42738113275321,  -122.17124841643775),
    "90":       ("Encina Hall area",                    37.428046131390595, -122.1712195164376),

    # Named buildings
    "ANKO":         ("Annenberg Building",              37.426489390387516, -122.16838975202774),
    "Alway":        ("Alway Building",                  37.43241340879434,  -122.17492105767093),
    "Art Gallery":  ("Cantor Arts Center",              37.428121611480556, -122.1676872164375),
    "BARNUM":       ("Barnum Hall",                     37.4257988955436,   -122.16865994527318),
    "Beckman":      ("Beckman Center",                  37.432119484032505, -122.17661614527293),
    "Bing":         ("Bing Concert Hall",               37.43215650596899,  -122.16607477410834),
    "Bishop":       ("Bishop Auditorium",               37.429655807250604, -122.16725074527294),
    "Braun":        ("Braun Music Center",              37.42390802912161,  -122.16951722883542),
    "CCSR":         ("Clark Center CCSR",               37.43250702494789,  -122.17798660294379),
    "CODAB":        ("CoDA Coffee",                     37.429974414980364, -122.17168225603719),
    "Campbell":     ("Campbell Recital Hall",           37.423787519660344, -122.1699569164378),
    "Cemex":        ("Cemex Auditorium",                37.42877685035125,  -122.16298515876676),
    "Chemistry Gazebo": ("Chemistry Gazebo",            37.43115406617632,  -122.17223240294389),
    "Clark":        ("Clark Center",                    37.43144968525243,  -122.17450478945025),
    "DINKG":        ("Dinkelspiel Auditorium",          37.42424280039734,  -122.16990214527318),
    "Dinkelspiel":  ("Dinkelspiel Auditorium",          37.42424280039734,  -122.16990214527318),
    "Econ":         ("Economics Building",              37.42878261747215,  -122.16579221534188),
    "Encina Center":("Encina Center",                   37.42746331254808,  -122.16459231643753),
    "Encina Commons":("Encina Commons",                 37.42691352143868,  -122.16488735767096),
    "Encina West":  ("Encina West",                     37.42742923246196,  -122.16462450294394),
    "GSB":          ("Graduate School of Business",     37.42811171171916,  -122.16120538945034),
    "Gates":        ("Gates Computer Science",          37.43019959300751,  -122.17334102883544),
    "Gilbert":      ("Gilbert Biological Sciences",     37.43024414660827,  -122.17258646061475),
    "Green":        ("Green Earth Sciences",            37.426783712777485, -122.17414888945063),
    "Hewlett":      ("Hewlett Teaching Center",         37.429047210216304, -122.1728484317794),
    "Huang":        ("Huang Engineering Center",        37.427934411636585, -122.17438536061492),
    "Knight":       ("Knight Building",                 37.43022884664157,  -122.16698724712128),
    "Knoll":        ("The Knoll",                       37.42087456949301,  -122.17297221627497),
    "LAW":          ("Stanford Law School",             37.424177395439806, -122.16738302442742),
    "Lathrop":      ("Lathrop Library",                 37.42927486938497,  -122.16742580294397),
    "Li Ka":        ("Li Ka Shing Center",              37.43193796483769,  -122.1757580029437),
    "Littlefield":  ("Littlefield Center",              37.43049913459962,  -122.16753750000001),
    "McCullough":   ("McCullough Building",             37.42761172016733,  -122.1729777288355),
    "McMurtry":     ("McMurtry Art Building",           37.432397602616085, -122.17180969527287),
    "Memaud":       ("Memorial Auditorium",             37.4289296693226,   -122.16665281828583),
    "Memorial":     ("Memorial Auditorium",             37.4289296693226,   -122.16665281828583),
    "Mitchell":     ("Mitchell Earth Sciences",         37.42654097405268,  -122.17247120294408),
    "NVIDIA":       ("NVIDIA Auditorium",               37.42832133082691,  -122.17432708945033),
    "O'Donohue":    ("O'Donohue Farm",                  37.42677861445522,  -122.18420071828585),
    "Packrd":       ("Packard Building",                37.429428827636755, -122.17380291643757),
    "Packard":      ("Packard Building",                37.429428827636755, -122.17380291643757),
    "Potter":       ("Potter House",                    37.42583479659254,  -122.17962683177959),
    "Raikes":       ("Raikes School",                   37.426489390387516, -122.16838975202774),
    "Roble":        ("Roble Gymnasium",                 37.42608721955861,  -122.17483725350662),
    "SAPP":         ("SAPP Building",                   37.430826065005704, -122.17144658945033),
    "STLC":         ("STLC Building",                   37.43080902573001,  -122.17143586061485),
    "School of Medicine": ("School of Medicine",        37.43298214452399,  -122.17436326449177),
    "Sequoia":      ("Sequoia Hall",                    37.42906336974604,  -122.1721318894503),
    "Shriram":      ("Shriram Center",                  37.429040049931615, -122.17541393177945),
    "Skilling":     ("Skilling Auditorium",             37.42724173273941,  -122.17284617410847),
    "SpilkerEng":   ("Spilker Engineering",             37.42904383602576,  -122.17399308465812),
    "Sweet":        ("Sweet Hall",                      37.42527263707281,  -122.1666549452732),
    "Thornton":     ("Thornton Hall",                   37.4257209361543,   -122.17369338760221),
    "Turing":       ("Turing Auditorium",               37.42925676857834,  -122.1775681182858),
    "William":      ("William H. Neukom Building",      37.423609858584584, -122.16811595876693),
    "Y2E2":         ("Y2E2 Building",                   37.42820895125612,  -122.17541302993116),
    "Green":         ("Green Library",                   37.435269655170146, -122.17057323584405),
    "Lane":         ("Lane Medical Library",                   37.43283798273006, -122.17546560185971),


    "AOERC":         ("Arrillaga Outdoor Education and Recreation Center",                   37.427044922889245, -122.17747710871191),
    "ACSR":         ("Arrillaga Center for Sports and Recreation",                   37.43000654941918, -122.16381620849373),
}


# BUILDING_LOCATIONS keys
SUBJECT_TO_HOME_BUILDING = {
    # Engineering
    "CS":       "Gates",  # Gates CS
    "EE":       "Packard",  # Packard EE
    "ME":       "530",  # Building 530 = Li Ka Shing area; ME lives in 500-series
    "BIOE":     "Shriram",  # Shriram = bioE building
    "CHEMENG":  "Shriram",  # ChemE shares Shriram
    "MS&E":     "Huang",  # MS&E in Huang
    "ENGR":     "Huang",  # Generic ENGR -> engineering quad center
    "CEE":      "Y2E2",  # CEE shares Y2E2

    # H&S Natural Sciences
    "MATH":     "380",  # Building 380 (Math)
    "PHYSICS":  "320",  # Building 320 (Physics)
    "CHEM":     "SAPP",  # Sapp Center for Science Teaching & Learning
    "BIO":      "Gilbert",  # Gilbert Biological Sciences
    "STATS":    "Sequoia",  # Sequoia Hall (Stats)
    "HUMBIO":   "Gilbert",  # Human Bio shares biology buildings
    "DATASCI":  "Sequoia",  # DataSci/Stats share Sequoia

    # H&S Social Sciences
    "ECON":     "Econ",  # Economics Building
    "PSYCH":    "420",  # Building 420
    "POLISCI":  "Encina Center",  # Encina = poli sci
    "SOC":      "120",  # Wallenberg / Building 120 (sociology)
    "ANTHRO":   "50",  # Building 50 (anthro)
    "COMM":     "McCullough",  # Comm in McCullough
    "PUBLPOL":  "Encina Center",  # Public Policy in Encina
    "SYMSYS":   "460",  # Symsys in Margaret Jacks (460/Jordan Hall)
    "HUMSCI":   "200",  # Humanities & Sciences admin = Main Quad

    # H&S Humanities
    "ENGLISH":  "460",  # English in Margaret Jacks (Building 460)
    "HISTORY":  "200",  # History Corner = Main Quad (Building 200)
    "PHIL":     "90",  # Philosophy in Building 90 (Encina area)
    "MUSIC":    "Braun",  # Braun Music Center
    "TAPS":     "Memaud",  # TAPS = Memorial Auditorium
    "FILMEDIA": "McMurtry",  # Film & Media Studies in McMurtry Art
    "PWR":      "460",  # PWR shares 460/Margaret Jacks
    "COLLEGE":  "Hewlett", 

    # Doerr School of Sustainability
    "EARTHSYS": "Y2E2",  # Earth Systems in Y2E2
}

DINING_LOCATIONS = {
    # Dining Halls
    "Arrillaga":        ("Arrillaga Dining",            37.42554405550269,  -122.16410887410869),
    "Lakeside":         ("Lakeside Dining",             37.424869059910634, -122.17641234712138),
    "Wilbur Dining":    ("Wilbur Dining Hall",          37.42443400187598,  -122.16302041643775),
    "Stern Dining":     ("Stern Dining",                37.42465947726492,  -122.16561401643777),
    "FloMo Dining":     ("Florence Moore Dining",       37.422489616576435, -122.171720086903),
    "Ricker":           ("Ricker Dining",               37.42563093512291,  -122.18048541643762),
    "Casper":           ("Casper Dining",               37.425590412990836, -122.16192641309851),
    "Branner Dining":   ("Branner Dining",              37.42587411745252,  -122.16271107978075),
    "EVGR Dining":      ("EVGR Dining",                37.42744845683085, -122.15750482284872),
    "Suites Dining":     ("Suites Dining",             37.42471968955181, -122.18088091642588),
    "YME":              ("YME Dining",                37.425174230206984, -122.17847526803594),

    # Other
    "TAP":              ("The Axe and Palm",            37.42515437642011,  -122.17055727595691),
    "Forbes":           ("Forbes Family Cafe",          37.428266210994664, -122.1742287317794),
    "Olives":           ("Olives",                      37.42841743062989,  -122.16880238760208),
    "Med Cafe":         ("Medical School Cafe",         37.43197668793252, -122.17585741545408),

    "Coupa Green":      ("Coupa Cafe Green Library",    37.42649365705376,  -122.16705937595694),
    "Coupa Y2E2":       ("Coupa Cafe Y2E2",             37.42845255086797,  -122.17560924712134),
    "Coupa GSB":        ("Coupa Cafe GSB",              37.42818633110339,  -122.16215810479227),
    "Bytes":            ("Bytes Cafe Gates",            37.42941798990146,  -122.17352321643746),
    "Voyager":          ("Voyager",                     37.43007544828158,  -122.1716909894502),
    "CoHo":             ("Coffee House",                37.4242893002863,   -122.17098120479235),
    
    "Blend":            ("Blend Juice Bar",             37.430597165526756, -122.17239202993113),
    "Greenfish":        ("Greenfish",                   37.431137705438175, -122.17469573177935),
    "Jamba":            ("Jamba Juice",                 37.424401343572484, -122.17078478057674),
    "Treehouse":        ("Treehouse",                   37.424053852539295, -122.17126068259887),
    "Panda":            ("Panda Express",               37.423946380759205, -122.17084342253206),
    "Starbucks":        ("Starbucks",                   37.42414699462392,  -122.17084116707224),
    "Subway":           ("Subway",                      37.423946380759205, -122.17084342253206),
}

# Dining hours sourced from rde.stanford.edu/dining-hospitality (Spring 2026 weekday hours)
DINING_METADATA = {
    # Dining halls
    "Arrillaga": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "10:00"),
            "lunch":     ("11:00", "15:00"),
            "dinner":    ("17:00", "20:30"),
        },
    },
    "Lakeside": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "10:00"),
            "lunch":     ("11:00", "14:30"),
            "dinner":    ("17:00", "20:30"),
        },
    },
    "Wilbur Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("11:00", "13:30"),
            "dinner":    ("17:00", "20:00"),
        },
    },
    "Stern Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("11:00", "13:30"),
            "dinner":    ("17:00", "20:00"),
        },
    },
    "FloMo Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("11:00", "13:30"),
            "dinner":    ("17:00", "20:00"),
        },
    },
    "Ricker": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("11:00", "13:30"),
            "dinner":    ("17:00", "20:00"),
        },
    },
    "Casper": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "lunch":  ("11:00", "13:30"),
            "dinner": ("17:00", "20:00"),
        },
    },
    "Branner Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "lunch":  ("11:00", "13:30"),
            "dinner": ("17:00", "19:00"),
        },
    },
    "EVGR Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "dinner": ("17:00", "19:00"),
        },
    },
    "Suites Dining": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("11:00", "13:00"),
            "dinner":    ("17:00", "19:00"),
        },
    },
    "YME": {
        "category": "dining_hall", "meal_plan": True,
        "hours": {
            "breakfast": ("07:30", "09:00"),
            "lunch":     ("12:00", "13:00"),
            "dinner":    ("18:00", "19:00"),
        },
    },

    # R&DE cafes
    "TAP": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("11:00", "23:59")},  # technically open til 2am
    },
    "Forbes": {
        "category": "cafe", "meal_plan": False,
        "hours": {
            "breakfast": ("08:00", "10:30"),
            "lunch":     ("11:00", "14:00"),
        },
    },
    "Olives": {
        "category": "cafe", "meal_plan": False,
        "hours": {
            "breakfast": ("07:30", "10:00"),
            "lunch":     ("10:30", "14:00"),
        },
    },
    "Med Cafe": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:00", "15:00")},
    },

    # Non-R&DE cafes
    "Coupa Green": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:30", "19:00")},
    },
    "Coupa Y2E2": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:30", "17:00")},
    },
    "Coupa GSB": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:00", "20:00")}, 
    },
    "Bytes": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:00", "14:30")}, 
    },
    "CoHo": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("08:00", "22:00")}, 
    },
    "Voyager": {
        "category": "cafe", "meal_plan": False,
        "hours": {"open": ("07:00", "17:00")},
    },

    # Tresidder
    "Treehouse": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("10:00", "22:00")},
    },
    "Panda": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("10:30", "20:00")},
    },
    "Subway": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("09:00", "20:00")},
    },
    "Starbucks": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("05:30", "19:30")},
    },
    "Jamba": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("07:30", "19:30")},
    },
    "Blend": {
        "category": "retail", "meal_plan": False,
        "hours": {"open": ("11:00", "14:00")}, 
    },
    "Greenfish": {
        "category": "retail", "meal_plan": False,
        "hours": {"breakfast": ("08:00", "10:30"),
                  "lunch": ("11:00", "14:00"),
                  "dinner": ("15:00", "17:00")},
    },
}

DORM_LOCATIONS = {
    # Branner
    "Branner":          ("Branner Hall",                37.42554637575066,  -122.16289266061501),

    # Crothers
    "Crothers":         ("Crothers Hall",               37.4261598352551,   -122.16571031828579),
    "Crothers Memorial":("Crothers Memorial",           37.42600705577146,  -122.16474370294415),

    # Toyon
    "Toyon":            ("Toyon Hall",                  37.42617261504555,  -122.16346260294398),
    
    # Apartments + suites
    "Mirrielees":       ("Mirrielees",                  37.423625058560596, -122.15981481828612),
    "EVGR":             ("EVGR-A",           37.424800872308914, -122.15942858020942),
    "Govco Suites":     ("Governor's Corner Suites", 37.424597359205535, -122.17956329686542), 

    # Flomo + subhouses
    # "FloMo":               ("Florence Moore Hall",         37.422489616576435, -122.171720086903),
    "Alondra":             ("Alondra (FloMo)",          37.422489616576435, -122.171720086903), 
    "Cardenal":            ("Cardenal (FloMo)",         37.42197347941193, -122.1711487301425),  
    "Faisan":              ("Faisan (FloMo)",           37.42164195401045, -122.1714409394618),  
    "Gavilan":             ("Gavilan (FloMo)",          37.42160938493771, -122.17184861652744), 
    "Loro":                ("Loro (FloMo)",             37.42216883344648, -122.1726391470952), 
    "Mirlo":               ("Mirlo (FloMo)",            37.4224547721803, -122.1723704188819), 
    "Paloma":              ("Paloma (FloMo)",           37.422489616576435, -122.171720086903), 

    # Stern + subhouses 
    # "Stern":            ("Stern Hall",                  37.42473169179578,  -122.16565427116453),
    "Burbank":             ("Burbank (Stern)",          37.42415290434469, -122.16525857546935), 
    "Casa Zapata":         ("Casa Zapata (Stern)",      37.4238782409102, -122.16560036064527), 
    "Donner":              ("Donner (Stern)",           37.42434355249279, -122.16630427535372), 
    "Larkin":              ("Larkin (Stern)",           37.42493165049676, -122.16607641857146),
    "Sally Ride":          ("Sally Ride (Stern)",       37.423998154959975, -122.16618331819402), 
    "Twain":               ("Twain (Stern)",            37.42468930298066, -122.1650388564242), 

    # Wilbur + subhouses
    # "Wilbur":           ("Wilbur Hall",                 37.424391400042225, -122.16310624712146),
    "Arroyo":              ("Arroyo (Wilbur)",          37.4244099745652, -122.16245573245061),  
    "Cedro":               ("Cedro (Wilbur)",           37.424150713177696, -122.16218269228573), 
    "Junipero":            ("Junipero (Wilbur)",        37.42356893186982, -122.16236167854015),
    "Okada":               ("Okada (Wilbur)",           37.423445383017274, -122.16290853309695), 
    "Otero":               ("Otero (Wilbur)",           37.4237074560983, -122.16373824345531),
    "Rinconada":           ("Rinconada (Wilbur)",       37.424018198705866, -122.16412009879237), 
    "Soto":                ("Soto (Wilbur)",            37.4245202912842, -122.16393375275823), 
    "Trancos":             ("Trancos (Wilbur)",         37.42456480305372, -122.16357324423848), 

    # Lagunita + subhouses
    # "Lagunita":         ("Lagunita Court",              37.4254931889434,   -122.17637072381716),
    "Adelfa":              ("Adelfa (Lagunita)",        37.42551393499349, -122.17642242088732),  
    "Meier":               ("Meier (Lagunita)",         37.425254275750476, -122.17504498601295), 
    "Naranja":             ("Naranja (Lagunita)",       37.425339215566524, -122.17585769659736), 
    "Norcliffe":           ("Norcliffe (Lagunita)",     37.42565787379536, -122.17674182746858),
    "Ujamaa":              ("Ujamaa (Lagunita)",        37.42456368827505, -122.17578240064543),
    "West Lagunita":       ("West Lagunita",            37.42473658877888, -122.17636142277652), 
    "Roble Hall":       ("Roble Hall",                  37.424425766731844, -122.17442955767093),

    # Gerhard Casper Quad
    "Kimball":          ("Kimball Hall",                37.425048806354575, -122.16190708667169),
    "Castano":          ("Castano",                     37.425142056416796, -122.16081958649758),
    "Lantana":          ("Lantana",                     37.42569680227947,  -122.16065691170235),
    "Ng":                  ("Ng House",                 37.42649888583288, -122.16137227125782), 

    # Governor's Corner
    "Potter":           ("Potter",                      37.42583479659254,  -122.17962683177959),
    "Murray":           ("Murray",                      37.42520253840577,  -122.17841591438707),
    "Adams":               ("Adams (Govco)",            37.42618252368693, -122.17972615766288),  
    "EAST":                ("EAST/Treat (Govco)",       37.42576742761246, -122.17854836528774), 
    "Robinson":            ("Robinson (Govco)",         37.4259069773324, -122.18091590379055),
    "Schiff":              ("Schiff (Govco)",           37.426387007376064, -122.18076685476528), 
    "Yost":                ("Yost (Govco)",             37.42479341814135, -122.1782740398536), 

    # Row Houses
    "Kappa Alpha Theta":("Kappa Alpha Theta",           37.420962424114755, -122.16254065038936),
    "Pi Beta Phi":      ("Pi Beta Phi",                 37.42191537316113,  -122.1624098337423),
    "550 Lasuen":          ("550 Lasuen",               37.423445047883625, -122.16940137919349), 
    "576 Alvarado":        ("576 Alvarado",             37.4228208702684, -122.16609001729378), 
    "680 Lomita":          ("680 Lomita",               37.42124799770271, -122.17162618660623), 
    "Alpha Phi/KKG":       ("Alpha Phi/KKG",            37.421989276328084, -122.16207933263883),
    "Delta Delta Delta":   ("Delta Delta Delta",        37.422660419046274, -122.16168878660514),
    "Durand":              ("Durand",                   37.41951896224487, -122.1657962098853), 
    "Enchanted Broccoli Forest": ("EBF",                37.42003579046997, -122.17378317126135), 
    "Jerry":               ("Jerry",                    37.42197852244473, -122.17374025591693), 
    "Kairos":              ("Kairos",                   37.420960383825005, -122.16783363263974), 
    "Kappa Alpha":         ("Kappa Alpha",              37.42089793440467, -122.1740544712619), 
    "Muwekma-Tah-Ruk":     ("Muwekma-Tah-Ruk",          37.42351625071305, -122.16904573232551), 
    "Narnia":              ("Narnia",                   37.42024153357308, -122.17503735766276),  
    "Neptune":             ("Neptune (650 Mayfield)",   37.41858487402672, -122.1654084633994), 
    "Robert Moore North":  ("Robert Moore North",       37.42267934921009, -122.16917735591636), 
    "Roth":                ("Roth",                     37.41986969475085, -122.167504747985),  
    "Sigma Phi Epsilon":   ("Sigma Phi Epsilon",        37.420041951184366, -122.17087465054819),
    "Storey":              ("Storey",                   37.4239271900762, -122.16975005591533), 
    "Synergy":             ("Synergy",                  37.42008272508935, -122.16899795591821), 
    "Terra":               ("Terra",                    37.42181824611333, -122.16329636332772), 
    "Kappa Sigma":      ("Kappa Sigma",                 37.42038278497288,  -122.170177276243),
    "BOB":              ("BOB",                         37.42164385651383,  -122.16892200243772),
    "Grove":            ("Grove",                       37.42045100974768,  -122.16811687115349),
    "aKDPhi/Chi Omega": ("alpha Kappa Delta Phi",       37.4205928974969,   -122.16900629048149),
    "Phi Kappa Psi":    ("Phi Kappa Psi",               37.42000495988917,  -122.16724139698331),
    "Toussaint":        ("Toussaint Louverture",        37.4197854553805,   -122.16690144203697),
    "Warehaus":         ("The Warehaus",                37.41946812983744,  -122.16644078717722),
    "Pluto":            ("Pluto",                       37.41833048716228,  -122.16598049174966),
    "ZAP":              ("ZAP",                         37.42157861811553,  -122.16173319579416),
    # "Casa Italiana":    ("Casa Italiana",               37.4219640372706,   -122.16915584527335),
    "Columbae":         ("Columbae",                    37.42320623871052,  -122.16878923177947),
    "Hammarskjold":     ("Hammarskjold",                37.421841564778745, -122.16534327410872),
    "Mars":             ("Mars",                        37.422763024854305, -122.16860162250052),
    "Sigma Nu":         ("Sigma Nu",                    37.42233763919645,  -122.16839909387218),
    "Xanadu":           ("Xanadu",                      37.42302484559174, -122.16922612522727) 
}

# Housing data from 2025-26 UG Housing Chart (studenthousing.stanford.edu)
# Years: 1=Frosh, 2=Soph, 3=Junior, 4=Senior
DORM_METADATA = {
    # Frosh only
    "Branner":         {"complex": "Branner",            "capacity": 168, "years": [1]},
    "Crothers":        {"complex": "Crothers",           "capacity": 129, "years": [1]},
    "Alondra":         {"complex": "Florence Moore",     "capacity":  67, "years": [1], "theme": "SLE"},
    "Mirlo":           {"complex": "Florence Moore",     "capacity":  85, "years": [1]},
    "Castano":         {"complex": "Gerhard Casper Quad","capacity": 107, "years": [1]},
    "Lantana":         {"complex": "Gerhard Casper Quad","capacity": 113, "years": [1]},
    "Robinson":        {"complex": "Governor's Corner",  "capacity":  90, "years": [1]},
    "Schiff":          {"complex": "Governor's Corner",  "capacity":  93, "years": [1]},
    "West Lagunita":   {"complex": "Lagunita",           "capacity": 142, "years": [1]},
    "Donner":          {"complex": "Stern",              "capacity":  93, "years": [1]},
    "Larkin":          {"complex": "Stern",              "capacity": 104, "years": [1]},
    "Arroyo":          {"complex": "Wilbur",             "capacity":  82, "years": [1]},
    "Cedro":           {"complex": "Wilbur",             "capacity":  94, "years": [1]},
    "Rinconada":       {"complex": "Wilbur",             "capacity":  94, "years": [1]},
    "Soto":            {"complex": "Wilbur",             "capacity":  94, "years": [1]},

    # 4 class
    "Cardenal":        {"complex": "Florence Moore",     "capacity":  67, "years": [1,2,3,4], "theme": "SLE"},
    "Potter":          {"complex": "Governor's Corner",  "capacity":  89, "years": [1,2,3,4], "theme": "Explore Energy"},
    "Ujamaa":          {"complex": "Lagunita",           "capacity": 109, "years": [1,2,3,4], "theme": "Black Diaspora"},
    "Burbank":         {"complex": "Stern",              "capacity":  84, "years": [1,2,3,4], "theme": "ITALIC+Arts"},
    "Casa Zapata":     {"complex": "Stern",              "capacity":  84, "years": [1,2,3,4], "theme": "Chicanx/Latinx"},
    "Okada":           {"complex": "Wilbur",             "capacity":  78, "years": [1,2,3,4], "theme": "Asian American"},
    "Otero":           {"complex": "Wilbur",             "capacity":  79, "years": [1,2,3,4], "theme": "Public Service"},
    "Muwekma-Tah-Ruk": {"complex": "Row",                "capacity":  32, "years": [1,2,3,4], "theme": "Indigenous"},

    # Sophomore/Junior/Senior
    "Crothers Memorial":{"complex": "Crothers",          "capacity": 208, "years": [2,3,4]},
    "Faisan":          {"complex": "Florence Moore",     "capacity":  65, "years": [2,3,4]},
    "Gavilan":         {"complex": "Florence Moore",     "capacity":  55, "years": [2,3,4]},
    "Loro":            {"complex": "Florence Moore",     "capacity":  69, "years": [2,3,4]},
    "Paloma":          {"complex": "Florence Moore",     "capacity":  51, "years": [2,3,4]},
    "Kimball":         {"complex": "Gerhard Casper Quad","capacity": 208, "years": [2,3,4]},
    "Ng":              {"complex": "Gerhard Casper Quad","capacity": 125, "years": [2,3,4], "theme": "Humanities"},
    "Adams":           {"complex": "Governor's Corner",  "capacity":  92, "years": [2,3,4]},
    "EAST":            {"complex": "Governor's Corner",  "capacity":  61, "years": [2,3,4]},
    "Murray":          {"complex": "Governor's Corner",  "capacity":  59, "years": [2,3,4]},
    "Yost":            {"complex": "Governor's Corner",  "capacity":  61, "years": [2,3,4]},
    "Adelfa":          {"complex": "Lagunita",           "capacity":  48, "years": [2,3,4]},
    "Meier":           {"complex": "Lagunita",           "capacity": 109, "years": [2,3,4]},
    "Naranja":         {"complex": "Lagunita",           "capacity":  45, "years": [2,3,4]},
    "Norcliffe":       {"complex": "Lagunita",           "capacity": 109, "years": [2,3,4]},
    "Roble Hall":      {"complex": "Roble Hall",              "capacity": 303, "years": [2,3,4]},
    "Sally Ride":      {"complex": "Stern",              "capacity":  94, "years": [2,3,4]},
    "Twain":           {"complex": "Stern",              "capacity": 106, "years": [2,3,4]},
    "Toyon":           {"complex": "Toyon",              "capacity": 211, "years": [2,3,4]},
    "Junipero":        {"complex": "Wilbur",             "capacity":  94, "years": [2,3,4]},
    "Trancos":         {"complex": "Wilbur",             "capacity":  85, "years": [2,3,4], "theme": "Outdoor House"},
    "576 Alvarado":    {"complex": "Row",                "capacity":  32, "years": [2,3,4], "theme": "Co-op"},
    "aKDPhi/Chi Omega":{"complex": "Row",                "capacity":  26, "years": [2,3,4], "theme": "Greek"},
    "Alpha Phi/KKG":   {"complex": "Row",                "capacity":  54, "years": [2,3,4], "theme": "Greek"},
    "Columbae":        {"complex": "Row",                "capacity":  53, "years": [2,3,4], "theme": "Co-op"},
    "Delta Delta Delta":{"complex": "Row",               "capacity":  55, "years": [2,3,4], "theme": "Greek"},
    "Enchanted Broccoli Forest":{"complex":"Row",        "capacity":  54, "years": [2,3,4], "theme": "Co-op"},
    "Hammarskjold":    {"complex": "Row",                "capacity":  33, "years": [2,3,4], "theme": "Co-op"},
    "Kairos":          {"complex": "Row",                "capacity":  36, "years": [2,3,4], "theme": "Co-op"},
    "Kappa Alpha":     {"complex": "Row",                "capacity":  49, "years": [2,3,4], "theme": "Greek"},
    "Kappa Alpha Theta":{"complex":"Row",                "capacity":  54, "years": [2,3,4], "theme": "Greek"},
    "Kappa Sigma":     {"complex": "Row",                "capacity":  55, "years": [2,3,4], "theme": "Greek"},
    "Phi Kappa Psi":   {"complex": "Row",                "capacity":  39, "years": [2,3,4], "theme": "Greek"},
    "Pi Beta Phi":     {"complex": "Row",                "capacity":  53, "years": [2,3,4], "theme": "Greek"},
    "Robert Moore North":{"complex":"Row",               "capacity":  51, "years": [2,3,4], "theme": "Wellness"},
    "Sigma Nu":        {"complex": "Row",                "capacity":  42, "years": [2,3,4], "theme": "Greek"},
    "Sigma Phi Epsilon":{"complex":"Row",                "capacity":  55, "years": [2,3,4], "theme": "Greek"},
    "Synergy":         {"complex": "Row",                "capacity":  50, "years": [2,3,4], "theme": "Co-op"},
    "Terra":           {"complex": "Row",                "capacity":  54, "years": [2,3,4], "theme": "Co-op"},

    # Junior/Senior 
    "550 Lasuen":      {"complex": "Row",                "capacity":  40, "years": [3,4]},
    "680 Lomita":      {"complex": "Row",                "capacity":  57, "years": [3,4]},
    "BOB":             {"complex": "Row",                "capacity":  58, "years": [3,4]},
    "Durand":          {"complex": "Row",                "capacity":  35, "years": [3,4]},
    "Grove":           {"complex": "Row",                "capacity":  34, "years": [3,4]},
    "Jerry":           {"complex": "Row",                "capacity":  49, "years": [3,4]},
    "Mars":            {"complex": "Row",                "capacity":  36, "years": [3,4]},
    "Narnia":          {"complex": "Row",                "capacity":  53, "years": [3,4]},
    "Neptune":         {"complex": "Row",                "capacity":  49, "years": [3,4]},
    "Pluto":           {"complex": "Row",                "capacity":  41, "years": [3,4]},
    "Roth":            {"complex": "Row",                "capacity":  38, "years": [3,4]},
    "Storey":          {"complex": "Row",                "capacity":  51, "years": [3,4]},
    "Toussaint":       {"complex": "Row",                "capacity":  43, "years": [3,4]},
    "Warehaus":        {"complex": "Row",                "capacity":  37, "years": [3,4]},
    "Xanadu":          {"complex": "Row",                "capacity":  60, "years": [3,4]},
    "ZAP":             {"complex": "Row",                "capacity":  53, "years": [3,4]},
    "Govco Suites":    {"complex": "Governor's Corner",  "capacity": 257, "years": [3,4]},
    "Mirrielees":      {"complex": "Mirrielees",         "capacity": 389, "years": [3,4]},
    "EVGR":      {"complex": "EVGR",         "capacity": 450, "years": [3,4]},  # TODO: this is an estimate, idk if its still accurate
}

def dorms_for_year(year):
    return [k for k, m in DORM_METADATA.items() if year in m['years']]

# Combined lookup for convenience
ALL_LOCATIONS = {**BUILDING_LOCATIONS, **DINING_LOCATIONS, **DORM_LOCATIONS}

# Map location string from Explore Courses to (name, lat, lon)
# if unresolvable, fall back to subject-based home building
def get_building_location(location_str, subject=None):
    if location_str:
        loc = str(location_str).strip()
        
        # Try direct resolution first
        if loc and loc not in {"Remote", "Departmental Room",
                                "FILTER OUT", "School of Medicine Room"}:
            # Numbered building format: "160-120" -> prefix "160"
            if loc[0].isdigit() and "-" in loc:
                prefix = loc.split("-")[0]
                if prefix in BUILDING_LOCATIONS:
                    return BUILDING_LOCATIONS[prefix]

            # Named building: try each key as a prefix match
            for key in BUILDING_LOCATIONS:
                if loc.startswith(key):
                    return BUILDING_LOCATIONS[key]

            # Try partial match anywhere in string
            for key in BUILDING_LOCATIONS:
                if key.lower() in loc.lower():
                    return BUILDING_LOCATIONS[key]

    # Fallback: subject-based home building
    if subject and subject in SUBJECT_TO_HOME_BUILDING:
        home = SUBJECT_TO_HOME_BUILDING[subject]
        if home in BUILDING_LOCATIONS:
            return BUILDING_LOCATIONS[home]

    return None


if __name__ == "__main__":
    import osmnx as ox
    import pandas as pd
    import matplotlib.pyplot as plt

    print("Loading campus graph...")
    G = ox.graph_from_place("Stanford University, California", network_type="walk")

    df = pd.read_csv(COURSES_RAW)

    matched = 0
    unmatched = set()
    for loc in df['building'].dropna().unique():
        result = get_building_location(loc)
        if result:
            matched += 1
        else:
            unmatched.add(loc)

    total = df['building'].dropna().nunique()
    print(f"Matched: {matched}/{total} unique building codes")
    if unmatched:
        print(f"\nStill unmatched ({len(unmatched)}):")
        for u in sorted(unmatched):
            print(f"  {u}")

    # Visualize
    print("\nGenerating map...")
    fig, ax = ox.plot_graph(
        G,
        figsize=(16, 16),
        node_size=2,
        node_color="#cccccc",
        edge_linewidth=0.5,
        edge_color="#aaaaaa",
        bgcolor="white",
        show=False,
        close=False,
    )

    seen = set()
    for key, (name, lat, lon) in BUILDING_LOCATIONS.items():
        if (lat, lon) in seen:
            continue
        
        seen.add((lat, lon))
        ax.scatter(lon, lat, c="red", s=60, zorder=5)
        ax.annotate(
            name[:25],
            xy=(lon, lat),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=5,
            color="darkred",
            zorder=6
        )

    plt.savefig(OUTPUTS / "buildings_verified.png", dpi=200, bbox_inches="tight")
    print(f"Saved {OUTPUTS / 'buildings_verified.png'}")