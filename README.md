# Track the impact of your GLAM on Wiki
This set of scripts help you understand the impact your Wiki-editing staff are having by collating and analysing their contributions across:
* various-language Wikipedias
* Wiki Commons
* Wikidata

It outputs a report showing total impact, and individualised reports for each editor.

The overall report tells you:
* How many edits made
* How many pages edited (overall, and articles/media/items)
* How many new articles/media/items created
* Monthly traffic for articles that have been edited
* How many of your collection images have been loaded to Commons
* Where your images are being used and the traffic to those pages
* Words, references, images and infoboxes added to articles

The editor reports provide similar information for their own contributions, and adds context that will help them demonstrate the value of this work to their managers.

## Looking out for your editors
Because this script fetches all the contributions your listed editors make (on or off the job), they're putting a lot of trust in you! Only add them if they understand what this means and agree.

The reports created only show aggregated numbers, but the stored data (`memo.json`) includes who has edited what so the individual reports can be generated. The stored usernames are lightly obscured so they can't be read at a glance, but it's not exactly secure.

## Still to do
* Add Wikisource analytics
* Add visualisations of impact
* Track longer-term impact, such as increased traffic/activity on pages you've edited

## How it works
For each editor you're tracking, the script uses [Pywikibot](https://doc.wikimedia.org/pywikibot/stable/index.html) to retrieve their contributions for a specified month across each Wiki Project - by default, Wikidata, Wikimedia Commons, and whichever language Wikipedias you choose.

It classifies each page, storing them so you build up a log of what your editors have worked on. Each edit is also checked for the kind and size of change made, which lets you see how many words, references etc have been added, plus which ones are new additions. This involves retrieving the content for the revision, and takes about 10 minutes per 1000 edits.

The script then uses [Wiki's REST API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/) to get monthly traffic for 'core' pages on each site - articles on Wikipedia, for example. It does this for pages edited this month as well as all the pages you have stored. It also takes about 10 minutes to get traffic for 1000 urls.

Commons numbers related to your organisation are retrieved using the [Commons analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/commons.html).

Note that because the data behind the Commons API takes a while to prepare, you may need to allow about a week after the end of the month to run this script.

Finally, it produces a csv with totals for the key stats across all your editors, and text files for each user that can be sent to them.

### Page types
`src/resources/site_details.yaml` contains information about each site, including the page types found there. The top `crosswiki` section includes the ones that exist on every wiki, like `User` and `Talk` pages, and the other sections have the page types that are unique to them.

When you want to get contributions to other language Wikipedias, make sure you add the url slugs for them in this file. For example, you need both `User:` and `Usario:` for it to work on English and Spanish Wikipedias.

The 'main' page type for each site sits under `core_type`, which is the default type if others don't apply, and is also the page type for which traffic is checked.

### Report elements
What elements the scripts checks for is set in `src/resources/site_details.yaml`. The ones that with `report_type: count` and `commons_count` are hooked up to specific parts of the script, but new `classification` elements can be added pretty easily.

```
    merged_items:
      name: merged_items
      label: Item merged
      report_type: classification
      for_user: true
      summary:
        - wbmergeitems
      tags:
        - "merge.js"
```

These check the edit's edit summary and tags for specified terms and mark it with the classification if they're found. The `label` displays in the reports output at the end, and `for_user` means it'll be included in the individual user reports.

`summary` and `tags` are lists of the terms to look for, and you can add as many variations as you need to ensure you're catching the right thing. If the edit has more than one of the set terms, it'll still just be counted once.

## How to run the script
Install the following packages:
* Requests
* BeautifulSoup
* PyYAML
* tqdm
* pywikibot

Rename `src/config/renametoconfig.yaml` to `config.yaml`. Under `usernames`, list the usernames of your editors.

Create a folder called `output_dir` at root level.

Set a `User-Agent` for querying the Commons analytics API, and add the name of the category for your images on Commons. Note that your category needs to be listed by the Commons analytics service for this to work. See https://wikitech.wikimedia.org/wiki/Commons_Impact_Metrics.

To gather a backlog of pages edited by your staff, set a year and month to backdate and set `backdate` to `True` before running. Later on you can list other editors under `backdate_users` to get their earlier pages.

To report on the most recent month, change `backdate` back to `False`, add the `year` and `month` and run.

By default the script checks Wikidata and Wikimedia Commons. To check Wikipedia, list the language codes you want to check under `languages` - for example, `en` for English Wikipedia.

To support testing, you can also set `use_saved_data` to `True` if you've already downloaded the data you need, and set `request_traffic` to `False` to save time.