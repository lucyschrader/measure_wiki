from pywikibot import Site, User, Page
from pywikibot import exceptions as pwbex
from pywikibot.data import api
from pywikibot.diff import html_comparator
from src.util.memo import sites, load_file
from src.config.config import read_config


def prepare_sites():
	site_details = load_file("src/resources/site_details.yaml")

	for lang in read_config("languages"):
		site_id = "wikipedia:{}".format(lang)
		retrieve_and_store_site(site_id, site_details, lang)

	retrieve_and_store_site("wikidata:wikidata", site_details)
	retrieve_and_store_site("commons:commons", site_details)

	if not read_config("quiet"):
		print(sites)


def retrieve_and_store_site(site_id, site_details, lang=None):
	get_site(site_id, lang)
	save_site_details(site_id, site_details)


def get_site(site_id, lang=None):
	if site_id in sites.keys():
		return sites[site_id]["site"]
	else:
		site = connect_to_site(site_id)
		sites[site_id] = {"site": site}
		sites[site_id]["site_id"] = site_id
		if lang:
			sites[site_id]["lang"] = lang
			sites[site_id]["platform_label"] = "{} Wikipedia".format(lang.upper())
		return site


def save_site_details(site_id, site_details):
	site_project_label = site_id.split(":")[0]
	this_site_details = site_details[site_project_label]
	if this_site_details.get("page_types"):
		this_site_details["page_types"].update(site_details["crosswiki"]["page_types"])
	else:
		this_site_details["page_types"] = site_details["crosswiki"]["page_types"]
	this_site_details["report_elements"].update(site_details["crosswiki"]["report_elements"])
	sites[site_id].update(this_site_details)


def connect_to_site(site_id):
	site = Site(site_id)
	if not read_config("quiet"):
		print("Sitename:", site.sitename)
	return site


def connect_to_user(site, username):
	user = User(site, username)
	return user


def connect_to_page(site, title):
	page = Page(site, title)
	return page


def load_revision(site, page, revid):
	try:
		site.loadrevisions(page=page, revids=[revid])
		revision = page._revisions[revid]
	except KeyError:
		revision = None

	return revision


def get_user_contributions(site, username, start_datestamp, end_datestamp):
	# Datestamps reversed because you start at the present and work backwards
	contributions = api.ListGenerator(
		'usercontribs',
		site=site,
		parameters=dict(
			ucprop='ids|title|timestamp|comment|flags|tags',
			ucuser=username,
			ucstart=end_datestamp,
			ucend=start_datestamp,
		)
	)
	contributions.set_maximum_items(10000)

	return [i for i in contributions]


def compare_diff(site, old_rev, diff_rev):
	try:
		diff_html = site.compare(old_rev, diff_rev, difftype="table")
	except pwbex.APIError:
		return {"deleted-context": [], "added-context": []}
	diff_list = html_comparator(diff_html)
	return diff_list
