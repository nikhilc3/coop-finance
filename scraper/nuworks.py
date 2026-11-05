"""Convert the NUWorks crawl (coop_nuworks.json from the browser script) into data/nuworks.json.

NUWorks (Symplicity) sits behind SSO, so it is crawled from a logged-in browser tab rather than fetched here.
The browser dump has: title, badge ("Not Qualified" or ""), sub ("Company - City, State"), extra, and for
finance/business-looking rows: id, applicantType, length, deadline, majors, posType, why.
"""
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import filters  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = date.today().isoformat()


def convert(rows):
    prev = {}
    pp = os.path.join(ROOT, "data", "nuworks.json")
    if os.path.exists(pp):
        prev = {j["url"]: j.get("first_seen", TODAY) for j in json.load(open(pp))}
    out = []
    for r in rows:
        if not r.get("id"):
            continue  # only rows we opened have a stable link and term info
        company, _, location = (r.get("sub") or "").partition(" - ")
        text = " ".join([r.get("title", ""), r.get("applicantType", ""), r.get("extra", ""), r.get("length", "")])
        job = dict(company=company.strip(), title=r["title"], location=location.strip(),
                   url=f"https://northeastern-csm.symplicity.com/students/app/jobs/detail/{r['id']}",
                   posted="", description=text, source="nuworks")
        at = r.get("applicantType") or ""
        # NUWorks states the cycle exactly ("2027 - Fall"); trust it over the text rules
        if re.search(r"2027\s*-\s*(fall|summer)", at, re.I):
            term = "fall" if re.search(r"fall", at, re.I) else "summer"
            meta = {"term": term, "hw": filters.hardware_score(job)[:4] or ["maybe"], "rank": "A"}
        elif re.search(r"2027\s*-\s*spring|2026", at, re.I):
            continue   # spring 2027 cycle or an old posting: not his
        else:
            ok, why, meta = filters.classify(job)
            if not ok:
                if why in ("spring/winter only", "2026 term (past)"):
                    continue
                # NUWorks titles are terse ("Co-op"); keep any co-op/intern that the crawl opened
                if not filters.is_intern(job) and not re.search(r"co-?op", r.get("posType", "") + r.get("length", ""), re.I):
                    continue
                meta = {"term": filters.term_of(job), "hw": filters.hardware_score(job)[:4] or ["maybe"], "rank": "B"}
        term, rank = meta["term"], meta["rank"]
        out.append(dict(company=job["company"], title=job["title"], location=job["location"], url=job["url"],
                        term=term, rank=rank, hw=",".join(meta["hw"]), qualified=(r.get("badge") != "Not Qualified"),
                        applicantType=r.get("applicantType", ""), length=r.get("length", ""), deadline=r.get("deadline", ""),
                        majors=r.get("majors", ""), why=r.get("why", ""), first_seen=prev.get(job["url"], TODAY), last_seen=TODAY))
    return out


if __name__ == "__main__":
    src = sys.argv[1]
    rows = json.load(open(src, encoding="utf-8"))
    out = convert(rows)
    json.dump(out, open(os.path.join(ROOT, "data", "nuworks.json"), "w"), indent=1)
    print(f"{len(rows)} rows -> {len(out)} finance/business co-op/intern postings")
