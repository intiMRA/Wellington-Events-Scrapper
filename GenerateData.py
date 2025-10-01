import json
import re
import random

training_file_name = "training_data.json"
unclassified_file_name = "unclassified_data.json"
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
    with open("training_data_kid_friendly.json", mode="r") as f:
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
        with open("small_training_data_kid_friendly.json", mode="w") as w:
            json.dump(small_set, w, indent=2)

def generate_data():
    with open("events.json", mode="r") as events_file:
        events = json.loads(events_file.read())["events"]
        clean_data("long_description", events)

        events = [event for event in events if event["long_description"] and event["eventType"] != "Other"]
        with open(unclassified_file_name, mode="r") as unclassified_file_read:
            unclassified_data = json.loads(unclassified_file_read.read())
            clean_data("description", unclassified_data)
            with open(training_file_name, mode="r") as read_training_file:
                descriptions = set([dictionary["description"] for dictionary in unclassified_data])
                new_events = []
                for event in events:
                    if (event["name"] + ", " + event["long_description"]) in descriptions:
                        continue
                    new_events.append(event)
                events = new_events
                training_data = json.loads(read_training_file.read())
                clean_data("description", training_data)
                descriptions = set([dictionary["description"] for dictionary in training_data])
                training_data += [{"new": True,
                                   "description": event["name"] + ", " + event["long_description"],
                                   "label": event["eventType"]}
                                      for event in events
                                      if
                                      event and (event["name"] + ", " + event["long_description"]) not in descriptions]
                training_data = sorted(training_data, key=lambda k: k["description"])
                training_data = sorted(training_data, key=lambda k: k["label"])
                for data in training_data:
                    should_skip = False
                    for skip_string in skip_strings:
                        description = data["description"]
                        if (len(description) < 110
                                or skip_string in description
                                or len(re.sub(skip_string, "", description)) < 110):
                            should_skip = True
                            break
                    data["skip"] = should_skip
                with open(training_file_name, mode="w") as training_file:
                    json.dump(training_data, training_file, indent=2)
def generate_unclassified_data():
    with open("events.json", mode="r") as events_file:
        events = json.loads(events_file.read())["events"]
        clean_data("long_description", events)
        events = [event for event in events if event["long_description"] and event["eventType"] == "Other"]
        with open(training_file_name, mode="r") as read_training_file:
            training_data = json.loads(read_training_file.read())
            clean_data("description", training_data)
            with open(unclassified_file_name, mode="r") as unclassified_file_read:
                descriptions = set([dictionary["description"] for dictionary in training_data])
                new_events = []
                for event in events:
                    if (event["name"] + ", " + event["long_description"]) in descriptions:
                        continue
                    new_events.append(event)
                events = new_events
                unclassified_data = json.loads(unclassified_file_read.read())
                clean_data("description", unclassified_data)
                descriptions = set([dictionary["description"] for dictionary in unclassified_data])
                unclassified_data += [{"new": True, "description": event["name"] + ", " + event["long_description"], "label": event["eventType"]}
                                  for event in events
                                  if event and (event["name"] + ", " + event["long_description"]) not in descriptions]
                unclassified_data = sorted(unclassified_data, key=lambda k: k["description"])
                unclassified_data = sorted(unclassified_data, key=lambda k: k["label"])
                for data in unclassified_data:
                    should_skip = False
                    for skip_string in skip_strings:
                        description = data["description"]
                        if (len(description) < 110
                                or skip_string in description
                                or len(re.sub(skip_string, "", description)) < 110):
                            should_skip = True
                            break
                    data["skip"] = should_skip
                with open(unclassified_file_name, mode="w") as training_file:
                    json.dump(unclassified_data, training_file, indent=2)

def count_categories():
    categories = {
    'Education & Learning': 0,
        'Business & Networking': 0,
        'Music & Concerts': 0,
        'Arts & Theatre': 0,
        'Markets & Fairs': 0,
        'Food & Drink': 0,
        'Festivals': 0,
        'Religion & Spirituality': 0,
        'Film & Media': 0,
        'Sports & Fitness': 0,
        'Health & Wellness': 0,
        'Conservation & Environment': 0,
        'Community & Culture': 0,
        'Hobbies & Interests': 0,
        'Government & Politics': 0,
        'Family Friendly': 0,
        'Classes & Workshops': 0
    }
    with open(training_file_name, mode="r") as read_training_file:
        with open("ai_generates.json", mode="r") as ai_file:
            training_data = json.loads(read_training_file.read())
            ai_data = json.loads(ai_file.read())
            training_data += ai_data
            for data in training_data:
                if data["skip"]:
                    continue
                categories[data["label"]] = categories[data["label"]] + 1
            for cat in sorted(categories):
                print(f"category: {cat} count: {categories[cat]}")

def print_duplicates():
    with open(training_file_name, mode="r") as f:
        data = json.loads(f.read())
        dictionary = {}

        for d in data:
            if d["skip"]:
                continue
            k = d["description"].split(",")[0]
            if k in dictionary:
                dictionary[k].append(d["label"])
            else:
                dictionary[k] = [d["label"]]
        for d in dictionary:
            if len(dictionary[d]) > 1:
                print(d)
                print(dictionary[d])
                if len(set(dictionary[d])) > 1:
                    print("DUPLICATES")
                print("-" * 100)
def move_top_n_shortest(num:int, category: str):
    with open("training_data.json", mode="r") as training_file_read:
        training_data = json.loads(training_file_read.read())
        with open("unclassified_data.json", mode="r") as unclassified_file_read:
            unclassified_data = json.loads(unclassified_file_read.read())
            category_training = [instance for instance in training_data if instance["label"] == category and not instance["skip"]]
            category_training = sorted(category_training, key=lambda x: len(x["description"]))[:num]
            training_data = [instance for instance in training_data if instance not in category_training]
            for instance in category_training:
                unclassified_data.append(instance)
            with open("training_data.json", mode="w") as training_file_write:
                json.dump(training_data, training_file_write, indent=2)
            with open("unclassified_data.json", mode="w") as unclassified_file_write:
                json.dump(unclassified_data, unclassified_file_write, indent=2)
def move_top_n_largest(num:int, category: str):
    with open("unclassified_data.json", mode="r") as unclassified_file_read:
        unclassified_data = json.loads(unclassified_file_read.read())
        with open("training_data.json", mode="r") as training_file_read:
            training_data = json.loads(training_file_read.read())
            training_titles = [element["description"].split(",")[0] for element in training_data]
            category_training = [instance for instance in unclassified_data
                                 if instance["label"] == category
                                 and not instance["skip"]
                                 and instance["description"].split(",")[0] not in training_titles]

            category_training = sorted(category_training, key=lambda x: len(x["description"]), reverse=True)[:num]
            unclassified_data = [instance for instance in unclassified_data if instance not in category_training]
            for instance in category_training:
                training_data.append(instance)
            with open("unclassified_data.json", mode="w") as training_file_write:
                json.dump(unclassified_data, training_file_write, indent=2)
            with open("training_data.json", mode="w") as unclassified_file_write:
                json.dump(training_data, unclassified_file_write, indent=2)

# generate_kid_friendly()
# move_top_n_shortest(2, "Community & Culture")
# move_top_n_largest(2, "Classes & Workshops")
generate_data()
generate_unclassified_data()
count_categories()
print_duplicates()