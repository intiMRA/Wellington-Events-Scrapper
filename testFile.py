import FileUtils

events = FileUtils.load_events()
events = [event for event in events if event.source == "Facebook"]
total = len(events)
c = 0

for event in events:
    if "oe=" not in event.image:
        print(event.image)
    if FileUtils.is_facebook_url_expired_now(event.image):
        c += 1
print(f"total: {total}")
print(f"missing: {c}")
print(f"percent: {c/total}")