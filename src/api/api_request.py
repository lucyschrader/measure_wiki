import time
from requests import get, exceptions


class Query():
	def __init__(self,
	             method=None,
	             url=None,
	             allow_redirects=True,
	             timeout=5,
	             attempts=3,
	             sleep=0.1,
	             quiet=False,
	             headers=None):
		self.response = None

		for attempt in range(attempts):
			if not self.response:
				try:
					if not quiet:
						print("Requesting {}".format(url))
					if method == "GET":
						self.response = get(url, timeout=timeout, allow_redirects=allow_redirects, headers=headers)
					if self.response.status_code == 404:
						if "The date(s) you used are valid" in self.response.text:
							if not quiet:
								print("No data available for {} in this date range".format(url))
							break
				except exceptions.Timeout:
					if not quiet:
						print("{} timed out".format(url))
					time.sleep(sleep)
				except exceptions.ConnectionError:
					if not quiet:
						print("Disconnected trying to get {}".format(url))
					time.sleep(sleep)
				except exceptions.HTTPError:
					if not quiet:
						print("Error {e} trying to get {u}".format(e=self.response.status_code, u=url))
					time.sleep(sleep)

		if not self.response:
			if not quiet:
				print("Query {m} {u} failed".format(m=method, u=url))
