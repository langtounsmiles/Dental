"""Minimal Dentally API client (https://developer.dentally.co).

Auth: set DENTALLY_TOKEN to your API access token. In the Claude Code cloud
environment the token is injected by the network proxy, so any placeholder
value (e.g. DENTALLY_TOKEN=proxy-injected) works there.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("DENTALLY_BASE_URL", "https://api.dentally.co/v1")
USER_AGENT = "LangTounSmiles-Dental/1.0"


class DentallyClient:
    def __init__(self, token=None, base_url=BASE_URL):
        self.token = token or os.environ.get("DENTALLY_TOKEN", "proxy-injected")
        self.base_url = base_url.rstrip("/")

    def get(self, path, **params):
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}/{path.lstrip('/')}" + (f"?{query}" if query else "")
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}",
            "User-Agent": USER_AGENT,  # Dentally rejects requests without one
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)

    def paginate(self, path, key, per_page=100, **params):
        """Yield every record of a paginated list endpoint."""
        page = 1
        while True:
            data = self.get(path, page=page, per_page=per_page, **params)
            yield from data.get(key, [])
            meta = data.get("meta", {})
            if page * per_page >= meta.get("total", 0):
                return
            page += 1

    def user(self):
        return self.get("user")["user"]

    def sites(self):
        return list(self.paginate("sites", "sites"))

    def appointments(self, site_id, on=None, before=None, after=None):
        return list(self.paginate("appointments", "appointments",
                                  site_id=site_id, on=on, before=before, after=after))

    def patients(self, site_id=None, query=None):
        return list(self.paginate("patients", "patients", site_id=site_id, query=query))


if __name__ == "__main__":
    client = DentallyClient()
    me = client.user()
    print(f"Connected as {me['first_name']} {me['last_name']} ({me['role']})")
    for site in client.sites():
        status = "active" if site["active"] else "inactive"
        print(f"  {site['name']}  [{status}]  {site['id']}")
    sys.exit(0)
