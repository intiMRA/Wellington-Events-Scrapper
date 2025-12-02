import FileNames
import TextClassifier
import FileUtils
classification_model, loaded_tokenizer, loaded_label_encoder = TextClassifier.load_models_from_file()
events_output_name = "events-labeled.json"
events = FileUtils.load_events(FileNames.EVENTS_COPY)
for event in events:
    event.labels = TextClassifier.predict_labels(classification_model, loaded_tokenizer, loaded_label_encoder, [event.name + "," + event.long_description])
FileUtils.write_to_events_file(events, events_output_name)