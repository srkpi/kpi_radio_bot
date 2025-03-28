import json

with open("schedule.json", "r", encoding="utf-8") as file:
    SCHEDULE: dict[str, object] = json.load(file)
