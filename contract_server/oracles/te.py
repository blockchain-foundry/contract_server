import json

r = "[{'name': 'setWeather', 'inputs': [{'type': 'uint256', 'name': 'today'}], 'outputs': [], 'type': 'function', 'id': 1, 'constant': False}, {'name': 'setWeather2', 'inputs': [{'type': 'uint256', 'name': 'today'}, {'type': 'uint256', 'name': 'tom'}], 'outputs': [], 'type': 'function', 'id': 2, 'constant': False}, {'type': 'constructor', 'id': 3, 'inputs': []}]"
k = eval(r)
print(k[0])
