from src.config.config import read_config
from src.api.api_request import Query
from src.util.datestamps import span_month


def commons_data_check():
	if not request_commons_snapshot():
		exit("Commons data not available yet")


def request_commons_snapshot(category=None):
	base_url = format_commons_base_url()
	if not category:
		category = read_config("main_category")
	first, last = span_month(read_config("year"), read_config("month"), inclusive=False, datestamp=False)
	url = "{}/{}/{}/{}/{}".format(base_url,
	                              "category-metrics-snapshot",
	                              category,
	                              first,
	                              last)

	r = Query(url=url, method="GET", headers=read_config("headers"))

	if r.response.status_code == 200:
		return r.response.json()
	else:
		return False


def get_category_details(category):
	counts = {"org_images_loaded": 0,
	          "org_images_used": 0,
	          "pages_using_org_images": 0,
	          "wikis_using_org_images": 0}

	snapshot_data = request_commons_snapshot(category)
	if snapshot_data:
		details = snapshot_data["items"][0]
		if details:
			counts["org_images_loaded"] = details["media-file-count-deep"]
			counts["org_images_used"] = details["used-media-file-count-deep"]
			counts["pages_using_org_images"] = details["leveraging-page-count-deep"]
			counts["wikis_using_org_images"] = details["leveraging-wiki-count-deep"]

	return counts


def get_totals_by_wiki(category, main_langs=None):
	base_url = format_commons_base_url()
	traffic = {"traffic_for_pages_using_org_images": 0}
	if main_langs:
		for lang in main_langs:
			traffic.update({lang: 0})
	year = read_config("year")
	month = read_config("month")
	if month < 10:
		month = "0{}".format(str(month))
	url = "{}/{}/{}/{}/{}/{}".format(base_url,
	                                    "top-wikis-per-category-monthly",
	                                    category,
	                                    "deep",
	                                    year,
	                                    month)

	r = Query(url=url, method="GET", headers=read_config("headers"))

	if r.response.status_code == 200:
		details = r.response.json().get("items")
		if details:
			for wiki in details:
				wiki_lang = wiki["wiki"].split(".")[0]
				if main_langs:
					if wiki_lang in main_langs:
						traffic["traffic_for_pages_using_org_images_{}".format(wiki_lang)] = wiki["pageview-count"]
				traffic["traffic_for_pages_using_org_images"] += wiki["pageview-count"]

	return traffic


def format_commons_base_url():
	url = "{}/{}".format(read_config("base_url"),
	                           read_config("commons_slug"))
	return url
