from datetime import datetime, date
import calendar
from src.config.config import read_config


def span_month(year, month, inclusive=True, datestamp=True):
	# Generates a datestamp or date string for a given date and one month later
	start_of_month = datetime(year, month, 1)
	if inclusive:
		last_day_of_month = calendar.monthrange(year, month)[1]
		end_of_month = datetime(year, month, last_day_of_month)
	else:
		if month == 12:
			eom_year = year + 1
			eom_month = 1
		else:
			eom_year = year
			eom_month = month + 1
		end_of_month = datetime(eom_year, eom_month, 1)

	if datestamp:
		return start_of_month, end_of_month
	else:
		return start_of_month.strftime("%Y%m%d"), end_of_month.strftime("%Y%m%d")


def backdate_months():
	year = read_config("year")
	month = read_config("month")
	backdate_year = read_config("backdate_year")
	backdate_month = read_config("backdate_month")
	start_date = date(year, month, 1)
	backdate_date = date(backdate_year, backdate_month, 1)
	date_tuples = []
	while start_date >= backdate_date:
		if month == 1:
			month = 12
			year -= 1
		else:
			month -= 1
		date_tuples.append((year, month))
		start_date = date(year, month, 1)

	return date_tuples
