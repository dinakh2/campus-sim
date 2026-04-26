from explorecourses import CourseConnection
import pandas as pd

connect = CourseConnection()
year = "2025-2026"

# Departments most relevant to undergrads (i think?)
DEPARTMENTS = [
    "CS", "EE", "MATH", "STATS", "PHYSICS", "CHEM", "BIO",
    "ECON", "PSYCH", "ENGLISH", "HISTORY", "POLISCI", "COMM",
    "ENGR", "ME", "CEE", "BIOE", "CHEMENG", "MS&E",
    "HUMBIO", "SYMSYS", "DATASCI", "EARTHSYS", "PUBLPOL",
    "ANTHRO", "SOC", "PHIL", "MUSIC", "TAPS", "FILMEDIA",
    "PWR", "HUMSCI", "THINK", "COLLEGE"
]

rows = []

for dept_code in DEPARTMENTS:
    print(f"Fetching {dept_code}...")
    try:
        courses = connect.get_courses_by_department(dept_code, year=year)
        for course in courses:
            for section in course.sections:
                # Drop if enrollment is less than 5, maybe change to be more accurate
                if section.max_class_size < 5:
                    continue
                for schedule in section.schedules:
                    rows.append({
                        "course_code": course.code,
                        "subject": course.subject,
                        "title": course.title,
                        "units_min": course.units_min,
                        "units_max": course.units_max,
                        "term": section.term,
                        "section_num": section.section_num,
                        "component": section.component,
                        "max_enrolled": section.max_class_size,
                        "curr_enrolled": section.curr_class_size,
                        "building": schedule.location,
                        "days": ",".join(schedule.days),
                        "start_time": schedule.start_time,
                        "end_time": schedule.end_time,
                        "start_date": schedule.start_date,
                        "end_date": schedule.end_date,
                    })

    except Exception as e:
        print(f"  Error on {dept_code}: {e}")
        continue

df = pd.DataFrame(rows)
df.to_csv("courses_2025_2026.csv", index=False)
print(f"\nSaved {len(df)} rows to courses_2025_2026.csv")
print(f"Unique buildings: {df['building'].nunique()}")
print(f"Max enrollment course: {df.loc[df['curr_enrolled'].idxmax(), 'title']} ({df['curr_enrolled'].max()} students)")
print(df.head(10))