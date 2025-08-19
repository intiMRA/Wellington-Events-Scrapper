import json
training_file_name = "training_data.json"
unclassified_file_name = "unclassified_data.json"
with open("events.json", mode="r") as events_file:
    events = json.loads(events_file.read())["events"]
    events = [event for event in events if event["long_description"] and event["eventType"] != "Other"]
    with open(training_file_name, mode="r") as read_training_file:
        training_data = json.loads(read_training_file.read())
        training_data += [{"new": True, "description": event["name"] + ", " + event["long_description"], "label": event["eventType"]} for event in events if event]
        final = []
        for t in training_data:
            if t in final:
                continue
            final.append(t)
        training_data = sorted(final, key=lambda k: k["label"])
        with open(training_file_name, mode="w") as training_file:
            json.dump(training_data, training_file, indent=2)