import FileNames
import json
with open(FileNames.BURGERS, mode="r") as f:
    dic = json.loads(f.read())

burgers = dic["burgers"]

burgers = sorted(burgers, key=lambda b: b["name"])

dic["burgers"] = burgers

with open(FileNames.BURGERS, mode="w") as f:
    json.dump(dic, f, indent=2)