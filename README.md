# coop-finance

Scans job boards every hour for **summer 2027 internships** and **fall 2027 co-ops** in finance and business, keeps only
the relevant ones, and shows them on a simple website. New postings get pushed to your phone.

Built on the same engine as [hrisheekmust-blip/coop-scraper](https://github.com/hrisheekmust-blip/coop-scraper), retuned for finance.

## What it searches

- **Company job boards**: Fidelity, State Street, Wellington, JPMorgan, Bank of America, the Big 4, BCG/Bain, Liberty Mutual,
  and about 70 others (see `config/candidates.json`). The first run figures out which job system each company uses.
- **LinkedIn and Indeed**: about 20 searches like "corporate finance intern 2027" and "finance co-op fall 2027".
- **internlist.org** (Simplify's index): the Boston, NYC and co-op lists.
- **NUWorks**: only if you run the crawl script yourself (it's behind Northeastern login). See below.

## What it keeps

- Titles with finance or business words: corporate finance, FP&A, treasury, accounting, audit, tax, investment banking,
  equity research, asset/wealth management, risk, consulting, strategy, business analyst, operations, and so on.
- Bank-style vague titles too, like "2027 Summer Analyst Program", at companies on the list.
- Drops: engineering/software roles, MBA/grad-only roles, non-US locations, spring 2027 only, anything for 2026.
- Ranks: **A** = summer or fall 2027 stated, **B** = co-op with no term stated, **C** = internship with no term stated.

## Setup (about 20 minutes, all in the browser)

1. Make a GitHub account if you don't have one.
2. Create a new **public** repository named `coop-finance` (public is what makes the website and hourly runs free).
3. On the repo page click **Add file → Upload files**, drag in everything from this folder, and commit.
   Note: the `.github` folder is hidden on Mac/Windows. Turn on hidden files before dragging, or create
   `.github/workflows/daily.yml` by hand with **Add file → Create new file** and paste its contents.
4. **Settings → Actions → General**: under "Workflow permissions" pick **Read and write permissions**, save.
5. **Settings → Pages**: Source = **Deploy from a branch**, Branch = `main`, folder `/ (root)`, save.
   Your board will be at `https://<your-username>.github.io/coop-finance/`.
6. Phone alerts: install the free **ntfy** app, subscribe to a topic name nobody would guess (like `jdoe-fin-8x2k`).
   Then in the repo: **Settings → Secrets and variables → Actions → Variables → New repository variable**,
   name `NTFY_TOPIC`, value = that topic name.
7. **Actions tab → finance co-op scrape → Run workflow**. The first run takes longer (up to ~30 minutes) because it
   works out each company's job system. After that it runs every hour from 7am to 8pm ET.

The first run fills the board but sends no alerts (otherwise you'd get hundreds). Alerts start from the second run.
GitHub also emails you a summary each time something new shows up (it opens an Issue in the repo).

## NUWorks (optional, recommended)

A lot of Northeastern business co-ops are only on NUWorks.

1. Log in to NUWorks in Chrome and go to the job search page.
2. Open DevTools (F12) → **Console**, paste everything from `scraper/nuworks_crawl.js`, press Enter.
3. It clicks through the listings for a few minutes, then downloads `coop_nuworks.json`.
4. In the repo, go into `data/browser/`, click **Add file → Upload files**, upload that file, commit.
   The next hourly run puts those postings on the board.

Do this once or twice a week.

## Changing what it looks for

- Add a company: add `{"name": "...", "slugs": ["..."], "careers": "https://...", "tier": "big"}` to
  `config/candidates.json`, then **Run workflow** with "also run ATS discovery" ticked.
- Change keywords or term rules: `scraper/filters.py` (what's kept) and `scraper/fit.py` (Finance vs Business label).
- Change LinkedIn/Indeed searches: `scraper/jobspy_search.py`.
- See why something was dropped: `data/rejected.jsonl`.
- The Watchlist tab on the board flags any company whose feed stops returning postings.

## Not included

The auto-apply tools from the original project are left out. This repo only finds postings.
