# ALL DATA FILE PATHS
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Data dirs
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"

# Raw inputs
COURSES_RAW = RAW / "courses_2025_2026.csv"
GEOCODED_BUILDINGS = RAW / "geocoded_buildings.json"

# Pipeline outputs
COURSES_TAGGED = PROCESSED / "courses_spring_2026_tagged.csv"
STUDENTS = PROCESSED / "students.csv"
STUDENTS_EXTENDED = PROCESSED / "students_with_behaviors.csv"
SCHEDULES = PROCESSED / "schedules.csv"

# Make sure output dirs exist when module is imported
OUTPUTS.mkdir(exist_ok=True)
PROCESSED.mkdir(exist_ok=True)