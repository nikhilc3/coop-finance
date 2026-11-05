# Handoff: set up coop-finance for this user

You are a Claude session on the user's computer. Your job is to get this project running under **the user's own
GitHub account**. Read this file, then README.md, then do the steps below. Keep the user's effort to a minimum:
run the commands yourself, and only ask the user for things you can't do (signing in, choosing names).

## What this is

A job scraper that runs on GitHub Actions every hour (7am to 8pm ET). It finds **summer 2027 internships** and
**fall 2027 co-ops** (Northeastern fall co-op, roughly Jul to Dec 2027) in **finance and business**. Results go to:

- a GitHub Pages website (`index.html` reads the CSVs in `data/`)
- phone push notifications via ntfy.sh
- a GitHub Issue per batch of new postings (GitHub emails the owner)

It was adapted from a friend's hardware/chip version (github.com/hrisheekmust-blip/coop-scraper). The auto-apply
parts of that project are deliberately left out. This repo only finds postings.

## How it works (files that matter)

- `scraper/main.py`: the pipeline. It fetches, classifies, diffs against `data/seen.json`, then writes `data/`.
- `scraper/filters.py`: what is kept. It requires an intern/co-op/"summer analyst" title with finance or business
  keywords, and drops engineering/software, MBA/grad-only, non-US, spring 2027 only, and 2026 terms.
- Ranks: A means summer or fall 2027 is stated, B is a co-op with no term, C is an intern with no term.
- `scraper/fit.py`: the FINANCE / BUSINESS / MAYBE / OTHER label.
- `scraper/priority.py`: urgency bands and the board CSVs (`sheet.csv`, `watchlist.csv`, `openings.csv`).
- `scraper/alerts.py`: the GitHub Issue and the ntfy push. The first run only seeds state, so it sends no alerts.
- `config/companies.json`: companies with known job-board details. Only JPMorgan (Oracle HCM) is there.
- `config/candidates.json`: about 70 finance/business employers. `scraper/discover.py` probes Workday, Greenhouse,
  Lever, Ashby, iCIMS and others. It writes `data/discover_config.json`, which `main.py` merges in automatically.
- `.github/workflows/daily.yml`: runs every hour.
  - Discovery runs on the first run (when `data/discover_config.json` doesn't exist yet), monthly, or when
    triggered manually with the "discover" input.
- `scraper/jobspy_search.py`: the LinkedIn/Indeed searches.
- `scraper/sources_internlist.py`: the internlist.org (Simplify) Boston, NYC and co-op lists.
- `scraper/nuworks_crawl.js` and `scraper/nuworks.py`: NUWorks support.
  - The JS runs in the user's logged-in NUWorks tab and downloads `coop_nuworks.json`.
  - Committing that file to `data/browser/coop_nuworks.json` makes the next run add those postings.

## Verified vs not verified

- Verified offline: the filter rules on sample titles, a full pipeline run on fake data, and the board rendering on
  desktop and mobile with no JS errors.
- Not verified (the build machine couldn't reach job boards):
  - Which of the 70 candidate companies discovery actually resolves.
  - Whether the internlist Boston/NYC list IDs are found at runtime. If not, those two lists are skipped with a log line.
  - Whether the LinkedIn/Indeed queries return good results.

## Steps

1. Ask the user for:
   - their GitHub username (they need an account)
   - an ntfy topic name that nobody could guess (for example `name-fin-` plus 4 random characters)
   - whether they want Boston-only or all US. The default is all US. Boston-only would mean adding a location check
     in `filters.classify`.
2. Unzip the folder somewhere sensible, for example `~/Documents/coop-finance`.
3. Make sure `git` and the GitHub CLI `gh` are installed. If `gh auth status` fails, run `gh auth login` and let the
   user finish the browser sign-in.
4. From inside the folder:
   ```
   git init -b main && git add . && git commit -m "initial commit"
   gh repo create coop-finance --public --source=. --push
   gh api -X PUT repos/{owner}/coop-finance/actions/permissions/workflow -f default_workflow_permissions=write
   gh api -X POST repos/{owner}/coop-finance/pages -f "source[branch]=main" -f "source[path]=/"
   gh variable set NTFY_TOPIC --body "<topic>"
   gh workflow run daily.yml
   ```
   - The repo must be public. That keeps Actions minutes and Pages free.
   - Have the user install the ntfy app and subscribe to the topic.
5. Watch the first run with `gh run watch`. It can take up to about 30 minutes because discovery probes every candidate.
6. After it finishes, `git pull` and check:
   - `data/discover.log`: how many candidates resolved. For important misses (Fidelity, State Street, Wellington,
     Bank of America, the Big 4), find the real job-board URL on the company's careers site and add an entry to
     `config/companies.json`. The formats are in README.md ("Adding a company").
     - A Workday URL looks like `https://<tenant>.wdN.myworkdayjobs.com/<site>`.
     - Oracle HCM uses a host plus a `siteNumber`.
     - Greenhouse and Lever use a board token.
   - `data/run.log`: look for `internlist:boston ... list id not found` (same for nyc). If you see it, open the
     internlist.org list page in a browser and read the uuid from the network request to
     `api.simplify.jobs/v2/job-list/:id/<uuid>/...`. Put that uuid as the fallback in `LISTS` in
     `sources_internlist.py`.
   - `data/rejected.jsonl`: skim for real finance roles that were wrongly dropped, and fix `filters.py` if needed.
   - The board at `https://<username>.github.io/coop-finance/` loads and shows postings.
7. Commit and push any fixes, trigger one more run, and confirm the second run sends a phone alert if anything is new.
8. NUWorks (optional, recommended for Northeastern business co-ops): walk the user through the crawl in the README
   once. That means pasting `scraper/nuworks_crawl.js` into the DevTools console on the NUWorks job search page, then
   committing the downloaded file to `data/browser/`.
   - You can also automate the commit and push with a small daily scheduled task on their computer.

## Things to avoid

- Don't add the user's personal info (phone, email, resume) to this repo. It's public.
- Don't re-add auto-apply features unless the user asks. That is a much bigger setup.
- Keep the hourly schedule. Don't add a faster one: finance postings don't move that fast, and it just makes noisy commits.
