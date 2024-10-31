from src.config.config import loader, read_config
from src.util.measure_commons import commons_data_check
from src.util.connect import prepare_sites, get_user_contributions
import src.util.memo as memo
from src.util.processanalytics import process_contributions, apply_contributions, identify_page_type
from src.util.output import prepare_key_stats
from src.util.datestamps import span_month, backdate_months


def run():
	loader()
	commons_data_check()
	prepare_sites()
	users = memo.load_users()
	if read_config("use_saved_data"):
		# Only use when memo contains the month you're working on
		memo.load_memo()
	else:
		segment_months(users)

	if read_config("backdate"):
		store_urls()
	else:
		if not read_config("use_saved_data"):
			process_contributions()
			store_urls()
		apply_contributions()
		prepare_key_stats()


def segment_months(users):
	if read_config("backdate"):
		if read_config("backdate_users"):
			users = read_config("backdate_users")
		for year, month in backdate_months():
			first, last = span_month(year, month)
			retrieve_contributions(users, first, last)
	else:
		first, last = span_month(read_config("year"), read_config("month"))
		retrieve_contributions(users, first, last)


def retrieve_contributions(users, first, last):
	# Reset user status if getting a new month's data
	for user in users:
		memo.editors[user]["active"] = False

	for site_id in memo.sites.keys():
		for user in users:
			retrieve_user_activity(site_id, user, first, last)


def retrieve_user_activity(site_id, username, first, last):
	# Get the user's contributions for the last month
	site_details = memo.sites[site_id]
	contributions = get_user_contributions(site_details["site"], username, first, last)
	contribution_count = len(contributions)
	print(username, site_details["platform_label"], contribution_count)

	if contribution_count > 0:
		memo.editors[username]["active"] = True

	for con in contributions:
		pageid = con["pageid"]
		revid = con["revid"]
		title = con["title"]
		comment = con["comment"]
		tags = con["tags"]

		page_key = "{s}:{i}".format(s=site_id, i=pageid)
		if not memo.pages.get(page_key):
			page_type = identify_page_type(title, site_details)
			memo.pages.update({page_key: {"pageid": pageid,
			                              "title": title,
			                              "site": site_id,
			                              "page_type": page_type,
			                              "new": False}})

		if not read_config("backdate"):
			o_username = memo.obscure_username(username)
			memo.edits.append({"page_key": page_key,
			                   "pageid": pageid,
			                   "title": title,
			                   "user": o_username,
			                   "revid": revid,
			                   "comment": comment,
			                   "site": site_id,
			                   "tags": tags})


def store_urls():
	languages = read_config("languages")
	for lang in languages:
		site_id = "wikipedia:{}".format(lang)
		lang_data = {page_key:data for (page_key, data) in memo.pages.items() if memo.pages[page_key]["site"] == site_id}
		file_path = "src/resources/editedarticles_{}.json".format(lang)
		memo.update_url_dump(file_path, lang_data)

	commons_data = {page_key: data for (page_key, data) in memo.pages.items() if memo.pages[page_key]["site"] == "commons:commons"}
	commons_fp = "src/resources/editedimages.json"
	memo.update_url_dump(commons_fp, commons_data)

	wikidata_data = {page_key: data for (page_key, data) in memo.pages.items() if memo.pages[page_key]["site"] == "wikidata:wikidata"}
	wikidata_fp = "src/resources/editeditems.json"
	memo.update_url_dump(wikidata_fp, wikidata_data)

	if not read_config("backfill"):
		memo.save_memo()
