"""How well a posting matches the target: finance first, then general business.

fit levels, highest first:
  FINANCE   corporate finance / FP&A / treasury / accounting / IB / asset & wealth management / equity research ...
  BUSINESS  strategy, consulting, business analyst, operations, corporate development-adjacent roles
  MAYBE     intern/co-op at a tracked finance employer with a vague title ("2027 Summer Analyst Program")
  OTHER     kept by the filters but weak
"""
import re

CORE_FIN_TITLE = re.compile(r"(?<![a-z])(finance|financial|fp&a|fpa|treasury|accounting|accountant|audit|assurance|tax|"
                            r"controller|investment banking|capital markets|equity research|investment|asset management|"
                            r"wealth management|private wealth|portfolio|fixed income|credit|leveraged finance|private equity|"
                            r"venture capital|valuation|m&a|corporate development|transaction|underwriting|actuarial|"
                            r"sales (&|and) trading|global markets|fund accounting|fund administration|banking)(?![a-z])", re.I)

BIZ_TITLE = re.compile(r"(?<![a-z])(business analyst|business analytics|business operations|business development|strategy|"
                       r"strategic|consulting|consultant|operations|commercial|analyst|analytics|investor relations|"
                       r"rotational|leadership development|risk|compliance|economics)(?![a-z])", re.I)

# employers where any intern analyst role is a finance role
FIN_CO = re.compile(r"\b(fidelity|state street|wellington|mfs\b|putnam|franklin templeton|john hancock|manulife|liberty mutual|"
                    r"massmutual|natixis|loomis|eaton vance|bain capital|point72|blackrock|vanguard|t\. ?rowe|invesco|"
                    r"goldman|morgan stanley|j\.?p\.? ?morgan|jpmorgan|bank of america|citi(group|bank)?\b|wells fargo|bny|"
                    r"citizens|santander|td bank|pnc|u\.?s\.? bank|capital one|ubs|barclays|jefferies|evercore|lazard|"
                    r"houlihan|moelis|rbc|deutsche|nomura|baird|raymond james|stifel|piper sandler|william blair|"
                    r"kpmg|deloitte|pwc|pricewaterhouse|ernst|\bey\b|grant thornton|rsm\b|bdo\b|baker tilly|crowe|"
                    r"wolf & company|cbiz|marcum|travelers|hanover|hartford|prudential|metlife|northwestern mutual|"
                    r"american express|mastercard|visa\b|charles schwab|schwab|edward jones|ameriprise|lpl|"
                    r"blackstone|kkr|carlyle|apollo|ares|bain & company|boston consulting|bcg\b|mckinsey|"
                    r"analysis group|charles river associates|cornerstone research|alvarez|fti consulting|accenture)\b", re.I)


def fit_of(job):
    """Return (fit, why). job needs company + title."""
    co, title = job.get("company", ""), job.get("title", "")
    m = CORE_FIN_TITLE.search(title)
    if m:
        return "FINANCE", m.group(1).lower()
    if FIN_CO.search(co) and re.search(r"analyst|intern|co-?op|program", title, re.I):
        return "FINANCE", "intern/analyst role at a finance employer"
    m = BIZ_TITLE.search(title)
    if m:
        return "BUSINESS", m.group(1).lower()
    return "OTHER", ""


FIT_ORDER = {"FINANCE": 0, "BUSINESS": 1, "MAYBE": 2, "OTHER": 3}
