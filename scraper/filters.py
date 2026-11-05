"""Filtering + classification shared by every source. Tuned for a business / finance student who wants
summer 2027 internships and a fall 2027 co-op (Northeastern fall co-op runs roughly Jul-Dec 2027).

Everything here works on a normalized job dict:
  {company, title, location, url, posted, description(optional), source}

To retune for a different person, edit the keyword lists and the TARGET / DROP term rules below.
"""
import re

# ---- what counts as an intern/co-op posting -------------------------------
# banks call interns "Summer Analysts", so that counts too
LEVEL_RE = re.compile(r"\b(interns?|internships?|co-?ops?|coops?|student|university|undergrad(uate)?|summer analysts?|"
                      r"summer analyst program|off-?cycle analyst|campus)\b", re.I)

# ---- finance / business relevance -----------------------------------------
FINANCE = [
    "finance", "financial", "corporate finance", "fp&a", "fpa", "financial planning", "treasury", "accounting", "accountant",
    "audit", "assurance", "tax", "controller", "controllership", "investment banking", "banking", "ib", "capital markets",
    "equity research", "investment", "investments", "investment management", "asset management", "wealth management",
    "private wealth", "portfolio", "fixed income", "credit", "leveraged finance", "private equity", "venture capital",
    "real estate finance", "valuation", "m&a", "mergers", "corporate development", "transaction", "advisory",
    "risk", "compliance", "underwriting", "actuarial", "insurance", "trading", "sales & trading", "sales and trading",
    "markets", "global markets", "economics", "economic", "financial analyst", "fund accounting", "fund administration",
    "operations analyst", "pricing", "revenue", "billing", "payroll", "procurement finance", "cost", "budget",
]
BUSINESS = [
    "business analyst", "business analytics", "business operations", "business development", "strategy", "strategic",
    "consulting", "consultant", "management consulting", "operations", "commercial", "analyst", "analytics", "data analyst",
    "product operations", "corporate strategy", "investor relations", "sales operations", "revenue operations",
    "supply chain finance", "business intelligence", "project management", "program management", "rotational",
    "leadership development", "general management", "entrepreneurship", "marketing analytics",
]
_re = lambda words: re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in words) + r")(?![a-z])", re.I)
FIN_RE, BIZ_RE = _re(FINANCE), _re(BUSINESS)

# titles that are clearly not finance/business even if a matching word sneaks in ("Risk Engineer", "Tax Software")
EXCLUDE_TITLE = re.compile(
    r"\b(software|swe|engineer|engineering|developer|full[- ]stack|frontend|backend|devops|hardware|electrical|mechanical|"
    r"civil|chemical|nurse|nursing|clinical|pharmac|biolog|chemist|lab tech|technician|machinist|welding|construction|"
    r"facilities|warehouse|driver|cashier|retail associate|graphic design|ux|ui\b|video|content creator|teacher|tutor|"
    r"research scientist|machine learning|data scientist|epidemiolog)\b", re.I)
# quant/engineering-adjacent roles that only count if the title also says analyst/finance plainly
QUANT_ONLY = re.compile(r"\b(quant(itative)? (developer|researcher)|quantitative research|trading technology)\b", re.I)
PHD_ONLY = re.compile(r"\b(phd|ph\.d|ms/phd|masters?/phd|masters|mba|graduate student|doctoral|j\.?d\.?|law student|\bms\b)\b", re.I)

# ---- term detection -----------------------------------------------------------
# TARGET: what he can actually do. Summer 2027 internships, and a fall 2027 co-op (Jul-Dec 2027).
SUMMER_RE = re.compile(r"summer\s*'?(20)?27|(20)?27\s+summer|summer\s+(analyst|intern|internship|co-?op|program)|"
                       r"(may|june?)\s*[-–—to]+\s*(aug|sept?)|10[- ]week|12[- ]week|summer\s*/\s*fall", re.I)
FALL_RE = re.compile(r"fall\s*'?(20)?27|(20)?27\s+fall|autumn\s*(20)?27|fall\s+(semester|term|co-?op|intern|internship)|"
                     r"ju(ly|n)e?\s*[-–—to]+\s*dec|jul(y)?\.?\s*2027|(aug|sept?)(ust|ember)?\.?\s*2027|"
                     r"summer\s*/\s*fall|fall\s*/\s*winter|jul(y)?\s*[-–—to]+\s*(dec|jan)", re.I)
# DROP: terms he can't do (he's in classes Jan-Jun 2027) or that already passed
SPRING_RE = re.compile(r"spring\s*'?(20)?27|winter\s*'?(20)?27|jan(uary)?\s*'?(20)?27|winter\s*[/&-]\s*spring|\bw/s\b|"
                       r"spring\s+(semester|term|co-?op|intern|internship)|jan(uary)?\.?\s*[-–—to]+\s*(may|jun)", re.I)
PAST_RE = re.compile(r"summer\s*'?(20)?26|fall\s*'?(20)?26|spring\s*'?(20)?26|2026\s+(summer|fall)", re.I)

NON_US = re.compile(r"\b(india|bangalore|bengaluru|hyderabad|pune|mumbai|gurgaon|noida|chennai|china|shanghai|beijing|shenzhen|hong kong|"
                    r"taiwan|taipei|germany|frankfurt|munich|israel|tel aviv|uk\b|united kingdom|london|edinburgh|ireland|dublin|emea|apac|"
                    r"netherlands|amsterdam|france|paris|poland|warsaw|romania|singapore|malaysia|philippines|manila|vietnam|japan|tokyo|"
                    r"korea|seoul|canada|toronto|vancouver|ottawa|montreal|mexico|brazil|sao paulo|switzerland|zurich|geneva|luxembourg|"
                    r"belgium|sweden|spain|madrid|italy|milan|czech|hungary|budapest|krakow|australia|sydney|dubai|uae|riyadh)\b", re.I)


def is_intern(job):
    return bool(LEVEL_RE.search(job["title"]))


def hardware_score(job):
    """Kept under the old name so the shared pipeline code works unchanged: returns the finance/business words
    found in the title (empty list = not relevant)."""
    title = job["title"]
    hits = [m.group(1).lower() for m in FIN_RE.finditer(title)] + [m.group(1).lower() for m in BIZ_RE.finditer(title)]
    return sorted(set(hits))


def term_of(job):
    text = job["title"] + " " + (job.get("description") or "")[:4000]
    summer, fall, spring = SUMMER_RE.search(text), FALL_RE.search(text), SPRING_RE.search(text)
    if (PAST_RE.search(job["title"]) or re.search(r"\b2026\b", job["title"])) and not re.search(r"2027", job["title"]):
        return "past"
    if fall:
        return "fall"
    if summer:
        return "summer"
    if spring:
        return "spring"
    if re.search(r"co-?op", job["title"], re.I):
        return "coop-unspecified"
    return "unspecified"


def _rank(term):
    # A = summer or fall 2027 stated, B = co-op with no term stated, C = intern with no term stated
    return "A" if term in ("summer", "fall") else ("B" if term == "coop-unspecified" else "C")


def classify(job):
    """Return (keep, reason, meta). meta has term, hw (matched keywords), rank."""
    title = job["title"]
    if not is_intern(job):
        return False, "not intern", {}
    if EXCLUDE_TITLE.search(title) and not re.search(r"\b(financial|finance|accounting|business) (analyst|intern)", title, re.I):
        return False, "excluded title", {}
    if QUANT_ONLY.search(title):
        return False, "quant/tech only", {}
    hits = hardware_score(job)
    if not hits:
        # bank/insurer/consultancy listings often say only "Summer Analyst" or "2027 Internship Program": keep as a Maybe
        # when the company is one we deliberately track, or the description reads like a finance role
        d = (job.get("description") or "")[:4000]
        fin_desc = len(set(m.group(1).lower() for m in FIN_RE.finditer(d))) >= 3
        if (job.get("tier") or fin_desc or re.search(r"summer analyst", title, re.I)) and not NON_US.search(job.get("location") or ""):
            t = term_of(job)
            if t not in ("spring", "past"):
                return True, "ok", {"term": t, "hw": ["maybe"], "rank": _rank(t), "maybe": True}
        return False, "no finance/business keyword", {}
    if PHD_ONLY.search(title) and not re.search(r"\b(bs|ba|bachelor|undergrad)", title, re.I):
        return False, "grad/mba only", {}
    if NON_US.search(job.get("location") or ""):
        return False, "non-US", {}
    term = term_of(job)
    if term == "spring":
        return False, "spring/winter only", {"term": term}
    if term == "past":
        return False, "2026 term (past)", {"term": term}
    return True, "ok", {"term": term, "hw": hits[:4], "rank": _rank(term)}
