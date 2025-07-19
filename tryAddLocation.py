from CoordinatesMapper import CoordinatesMapper
import FileUtils
stored_events = FileUtils.load_event()
location_events = []
for event in stored_events:
    if event.coordinates:
        location_events.append(event)
    else:
        location = CoordinatesMapper.get_coordinates(event.venue)
        if location:
            event.coordinates = location
        location_events.append(event)
FileUtils.write_to_events_file(location_events)