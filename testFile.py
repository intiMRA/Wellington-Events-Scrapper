import json
import random

with open("training_data_kid_friendly.json", mode="r") as f:
    full_set = json.loads(f.read())
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
