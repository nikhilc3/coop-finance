"""Wide sweep over the career-ops employer registry.

career-ops (github.com/career-ops-hq/career-ops) keeps a community list of ~17,000 company job boards in employers/boards
(data licensed CC BY 4.0). The workflow sparse-clones just that folder into ext/career-ops; this module reads every US
Greenhouse, Lever, Ashby, SmartRecruiters and Workday board on it, keeps only titles that look like a finance/business
internship or co-op, pulls those postings' descriptions, and caches them in data/registry_raw.json.

  python -m scraper.sources_registry           # sweep (GitHub Actions, once a day; ~20-30 min)
  main.py reads the cache on every run, so hourly runs reuse the last sweep.
"""
import concurrent.futures as cf
import glob
import json
import os
import re
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import fetchers, filters  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.environ.get("CAREER_OPS_BOARDS", os.path.join(ROOT, "ext", "career-ops", "employers", "boards"))
CACHE = os.path.join(ROOT, "data", "registry_raw.json")
ATS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workday")
THREADS = int(os.environ.get("REGISTRY_THREADS", "48"))
_get = fetchers._get


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- board list
def load_boards(skip=()):
    """Every live US board on the registry, minus boards config/companies.json already reads (skip = set of (ats, id))."""
    rows, seen = [], set()
    for ats in ATS:
        for path in sorted(glob.glob(os.path.join(REG, ats, "*.ndjson"))):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if r.get("retired"):
                        continue
                    if ats in ("greenhouse", "lever") and r.get("region", "us") != "us":
                        continue   # EU-hosted boards
                    if ats == "workday" and r.get("workday_host", "jobs") != "jobs":
                        continue
                    k = (ats, r["board"].lower())
                    if k in seen or k in skip:
                        continue
                    seen.add(k)
                    rows.append({"ats": ats, "board": r["board"], "name": r.get("name") or r["board"]})
    return rows


def skip_set(companies):
    s = set()
    for c in companies:
        a = c.get("ats")
        if a in ("greenhouse", "lever", "ashby"):
            s.add((a, str(c.get("token", "")).lower()))
        elif a == "smartrecruiters":
            s.add((a, str(c.get("slug", "")).lower()))
        elif a == "workday":
            s.add((a, f"{c.get('tenant')}/{c.get('host')}/{c.get('site')}".lower()))
    return s


# ---------------------------------------------------------------- cheap title screen
SUMMER_ANALYST = re.compile(r"summer analyst|analyst (intern|program)|internship program", re.I)


def looks_relevant(title, location=""):
    """Title-only screen before any description fetch: intern/co-op + a finance/business word, not engineering, US."""
    job = {"title": title, "location": location or ""}
    if not filters.is_intern(job):
        return False
    if filters.EXCLUDE_TITLE.search(title) and not re.search(r"\b(financial|finance|accounting|business) (analyst|intern)", title, re.I):
        return False
    if filters.NON_US.search(location or ""):
        return False
    if filters.PAST_RE.search(title) or (re.search(r"\b2026\b", title) and "2027" not in title):
        return False
    return bool(filters.hardware_score(job) or SUMMER_ANALYST.search(title))


def _job(name, title, location, url, posted, desc, ats):
    return dict(company=name, title=title, location=location or "", url=url, posted=(posted or "")[:10],
                description=fetchers._strip_html(desc or "")[:6000], source=f"careerops-{ats}", tier="")


# ---------------------------------------------------------------- per-ATS readers (titles first, details for survivors)
def greenhouse(b):
    j = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{b['board']}/jobs", timeout=25))
    out = []
    for p in j.get("jobs", []):
        loc = (p.get("location") or {}).get("name", "")
        if not looks_relevant(p.get("title", ""), loc):
            continue
        desc = ""
        try:
            d = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{b['board']}/jobs/{p['id']}", timeout=25))
            desc = d.get("content", "")
        except Exception:
            pass
        out.append(_job(b["name"], p["title"], loc, p.get("absolute_url", ""), p.get("updated_at"), desc, "greenhouse"))
    return out


def lever(b):
    j = json.loads(_get(f"https://api.lever.co/v0/postings/{b['board']}?mode=json", timeout=25))
    out = []
    for p in j if isinstance(j, list) else []:
        loc = (p.get("categories") or {}).get("location", "")
        if looks_relevant(p.get("text", ""), loc):
            created = p.get("createdAt")
            posted = date.fromtimestamp(created / 1000).isoformat() if isinstance(created, (int, float)) else ""
            out.append(_job(b["name"], p["text"], loc, p.get("hostedUrl", ""), posted,
                            p.get("descriptionPlain") or p.get("description", ""), "lever"))
    return out


def ashby(b):
    j = json.loads(_get(f"https://api.ashbyhq.com/posting-api/job-board/{b['board']}?includeCompensation=false", timeout=40))
    out = []
    for p in j.get("jobs", []):
        if p.get("isListed") is False:
            continue
        if looks_relevant(p.get("title", ""), p.get("location", "")):
            out.append(_job(b["name"], p["title"], p.get("location", ""), p.get("jobUrl") or p.get("applyUrl", ""),
                            p.get("publishedAt"), p.get("descriptionHtml") or p.get("descriptionPlain", ""), "ashby"))
    return out


def smartrecruiters(b):
    out, ids = [], set()
    for q in ("intern", "co-op", "summer analyst"):
        j = json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{b['board']}/postings?limit=100&q={q.replace(' ', '%20')}",
                            timeout=25))
        for p in j.get("content") or []:
            if p.get("id") in ids:
                continue
            ids.add(p.get("id"))
            loc = p.get("location") or {}
            l = loc.get("fullLocation") or ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
            if loc.get("country") and str(loc.get("country")).lower() not in ("us", "usa", "united states"):
                continue
            if not looks_relevant(p.get("name", ""), l):
                continue
            desc = ""
            try:
                d = json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{b['board']}/postings/{p['id']}", timeout=25))
                secs = ((d.get("jobAd") or {}).get("sections") or {})
                desc = " ".join((secs.get(k) or {}).get("text", "") for k in ("jobDescription", "qualifications", "additionalInformation"))
            except Exception:
                pass
            out.append(_job(b["name"], p.get("name", ""), l, f"https://jobs.smartrecruiters.com/{b['board']}/{p.get('id')}",
                            p.get("releasedDate"), desc, "smartrecruiters"))
    return out


def workday(b):
    tenant, host, site = b["board"].split("/", 2)
    base = f"https://{tenant}.{host}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    c = {"tenant": tenant, "host": host, "site": site, "name": b["name"]}
    out, seen = [], set()
    for term in ("intern", "co-op", "summer analyst"):
        for offset in (0, 20, 40):
            for attempt in range(3):
                try:
                    j = json.loads(_get(api, data={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term}, timeout=25))
                    break
                except Exception as e:  # Workday's WAF answers bursts with 429
                    if "429" in str(e) and attempt < 2:
                        time.sleep(3 * (attempt + 1))
                        continue
                    raise
            posts = j.get("jobPostings", [])
            for p in posts:
                path = p.get("externalPath", "")
                if not path or path in seen:
                    continue
                seen.add(path)
                if not looks_relevant(p.get("title", ""), p.get("locationsText", "")):
                    continue
                job = _job(b["name"], p.get("title", ""), p.get("locationsText", ""), f"{base}/{site}{path}", "", "", "workday")
                job["posted"] = p.get("postedOn", "")
                try:
                    job["description"] = fetchers._strip_html(fetchers.workday_detail(c, job))[:6000]
                except Exception:
                    pass
                out.append(job)
            if offset + 20 >= j.get("total", 0) or not posts:
                break
    return out


READERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters, "workday": workday}


def sweep(companies=(), limit=None):
    boards = load_boards(skip_set(companies))
    if limit:
        boards = boards[:limit]
    from collections import Counter
    log(f"career-ops registry: {len(boards)} boards", dict(Counter(b["ats"] for b in boards)))
    jobs, fails, done, t0 = [], Counter(), 0, time.time()
    with cf.ThreadPoolExecutor(max_workers=THREADS) as ex:
        futs = {ex.submit(READERS[b["ats"]], b): b for b in boards}
        for fut in cf.as_completed(futs):
            b = futs[fut]
            done += 1
            try:
                got = fut.result()
                jobs += got
                for j in got:
                    log(f"  + {b['name'][:28]:28s} {j['title'][:70]}")
            except Exception as e:  # noqa
                fails[b["ats"]] += 1
            if done % 1000 == 0:
                log(f"  ... {done}/{len(boards)} boards, {len(jobs)} postings, {time.time()-t0:.0f}s")
    log(f"registry sweep: {len(jobs)} postings from {len(boards)} boards in {time.time()-t0:.0f}s; failed boards {dict(fails)}")
    return jobs


def load_cache(log=log):
    """Postings from the last sweep (main.py calls this every run)."""
    if not os.path.exists(CACHE):
        return []
    try:
        d = json.load(open(CACHE, encoding="utf-8"))
    except ValueError:
        return []
    log(f"career-ops registry cache ({d.get('swept', '?')}): {len(d.get('jobs', []))} postings")
    return d.get("jobs", [])


if __name__ == "__main__":
    cfg = os.path.join(ROOT, "config", "companies.json")
    companies = json.load(open(cfg)) if os.path.exists(cfg) else []
    dc = os.path.join(ROOT, "data", "discover_config.json")
    if os.path.exists(dc):
        companies += json.load(open(dc))
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if not os.path.isdir(REG):
        log(f"no registry at {REG} (the workflow sparse-clones career-ops first)"); sys.exit(0)
    jobs = sweep(companies, lim)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump({"swept": date.today().isoformat(), "jobs": jobs}, open(CACHE, "w"), indent=0)
