import src.util.memo as memo
from src.util.connect import get_site, connect_to_page, load_revision, compare_diff
from tqdm import tqdm
import re
from bs4 import BeautifulSoup


def process_contributions():
    for edit in tqdm(memo.edits, desc="Processing edits"):
        compare_edits(edit)


def apply_contributions():
    for edit in tqdm(memo.edits, desc="Applying edits"):
        update_memo(edit)


def compare_edits(edit):
    site_id = edit["site"]
    title = edit["title"]

    site_details = memo.sites[site_id]
    site_classifications = {k:v for k, v in site_details["report_elements"].items()
                                if site_details["report_elements"][k]["report_type"] == "classification"}
    edit["classifications"] = classify_edit(site_classifications, edit)
    revid = edit["revid"]

    edit["new"], edit["diff"], edit["diff_details"] = get_diff_details(site_id, title, revid)


def update_memo(edit):
    site_id = edit["site"]
    pageid = edit["pageid"]
    h_username = edit["user"]
    page_key = "{s}:{i}".format(s=site_id, i=pageid)
    page_memo = memo.pages[page_key]

    if not page_memo["new"]:
        if edit["new"]:
            memo.pages[page_key]["new"] = edit["new"]
            memo.pages[page_key]["creator"] = h_username


def get_diff_details(site_id, title, revid):
    site = get_site(site_id)
    page = connect_to_page(site, title)

    user_revision = load_revision(site, page, revid)
    if user_revision:
        user_revision_size = user_revision["size"]
        parent_revid = user_revision["parentid"]
        if parent_revid > 0:
            parent_revision = load_revision(site, page, parent_revid)
            if parent_revision:
                try:
                    if "wikipedia" in site_id:
                        diff_details = compare_revisions(site, parent_revision, user_revision)
                    else:
                        diff_details = None
                    parent_revision_size = parent_revision["size"]
                    diff_size = user_revision_size - parent_revision_size
                    return False, diff_size, diff_details
                except KeyError:
                    return None, None, None
        else:
            if "wikipedia" in site_id:
                rev_text = page.getOldVersion(revid)
                w, c, im, inf = check_single_diff(rev_text)
                diff_details = {"words_added": w,
                                "cites_added": len(c),
                                "images_added": len(im),
                                "infobox_added": inf}
                return True, user_revision_size, diff_details
            else:
                return True, user_revision_size, None

    return None, None, None


def compare_revisions(site, parent_rev, edit_rev):
    diff_list = compare_diff(site, parent_rev, edit_rev)
    diff_list_deleted = diff_list.get("deleted-context")
    diff_list_added = diff_list.get("added-context")

    if len(diff_list_deleted) > 0:
        words_del, cites_del, img_del, infobox = diff_deletions(diff_list_deleted)
    else:
        words_del, cites_del, img_del, infobox = 0, [], [], False

    return diff_additions(diff_list_added,
                          words_del,
                          cites_del,
                          img_del,
                          infobox)


def diff_deletions(deletions):
    wordcount = 0
    cites = []
    images = []
    infobox = False
    for diff_del in deletions:
        w, c, im, inf = check_single_diff(diff_del)
        wordcount -= w
        cites.extend(c)
        images.extend(im)
        infobox = inf

    return wordcount, cites, images, infobox


def diff_additions(additions, words_del, cites_del, images_del, infobox):
    words_added = 0
    cites_add = []
    images_add = []
    new_infobox = False

    for diff_add in additions:
        w, c, im, inf = check_single_diff(diff_add)
        words_added += w
        cites_add.extend(c)
        images_add.extend(im)
        if not infobox:
            new_infobox = inf

    words_added = words_added - words_del
    new_cites = diff_citations(cites_del, cites_add)
    new_images = diff_images(images_del, images_add)

    return {"words_added": words_added,
            "citations_added": len(new_cites),
            "images_added": len(new_images),
            "infobox_added": new_infobox}


def check_single_diff(string):
    words_added = count_words(string)
    cites_add = find_cites(string)
    images_add = find_images(string)
    infobox = find_infobox(string)

    return words_added, cites_add, images_add, infobox


def count_words(string):
    # Strips text inside templates ("{{...}}") to get a more accurate word count
    string = re.sub(r'\{\{.+?}}', '', string)

    return len(re.findall(r'\w+', string))


def find_cites(string):
    # Checks for new named sources, not individual references
    citations = []
    try:
        soup = BeautifulSoup(string, 'html.parser')
        refs = soup.find_all("ref")
        for ref in refs:
            if ref.get("name"):
                citations.append(ref["name"])
    except TypeError as e:
        print(e)

    citations = list(set(citations))
    return citations


def find_images(string):
    # Finds new individual images, may not work for all formats
    images = []
    image_strings = re.findall(r'\[\[File:.+]]', string)
    for img_link in image_strings:
        params = img_link.split("|")
        images.append(params[0].split(":")[1])
    return images


def find_infobox(string):
    template_labels = ["{{Infobox", "{{Taxobox"]
    for label in template_labels:
        if label in string:
            return True
    return False


def diff_citations(cites_del, cites_add):
    new_citations = []
    for cite in cites_add:
        if cite not in cites_del:
            new_citations.append(cite)

    return new_citations


def diff_images(images_del, images_add):
    new_images = []
    for image in images_add:
        if image not in images_del:
            new_images.append(image)

    return new_images


def classify_edit(site_classifications, edit):
    classifications = {}

    comment = edit['comment']
    tags = "|".join(edit['tags'])
    for cat in site_classifications.keys():
        cat_label = site_classifications[cat]["name"]
        count = False
        if site_classifications[cat].get("summary"):
            for summary_string in site_classifications[cat]["summary"]:
                if summary_string.lower() in comment.lower():
                    count = True
        if site_classifications[cat].get("tags"):
            for tag_string in site_classifications[cat]["tags"]:
                if tag_string.lower() in tags.lower():
                    count = True

        if count:
            classifications[cat_label] = True

    return classifications


def identify_page_type(title, site_details):
    page_type = None
    page_types = site_details["page_types"]
    for possible_type in page_types.keys():
        if page_types[possible_type].get("slugs"):
            for slug in page_types[possible_type]["slugs"]:
                if slug in title:
                    page_type = possible_type
    if not page_type:
        page_type = site_details["core_type"]["name"]

    return page_type
