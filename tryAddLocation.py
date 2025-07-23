import json

import FileNames
import Summarizer
from EventInfo import EventInfo
from CoordinatesMapper import CoordinatesMapper
import FileUtils
stored_events = FileUtils.load_event()
# location_events = []
# for event in stored_events:
#     if event.coordinates:
#         location_events.append(event)
#     else:
#         location = CoordinatesMapper.get_coordinates(event.venue)
#         if location:
#             event.coordinates = location
#         location_events.append(event)
# FileUtils.write_to_events_file(location_events)

# description_events = []
# for event in stored_events:
#     if not event.description:
#         description_events.append(event)
#     else:
#         event_description = EventInfo.clean_html_tags(event.description)
#         if event_description:
#             event_description = Summarizer.sumerize(event_description)
#             event.description = event_description
#         description_events.append(event)
# FileUtils.write_to_events_file(description_events)

