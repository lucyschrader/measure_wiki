import src.util.memo as memo
from src.config.config import read_config
from src.util.datestamps import span_month
from src.api.api_request import Query
from src.util.measure_commons import get_category_details, get_totals_by_wiki
from tqdm import tqdm
import csv


def prepare_key_stats():
	# Todo: Add overall numbers for touched articles, items, images
	editor_count, active_editor_count = count_editors()
	key_stats = {"general": {"editor_count": editor_count,
	                         "active_editor_count": active_editor_count}}

	for site_id in memo.sites.keys():
		key_stats[site_id] = count_wiki_edits(memo.sites[site_id])

	# Then, send to output as csv and emailable reports
	export_full_report(key_stats)

	if not read_config("quiet"):
		print_key_stats(key_stats)

	editors = memo.editors.keys()
	for username in tqdm(editors, desc="Creating editor reports"):
		user_key_stats = {}
		for site_id in memo.sites.keys():
			user_key_stats[site_id] = count_wiki_edits(memo.sites[site_id], username)

		export_user_report(username, user_key_stats)


def export_full_report(stats):
	formatted_stats = flatten_stats(stats)
	export_path = "output_dir/wiki_key_stats.csv"
	export_csv(export_path, formatted_stats)


def flatten_stats(stats):
	rows = [("", "count")]
	for site_id, site_stats in stats.items():
		if site_id == "general":
			rows.append(("Editor count", site_stats["editor_count"]))
			rows.append(("Active editor count", site_stats["active_editor_count"]))
		else:
			site_details = memo.sites[site_id]
			for k, v in site_stats.items():
				k_label = lookup_key_label(k, site_details)
				if k_label:
					rows.append((k_label, v))

	return rows


def lookup_key_label(key, site_details):
	if "traffic_for_pages_using_org_images_" in key:
		lang = key.split("_")[-1]
		label = site_details["report_elements"]["traffic_for_pages_using_org_images"]["alt_label"]
		label = label.format(lang.upper())
		return label
	else:
		try:
			label = site_details["report_elements"][key]["label"]
			lang = site_details.get("lang")
			if "{l}" in label:
				label = label.replace("{l}", lang.upper())
			if "{c}" in label:
				sub_string = site_details["core_type"]["label_plural"]
				if label.startswith("{c}"):
					label = label.replace("{c}", sub_string.capitalize())
				else:
					label = label.replace("{c}", sub_string)
			if "{s}" in label:
				label = label.replace("{s}", site_details["platform_label"])
			return label
		except KeyError:
			return None


def export_csv(filepath, data):
	with open(filepath, "w+", newline="", encoding="utf-8") as outfile:
		writer = csv.writer(outfile, delimiter=",")
		for label, value in data:
			writer.writerow([label, value])


def export_user_report(username, stats):
	formatted_report = format_user_report(stats)
	filepath = "output_dir/{}_key_stats.txt".format(username)
	if formatted_report:
		with open(filepath, "w+", encoding="utf-8") as outfile:
			outfile.write(formatted_report)


def print_key_stats(key_stats):
	for site_id, site_stats in key_stats.items():
		if site_id == "general":
			print("Editor count:", site_stats["editor_count"])
			print("Active editor count:", site_stats["active_editor_count"])
		else:
			site_details = memo.sites[site_id]
			print(site_details["platform_label"])
			for k, v in site_stats.items():
				k_label = lookup_key_label(k, site_details)
				if k_label and v:
					print("{key}: {val}".format(key=k_label, val=v))


def count_editors():
	editor_count = len(memo.editors.keys())
	active_editor_count = len([ed for ed in memo.editors.keys() if memo.editors[ed]["active"]])
	return editor_count, active_editor_count


def count_wiki_edits(site_details, username=None):
	platform_name = site_details["platform_name"]
	full_url_list, core_url_list = build_page_lists(site_details, username)
	full_monthly_list, core_monthly_list = build_monthly_page_lists(site_details, username)

	crosswiki_counts = run_crosswiki_counts(site_details, full_url_list, core_url_list, full_monthly_list, core_monthly_list, username)
	if platform_name == "wikipedia":
		site_counts = run_wikipedia_counts(site_details, core_url_list, core_monthly_list)
	elif platform_name == "wikidata":
		site_counts = run_wikidata_counts(site_details, username)
	elif platform_name == "commons":
		site_counts = run_commons_counts(site_details, username)
	else:
		site_counts = None

	if site_counts:
		crosswiki_counts.update(site_counts)

	return crosswiki_counts


def run_crosswiki_counts(site_details, full_url_list, core_url_list, full_monthly_list, core_monthly_list, username=None):
	counts = {"any_page_all_time": 0,
	          "core_page_all_time": 0,
	          "any_page_this_month": 0,
	          "core_page_this_month": 0,
	          "new_page_this_month": 0,
	          "new_core_this_month": 0,
	          "any_edit_this_month": 0,
	          "core_edit_this_month": 0,
	          "core_major_edit_this_month": 0}

	if full_url_list:
		counts["any_page_all_time"] = len(full_url_list)
	if core_url_list:
		counts["core_page_all_time"] = len(core_url_list)

	if full_monthly_list:
		counts["any_page_this_month"] = len(full_monthly_list)
	if core_monthly_list:
		counts["core_page_this_month"] = len(core_monthly_list)

	counts["new_page_this_month"] = count_new_pages(full_monthly_list, username)
	counts["new_core_this_month"] = count_new_pages(core_monthly_list, username)

	counts["any_edit_this_month"] = count_edits(site_details, core=False, username=username)
	counts["core_edit_this_month"] = count_edits(site_details, core=True, username=username)
	counts["core_major_edit_this_month"] = count_major_edits(site_details, username)

	classified_edits = summarise_classified_edits(site_details, username)

	counts.update(classified_edits)

	return counts


def build_page_lists(site_details, username=None):
	if site_details["platform_name"] == "wikipedia":
		url_store = site_details["url_store"].format(site_details["lang"])
	else:
		url_store = site_details["url_store"]

	full_url_list = memo.load_file("src/resources/{}".format(url_store))
	core_url_list = reduce_url_list(full_url_list, site_details)

	if username:
		full_url_list, core_url_list = build_user_lists(site_details, username, full_url_list, core_url_list)

	return full_url_list, core_url_list


def build_monthly_page_lists(site_details, username=None):
	full_monthly_list = {page_key: data for page_key, data in memo.pages.items() if
	                        memo.pages[page_key]["site"] == site_details["site_id"]}
	core_monthly_list = reduce_url_list(full_monthly_list, site_details)

	if username:
		full_monthly_list, core_monthly_list = build_user_lists(site_details, username, full_monthly_list, core_monthly_list)

	return full_monthly_list, core_monthly_list


def build_user_lists(site_details, username, full_list, core_list):
	user_edits = get_site_edits(site_details, username)
	user_pagekeys = [edit["page_key"] for edit in user_edits]
	user_full_list = {page_key: full_list[page_key] for page_key in user_pagekeys}
	user_core_list = {page_key: core_list[page_key] for page_key in user_pagekeys if core_list.get(page_key)}

	return user_full_list, user_core_list


def reduce_url_list(page_list, site_details):
	core_type = site_details["core_type"]["name"]

	reduced_list = {page_key: page_data for page_key, page_data in page_list.items() if
	                    page_list[page_key]["page_type"] == core_type}

	return reduced_list


def run_wikipedia_counts(site_details, core_url_list, core_monthly_list):
	traffic_all_time = 0
	traffic_month = 0

	if read_config("request_traffic"):
		if not memo.sites[site_details["site_id"]].get("traffic_checked"):
			traffic_all_time = get_monthly_traffic(core_url_list, site_details)
			memo.sites[site_details["site_id"]]["traffic_checked"] = True
		else:
			traffic_all_time = sum_article_traffic(core_url_list)
		traffic_month = sum_article_traffic(core_monthly_list)

	return {"traffic_all_time": traffic_all_time,
	        "traffic_month": traffic_month}


def run_wikidata_counts(site_details, username=None):
	counts = summarise_classified_edits(site_details, username)
	return counts


def run_commons_counts(site_details, username=None):
	try:
		main_langs = site_details["report_elements"]["traffic_for_pages_using_org_images"]["main_langs"]
	except KeyError:
		main_langs = None

	category = read_config("main_category")

	if username:
		counts = {}
	else:
		if read_config("require_commons"):
			counts = get_category_details(category)
			counts.update(get_totals_by_wiki(category, main_langs))
		else:
			counts = {}
	counts.update(summarise_classified_edits(site_details, username=username))

	return counts


def get_monthly_traffic(pages, site_details):
	# Get traffic counts for a page list
	traffic = 0
	if site_details["platform_name"] == "wikipedia":
		domain = "{}.wikipedia.org".format(site_details["lang"])
	elif site_details["platform_name"] == "wikidata":
		domain = "wikidata.org"
	else:
		raise ValueError("No valid site id set")
	url_slugs = "/".join([read_config("base_url") + "/pageviews/per-article",
	                      domain,
	                      "all-access",
	                      "user"])
	first, last = span_month(read_config("year"), read_config("month"), datestamp=False)

	for page_key in tqdm(pages, desc="Getting traffic for {}".format(domain)):
		title = pages[page_key]["title"]
		page_type = pages[page_key]["page_type"]
		core_type = site_details["core_type"]["name"]
		if page_type == core_type:
			views = get_page_traffic(title, url_slugs, first, last)
			if page_key in memo.pages.keys():
				memo.pages[page_key]["traffic"] = views
			traffic += views

	return traffic


def get_page_traffic(title, url_slugs, first, last):
	# Retrieve traffic for a given page this month
	views = 0
	title = title.replace(" ", "_")
	title = title.replace("%3A", ":")
	query_url = "{}/{}/{}/{}/{}".format(url_slugs, title, "monthly", first, last)
	q = Query(method="GET", url=query_url, quiet=read_config("quiet"), headers=read_config("headers"))

	# Todo: check for redirects and update saved data
	if q.response.status_code == 200:
		try:
			resp_json = q.response.json()
			views = resp_json["items"][0]["views"]
		except (KeyError, IndexError):
			views = 0

	return views


def sum_article_traffic(page_list):
	# Sum traffic for a page list when traffic already retrieved
	traffic = 0
	for page_key in page_list.keys():
		try:
			url_traffic = memo.pages[page_key]["traffic"]
		except KeyError:
			url_traffic = 0
		traffic += url_traffic

	return traffic


def count_new_pages(page_list, username=None):
	# Count pages added this month from page list
	new_pages = [page_key for page_key in page_list.keys() if page_list[page_key]["new"]]
	if username:
		new_user_pages = [i for i in new_pages if memo.match_username(username, page_list[i].get("creator"))]
		return len(new_user_pages)
	else:
		return len(new_pages)


def get_site_edits(site_details, username=None):
	# Count number of edits this month for a given site
	if username:
		edits = [edit for edit in memo.edits if (edit["site"] == site_details["site_id"]) and (memo.match_username(username, edit["user"]))]
	else:
		edits = [edit for edit in memo.edits if edit["site"] == site_details["site_id"]]

	return edits

def count_edits(site_details, core=False, username=None):
	# Check for total edit counts
	edits = get_site_edits(site_details, username)
	if core:
		edits = [edit for edit in edits if memo.pages[edit["page_key"]]["page_type"] == site_details["core_type"]["name"]]

	return len(edits)


def count_major_edits(site_details, username=None):
	# Check for large diffs
	edits = get_site_edits(site_details, username)
	edits = [edit for edit in edits if check_for_major_diffs(edit)]

	return len(edits)


def check_for_major_diffs(edit):
	major_diff = False
	diff = edit.get("diff")
	if diff:
		if (diff > 500) or (diff < -500):
			major_diff = True

	return major_diff


def summarise_classified_edits(site_details, username=None):
	platform_name = site_details["platform_name"]
	site_classifications = {k: v for k, v in site_details["report_elements"].items()
	                        if site_details["report_elements"][k]["report_type"] == "classification"}
	cat_counts = {site_classifications[k]["name"]: 0 for k in site_classifications.keys()}

	edits = get_site_edits(site_details, username)
	for edit in edits:
		for cat in site_classifications.keys():
			cat_label = site_classifications[cat]["name"]
			if edit["classifications"].get(cat_label):
				cat_counts[cat_label] += 1

	if platform_name == "wikipedia":
		cat_counts.update({"words_added": 0,
		                   "citations_added": 0,
		                   "images_added": 0,
		                   "infoboxes_added": 0})
		for edit in edits:
			details = edit.get("diff_details")
			if details:
				if details.get("words_added"):
					cat_counts["words_added"] += details.get("words_added")
				if details.get("citations_added"):
					cat_counts["citations_added"] += details.get("citations_added")
				if details.get("images_added"):
					cat_counts["images_added"] += details.get("images_added")
				if details.get("infobox_added"):
					cat_counts["infoboxes_added"] += 1

	return cat_counts


def format_user_report(userdata):
	report_elements = []
	user_edited_wikipedia = False

	for site_id in userdata.keys():
		site_data = userdata[site_id]
		site_details = memo.sites[site_id]
		site_report_elements = ["Contributions to {}".format(site_details["platform_label"])]

		for k, v in site_data.items():
			if confirm_user_print(k, site_details):
				k_label = lookup_key_label(k, site_details)
				if k_label and v:
					site_report_elements.append("* {key}: {val}".format(key=k_label, val=v))

		if len(site_report_elements) > 1:
			if "wikipedia" in site_id:
				if not user_edited_wikipedia:
					site_report_elements.insert(0, memo.load_summary("wikipedia"))
				user_edited_wikipedia = True
			else:
				site_report_elements.insert(0, memo.load_summary(site_details["platform_name"]))

			formatted_site_data = "\n".join(site_report_elements)

			report_elements.append(formatted_site_data)

	formatted_report = "\n\n".join(report_elements)

	return formatted_report


def confirm_user_print(key, site_details):
	if site_details["report_elements"][key].get("for_user"):
		return True
