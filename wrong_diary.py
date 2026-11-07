"""Find appointments booked in a diary other than the patient's registered clinician.

Usage: python3 wrong_diary.py SITE_ID FROM_DATE TO_DATE [BOOKED_BY_USER_ID] > out.csv
Dates are YYYY-MM-DD (TO_DATE exclusive). Prints a CSV; summary goes to stderr.
"""
import csv
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

from dentally import DentallyClient

LONDON = ZoneInfo("Europe/London")
# (diary practitioner, patient's registered practitioner) pairs that are fine.
# Henry Chang (366384) is covering Gayle MacVicar's (184354) diary.
ALLOWED = {(366384, 184354)}


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(LONDON)


def main(site_id, start, end, booked_by=None):
    c = DentallyClient()
    prac = {p["id"]: p for p in c.paginate("practitioners", "practitioners", site_id=site_id)}
    users = {}

    def pname(i):
        if i in prac:
            u = prac[i]["user"]
            return f"{u['first_name']} {u['last_name']}".title()
        return f"#{i}" if i else "none"

    def uname(i):
        if i is None:
            return "none"
        if i not in users:
            try:
                u = c.get(f"users/{i}")["user"]
                users[i] = " ".join(f"{u['first_name']} {u['last_name']}".split())
            except Exception:
                users[i] = f"user #{i}"
        return users[i]

    appts = [a for a in c.paginate("appointments", "appointments", site_id=site_id,
                                   after=f"{start}T00:00:00Z", before=f"{end}T00:00:00Z")
             if a["patient_id"] and a["state"] != "Cancelled"
             and (booked_by is None or a["user_id"] == booked_by)]
    ids = sorted({a["patient_id"] for a in appts})
    with ThreadPoolExecutor(8) as ex:
        patients = dict(zip(ids, ex.map(lambda i: c.get(f"patients/{i}")["patient"], ids)))

    rows = []
    for a in appts:
        p = patients[a["patient_id"]]
        diary = a["practitioner_id"]
        kind = prac[diary]["user"]["role"] if diary in prac else "?"
        expected = p["dentist_id"] if kind == "Dentist" else p["hygienist_id"]
        if expected == diary or (diary, expected) in ALLOWED:
            continue
        rows.append({
            "when": local(a["start_time"]).strftime("%a %d %b %H:%M"),
            "minutes": a["duration"],
            "patient": " ".join(f"{p['first_name']} {p['last_name']}".split()).title(),
            "patient_id": p["id"],
            "booked_in": pname(diary),
            "diary_type": kind,
            "registered": pname(expected),
            "registered_dentist": pname(p["dentist_id"]),
            "registered_hygienist": pname(p["hygienist_id"]),
            "reason": (a["reason"] or "").strip(),
            "state": a["state"],
            "booked_by": uname(a["user_id"]),
            "booked_on": local(a["created_at"]).strftime("%a %d %b %Y %H:%M"),
            "_t": a["start_time"],
        })
    rows.sort(key=lambda r: r["_t"])
    for r in rows:
        del r["_t"]
    print(f"checked {len(appts)} appointments, {len(rows)} flagged", file=sys.stderr)
    if rows:
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], int(args[3]) if len(args) > 3 else None)
