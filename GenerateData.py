import json
training_file_name = "training_data.json"
unclassified_file_name = "unclassified_data.json"
with open("events.json", mode="r") as events_file:
    events = json.loads(events_file.read())["events"]
    events = [event for event in events if event["long_description"] and event["eventType"] != "Other"]
    with open(training_file_name, mode="r") as read_training_file:
        training_data = json.loads(read_training_file.read())
        descriptions = set([dictionary["description"] for dictionary in training_data])
        training_data += [{"description": event["name"] + ", " + event["long_description"], "label": event["eventType"]}
                          for event in events
                          if event and (event["name"] + ", " + event["long_description"]) not in descriptions]
        training_data = sorted(training_data, key=lambda k: k["label"])
        with open(training_file_name, mode="w") as training_file:
            json.dump(training_data, training_file, indent=2)