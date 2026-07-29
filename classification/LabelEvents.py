from util import FileNames
from classification import TextClassifier
from util import FileUtils
from util import paths

events = FileUtils.load_events(FileNames.EVENTS_COPY)
TextClassifier.classify_events(events, only_empty=False)
FileUtils.write_to_events_file(events, paths.data_path("events-labeled.json"))
