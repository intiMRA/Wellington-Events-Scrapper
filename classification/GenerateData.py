import json
import re
import random
from collections import Counter

from util import paths

GENERATED_FILE = paths.data_path("training/generated_data.json")
skip_strings = [
    "All Tickets are Mobile Ticket Only. \r\nMobile Tickets are like Print-at-Home tickets but instead of having to print off the tickets yourself, you can just show the barcode on your mobile phone. It is the easiest way to access tickets to your events. For more information visit Ticketmaster.co.nz/mobileticket",
    "BOK JOL WELLINGTON 2025, Age restriction. Under 18 only allowed with parents or legal guardian."
]

you_may_like_regex = "You may also like the following events from"
also_check_out_regex = "Also check out other"


def clean_data(key: str, events):
    for e in events:
        description = e[key]
        description = description.split(you_may_like_regex)[0]
        description = description.split(also_check_out_regex)[0]
        e[key] = description


def generate_kid_friendly():
    with open(paths.data_path("training/training_data_kid_friendly.json"), mode="r") as f:
        full_set = json.loads(f.read())
        clean_data("description", full_set)
        small_set = []
        trues = [t for t in full_set if t["kid_friendly"]]
        falses = [t for t in full_set if not t["kid_friendly"]]
        print(len(trues))
        print(len(falses))
        random.shuffle(trues)
        random.shuffle(falses)
        for i in range(1, len(trues)):
            small_set.append(falses[i])
        small_set += trues
        with open(paths.data_path("training/small_training_data_kid_friendly.json"), mode="w") as w:
            json.dump(small_set, w, indent=2)


def generate_data():
    """Ingest new events from events.json into generated_data.json. Any event with a
    long_description is added (unless its description is already present), labelled with its
    scraper eventType ("Other" when uncategorised) for later review/classification."""
    with open(paths.root_path("events.json"), mode="r") as events_file:
        events = json.loads(events_file.read())["events"]
    clean_data("long_description", events)
    events = [event for event in events if event["long_description"]]

    with open(GENERATED_FILE, mode="r") as f:
        data = json.loads(f.read())
    clean_data("description", data)

    existing = set(entry["description"] for entry in data)
    for event in events:
        description = event["name"] + ", " + event["long_description"]
        if description in existing:
            continue
        existing.add(description)
        data.append({"new": True, "description": description, "label": event["eventType"]})

    data = sorted(data, key=lambda k: k["description"])
    data = sorted(data, key=lambda k: k["label"])
    for entry in data:
        should_skip = False
        for skip_string in skip_strings:
            description = entry["description"]
            if (len(description) < 110
                    or skip_string in description
                    or len(re.sub(skip_string, "", description)) < 110):
                should_skip = True
                break
        entry["skip"] = should_skip

    with open(GENERATED_FILE, mode="w") as out:
        json.dump(data, out, indent=2)


def count_categories():
    with open(GENERATED_FILE, mode="r") as f:
        data = json.loads(f.read())
    counts = Counter(entry["label"] for entry in data if not entry.get("skip"))
    for category in sorted(counts):
        print(f"category: {category} count: {counts[category]}")


if __name__ == "__main__":
    generate_data()
    count_categories()
