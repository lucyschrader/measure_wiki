import json
import csv

file = "editedarticles_en"

data = None

with open(file + ".json", "r", encoding="utf-8") as f:
	data = json.load(f)

if data:
	filtered_data = [data[page]["url"] for page in data.keys() if data[page]["page_type"] == "article"]

	out = file + ".csv"
	with open(out, "w+", encoding="utf-8") as outfile:
		writer = csv.writer(outfile, delimiter=",")
		for url in filtered_data:
			writer.writerow([url])
