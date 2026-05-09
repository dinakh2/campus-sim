# Preprocess courses_2025_2026.csv -> Spring-only tagged file for assign_schedules.py
# Add: school, level_num, level, is_anchor, section_id
#
# section_id format: SUBJECT-COURSE_CODE-COMPONENT-SECTION_NUM
# (same section meeting MW + F shows up as 2 rows but shares 1 section_id)

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import COURSES_RAW, COURSES_TAGGED

INPUT  = COURSES_RAW
OUTPUT = COURSES_TAGGED

TERM = "2025-2026 Spring"

DROP_COMPONENTS = {"INS", "T/D", "RES", "ITR", "API"}

ANCHOR_PRIORITY = [
    "LEC", "SEM", "LAB", "LBS", "PRA", "COL", "WKS",
    "ACT", "ISF", "ISS", "CAS", "RSC", "SCS", "DIS",
]

SUBJECT_TO_SCHOOL = {
    # School of Engineering
    "CS":"engineering","EE":"engineering","ME":"engineering","BIOE":"engineering",
    "CHEMENG":"engineering","MS&E":"engineering","ENGR":"engineering","CEE":"engineering",
    # H&S Natural Sciences
    "MATH":"hs_natural","PHYSICS":"hs_natural","CHEM":"hs_natural","BIO":"hs_natural",
    "STATS":"hs_natural","HUMBIO":"hs_natural","DATASCI":"hs_natural",
    # H&S Social Sciences
    "ECON":"hs_social","PSYCH":"hs_social","POLISCI":"hs_social","SOC":"hs_social",
    "ANTHRO":"hs_social","COMM":"hs_social","PUBLPOL":"hs_social","SYMSYS":"hs_social",
    "HUMSCI":"hs_social",
    # H&S Humanities
    "ENGLISH":"hs_humanities","HISTORY":"hs_humanities","PHIL":"hs_humanities",
    "MUSIC":"hs_humanities","TAPS":"hs_humanities","FILMEDIA":"hs_humanities",
    "PWR":"hs_humanities","COLLEGE":"hs_humanities",
    # Doerr School of Sustainability
    "EARTHSYS":"doerr",
}


# Course code -> level bucket
#   <100   split: PWR + small components (SEM/ISF/etc) -> seminar,
#                 LEC/LAB -> intro (foundational stuff like MATH 51, CHEM 33)
#   100s   intro   (~soph)
#   200s   mid     (~junior)
#   300+   advanced (senior + grad cross-list)
# Without the <100 split, "seminar" gets dominated by big intro lectures
# and frosh enrollment patterns in assign_schedules.py get distorted.
def parse_level_num(course_code) -> int | None:
    # '106A' -> 106
    m = re.match(r"^(\d+)", str(course_code))
    return int(m.group(1)) if m else None


def level_bucket(level_num, subject, component) -> str:
    if level_num is None:
        return "unknown"
    if level_num < 100:
        if subject == "PWR":
            return "seminar"
        if component in ("LEC", "LAB"):
            return "intro"
        return "seminar"
    if level_num < 200:
        return "intro"
    if level_num < 300:
        return "mid"
    return "advanced"


def main():
    df = pd.read_csv(INPUT)
    print(f"Loaded {len(df)} rows from {INPUT}")

    df = df[df["term"] == TERM].copy()
    print(f"After term filter ({TERM}): {len(df)} rows")

    before = len(df)
    df = df[~df["component"].isin(DROP_COMPONENTS)].copy()
    print(f"After dropping {sorted(DROP_COMPONENTS)}: {len(df)} rows (-{before - len(df)})")

    df["school"]    = df["subject"].map(SUBJECT_TO_SCHOOL).fillna("unknown")
    df["level_num"] = df["course_code"].apply(parse_level_num)
    df["level"] = df.apply(
        lambda r: level_bucket(r["level_num"], r["subject"], r["component"]),
        axis=1,
    )

    df["section_id"] = (
        df["subject"].astype(str) + "-"
        + df["course_code"].astype(str) + "-"
        + df["component"].astype(str) + "-"
        + df["section_num"].astype(str).str.zfill(2)
    )

    priority_rank = {c: i for i, c in enumerate(ANCHOR_PRIORITY)}
    df["_rank"] = df["component"].map(priority_rank).fillna(999).astype(int)
    
    course_min_rank = df.groupby(["subject", "course_code"])["_rank"].transform("min")
    df["is_anchor"] = df["_rank"] == course_min_rank
    df = df.drop(columns=["_rank"])

    # ---- sanity checks ----
    anchor_unique = df[df["is_anchor"]].drop_duplicates("section_id")

    print("\n=== School distribution (anchor rows, deduped) ===")
    school_enroll = anchor_unique.groupby("school")["curr_enrolled"].sum().sort_values(ascending=False)
    
    total = school_enroll.sum()
    for sch, n in school_enroll.items():
        print(f"  {sch:18s} {int(n):6d}  ({n/total*100:5.1f}%)")

    print("\n=== Level distribution (anchor rows, deduped) ===")
    print(anchor_unique["level"].value_counts())

    print("\n=== School x level seats (anchor enrollment) ===")
    print(pd.crosstab(anchor_unique["school"], anchor_unique["level"],
                      values=anchor_unique["curr_enrolled"], aggfunc="sum",
                      margins=True, margins_name="TOTAL").fillna(0).astype(int))

    # Sanity check <100 split routing
    print("\n=== <100 course routing (after split rule) ===")
    under100 = anchor_unique[anchor_unique["level_num"] < 100]
    print(under100.groupby(["level"]).agg(
        sections=("section_id","count"),
        enrolled=("curr_enrolled","sum")
    ))

    print("\n=== Top 10 <100 courses now classified as 'intro' ===")
    intro_promo = under100[under100["level"]=="intro"].sort_values("curr_enrolled", ascending=False)
    print(intro_promo[["subject","course_code","component","curr_enrolled"]].head(10).to_string(index=False))

    print("\n=== Top 10 <100 courses still 'seminar' ===")
    still_sem = under100[under100["level"]=="seminar"].sort_values("curr_enrolled", ascending=False)
    print(still_sem[["subject","course_code","component","curr_enrolled"]].head(10).to_string(index=False))

    unknown = df[df["school"] == "unknown"]["subject"].unique()
    if len(unknown):
        print(f"\n!! UNMAPPED SUBJECTS: {sorted(unknown)}")
    else:
        print("\n[OK] All subjects have a school mapping")

    courses_with_anchor = set(map(tuple, df[df["is_anchor"]][["subject","course_code"]].drop_duplicates().values))
    all_courses = set(map(tuple, df[["subject","course_code"]].drop_duplicates().values))
    
    orphans = all_courses - courses_with_anchor
    if orphans:
        print(f"!! {len(orphans)} courses have no anchor: {sorted(orphans)[:5]}")
    else:
        print("[OK] Every course has at least one anchor row")

    n_anchor = anchor_unique.shape[0]
    n_linked = df[~df["is_anchor"]].drop_duplicates("section_id").shape[0]
    print(f"\nAnchor offerings: {n_anchor}  Linked sections: {n_linked}")

    df.to_csv(OUTPUT, index=False)
    print(f"\nWrote {len(df)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()