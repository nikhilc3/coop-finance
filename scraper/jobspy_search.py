"""Optional LinkedIn / Indeed / Glassdoor sweep via python-jobspy (speedyapply/JobSpy).

Best-effort: these sites rate-limit and change markup, so failures are logged and skipped, never fatal.
Installed only in the GitHub Actions run (see .github/workflows/daily.yml); locally `pip install python-jobspy`.
"""
QUERIES = [
    "finance intern summer 2027", "corporate finance intern 2027", "FP&A intern", "financial analyst intern 2027",
    "accounting intern summer 2027", "audit intern 2027", "tax intern summer 2027", "treasury intern",
    "investment banking summer analyst 2027", "equity research intern", "asset management intern 2027",
    "wealth management intern 2027", "private equity intern", "business analyst intern 2027", "strategy intern 2027",
    "consulting intern summer 2027", "finance co-op fall 2027", "accounting co-op fall 2027", "business co-op 2027",
    "finance co-op Boston", "summer analyst Boston",
]


def fetch_all(log=print, hours_old=72):
    try:
        from jobspy import scrape_jobs
    except ImportError:
        log("  jobspy not installed, skipping LinkedIn/Indeed sweep")
        return []
    out, seen = [], set()
    for q in QUERIES:
        try:
            df = scrape_jobs(site_name=["linkedin", "indeed"], search_term=q, location="United States",
                             results_wanted=40, hours_old=hours_old, country_indeed="USA", linkedin_fetch_description=True)
        except Exception as e:  # noqa
            log(f"  jobspy '{q}': FAILED {type(e).__name__}: {str(e)[:60]}")
            continue
        n = 0
        for _, r in df.iterrows():
            url = str(r.get("job_url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            n += 1
            out.append(dict(company=str(r.get("company") or ""), title=str(r.get("title") or ""), location=str(r.get("location") or ""),
                            url=url, posted=str(r.get("date_posted") or "")[:10], description=str(r.get("description") or "")[:3000],
                            source=f"jobspy:{r.get('site')}"))
        log(f"  jobspy '{q}': {n} new")
    return out
