# Dental

Tools for working with our practices' data in [Dentally](https://developer.dentally.co).

## Dentally connection

`dentally.py` is a dependency-free Python client for the Dentally API.

```bash
export DENTALLY_TOKEN=<your access token>   # in Claude Code cloud sessions, any placeholder works
python3 dentally.py                          # prints the user and the sites it can reach
```

```python
from dentally import DentallyClient
c = DentallyClient()
sites = c.sites()
appts = c.appointments(site_id=sites[0]["id"], on="2026-11-09")
```

Never commit the token.
