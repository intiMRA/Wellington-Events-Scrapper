import json
training_file_name = "training_data.json"
unclassified_file_name = "unclassified_data.json"

def generate_data():
    with open("events.json", mode="r") as events_file:
        events = json.loads(events_file.read())["events"]
        events = [event for event in events if event["long_description"] and event["eventType"] == "Other"]
        with open(unclassified_file_name, mode="r") as unclassified_file_read:
            unclassified_data = json.loads(unclassified_file_read.read())
            with open(training_file_name, mode="r") as read_training_file:
                descriptions = set([dictionary["description"] for dictionary in unclassified_data])
                new_events = []
                for event in events:
                    if (event["name"] + ", " + event["long_description"]) in descriptions:
                        continue
                    new_events.append(event)
                events = new_events
                training_data = json.loads(read_training_file.read())
                descriptions = set([dictionary["description"] for dictionary in training_data])
                training_data += [{"new": True, "description": event["name"] + ", " + event["long_description"],
                                       "label": event["eventType"]}
                                      for event in events
                                      if
                                      event and (event["name"] + ", " + event["long_description"]) not in descriptions]
                training_data = sorted(training_data, key=lambda k: k["label"])
                with open(training_file_name, mode="w") as training_file:
                    json.dump(training_data, training_file, indent=2)
def generate_unclassified_data():
    with open("events.json", mode="r") as events_file:
        events = json.loads(events_file.read())["events"]
        events = [event for event in events if event["long_description"] and event["eventType"] == "Other"]
        with open(training_file_name, mode="r") as read_training_file:
            training_data = json.loads(read_training_file.read())
            with open(unclassified_file_name, mode="r") as unclassified_file_read:
                descriptions = set([dictionary["description"] for dictionary in training_data])
                new_events = []
                for event in events:
                    if (event["name"] + ", " + event["long_description"]) in descriptions:
                        continue
                    new_events.append(event)
                events = new_events
                unclassified_data = json.loads(unclassified_file_read.read())
                descriptions = set([dictionary["description"] for dictionary in unclassified_data])
                unclassified_data += [{"new": True, "description": event["name"] + ", " + event["long_description"], "label": event["eventType"]}
                                  for event in events
                                  if event and (event["name"] + ", " + event["long_description"]) not in descriptions]
                unclassified_data = sorted(unclassified_data, key=lambda k: k["label"])
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
                categories[data["label"]] = categories[data["label"]] + 1
            for cat in sorted(categories):
                print(f"category: {cat} count: {categories[cat]}")

count_categories()
