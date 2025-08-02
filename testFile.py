import FileUtils

events = FileUtils.load_events()
FileUtils.write_to_events_file(events)