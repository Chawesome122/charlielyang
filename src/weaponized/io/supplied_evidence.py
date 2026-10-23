"""Admit supplied public documents without confusing copies with source vintages."""
from datetime import date
import calendar
from decimal import Decimal
import hashlib
import math
from pathlib import Path
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from weaponized.io.original_text import normalize_evidence, verified_original_text

FREEZE = "2026-10-11"


def incorporated_report_link(body, parent_url, report_url):
    """Require the full resolved exhibit URL; SEC exhibit basenames recur."""
    soup = BeautifulSoup(body, "html.parser")
    labels = [a.get_text(" ", strip=True) for a in soup.find_all("a", href=True)
              if urljoin(parent_url, a["href"]) == report_url]
    if not labels or not any(label.strip() for label in labels):
        raise ValueError("Full incorporated report URL absent from parent filing")
    return " | ".join(dict.fromkeys(" ".join(label.split()) for label in labels))


def stated_event_window(phrase):
    """Closed outer interval supported by an explicitly quoted date phrase."""
    exact=re.fullmatch(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})",phrase)
    months={calendar.month_name[i]:i for i in range(1,13)}
    if exact and exact[1] in months:
        d=date(int(exact[3]),months[exact[1]],int(exact[2])).isoformat()
        return d,d
    month=re.fullmatch(r"([A-Z][a-z]+) (\d{4})",phrase)
    if month and month[1] in months:
        y,m=int(month[2]),months[month[1]]
        return date(y,m,1).isoformat(),date(y,m,calendar.monthrange(y,m)[1]).isoformat()
    quarter=re.fullmatch(r"(?:the )?(first|second|third|fourth) quarter of (\d{4})",phrase)
    if quarter:
        q=['first','second','third','fourth'].index(quarter[1])+1;y=int(quarter[2]);m=3*q
        return date(y,m-2,1).isoformat(),date(y,m,calendar.monthrange(y,m)[1]).isoformat()
    short_quarter=re.fullmatch(r"Q([1-4]) (\d{4})",phrase)
    if short_quarter:
        q,y=int(short_quarter[1]),int(short_quarter[2]);m=3*q
        return date(y,m-2,1).isoformat(),date(y,m,calendar.monthrange(y,m)[1]).isoformat()
    if re.fullmatch(r"\d{4}",phrase):return phrase+'-01-01',phrase+'-12-31'
    raise ValueError('Unregistered event date wording')


def source_pages(root, source):
    path = Path(root) / source["archive_path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError("Supplied document checksum mismatch")
    if len(payload) != source["bytes"] or not payload.startswith(b"%PDF-"):
        raise ValueError("Supplied document size/form mismatch")
    pages = verified_original_text(path, source["sha256"]).split("\f")
    if not pages[-1].strip():
        pages.pop()
    if len(pages) != source["pdf_pages"]:
        raise ValueError("Supplied document page count mismatch")
    return [normalize_evidence(p) for p in pages]


def one_match(pattern, text):
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one evidence match, got {len(matches)}: {pattern}")
    return matches[0]


def extract_claim(pages, spec, source):
    public = source["info_public_date"]
    if date.fromisoformat(public).isoformat() > FREEZE:
        raise ValueError("Post-freeze source cannot enter historical evidence")
    page = spec["pdf_page"]
    if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= len(pages):
        raise ValueError("Explicit nonempty PDF page required")
    text = pages[page-1]
    match = one_match(spec["pattern"], text)
    header = ""
    if spec.get("header_pattern"):
        header = one_match(spec["header_pattern"], text)[0]
    value, token = None, None
    if "value" in spec:
        token = match[spec.get("group", "value")]
        if not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", token):
            raise ValueError("Unregistered numeric token")
        numeric = Decimal(token.replace(",", ""))
        if numeric != Decimal(str(spec["value"])):
            raise ValueError("Claim value disagrees with named source cell")
        value = float(numeric)
        if not math.isfinite(value) or value<0 or (spec['native_unit'].startswith('percent') and value>100):
            raise ValueError("Nonfinite evidence value")
    for key in ["event_start", "event_end", "period_end"]:
        if spec.get(key):
            date.fromisoformat(spec[key])
    if spec.get("event_start") and spec.get("event_end") and spec["event_start"] > spec["event_end"]:
        raise ValueError("Reversed event interval")
    if spec.get('event_start') or spec.get('event_end'):
        phrase=spec.get('event_date_phrase','')
        if phrase not in match[0] or not phrase:
            raise ValueError('Event interval lacks its exact quoted date phrase')
        if stated_event_window(phrase)!=(spec.get('event_start'),spec.get('event_end')):
            raise ValueError('Event interval disagrees with source date precision')
    if spec.get('period_label'):
        p=re.fullmatch(r'(\d{4})(Q2|H1)',spec['period_label'])
        if not p or (spec.get('period_start'),spec.get('period_end'))!=(p[1]+('-04-01' if p[2]=='Q2' else '-01-01'),p[1]+'-06-30'):
            raise ValueError('Reporting-period interval disagrees with named quarter/half-year')
    if spec.get("event_kind") == "observed" and spec.get("event_end", public) > public:
        raise ValueError("Observed event cannot occur after its source became public")
    if spec.get('event_kind')=='observed' and spec.get('period_end',public)>public:
        raise ValueError('Observed reporting period ends after source date')
    if spec.get("event_kind") not in {"observed", "planned", "definition", "legal_text"}:
        raise ValueError("Explicit observation/plan/definition/legal distinction required")
    return {k:v for k,v in spec.items() if k not in {"pattern", "group", "header_pattern"}} | dict(
        source_id=source["source_id"], request_source_id=source["request_source_id"],
        source_sha256=source["sha256"], source_url=source["source_url"],
        archive_path=source["archive_path"], info_public_date=public,
        public_clock_method=source["public_clock_method"],
        quote=match[0], header_quote=header, value=value, source_cell_token=token,
        locator=f"PDF page {page}; named quantity/statement {spec['variable']}",
        acquisition_method="user_upload", representation=source["representation"],
        retrieval_timestamp=source["retrieval_timestamp"],
        historical_byte_vintage_certified=False, earliest_public_date_certified=False,
        empirical_service_identified=False, causal_effect_identified=False)


def asof_supplied(frame, origin):
    date.fromisoformat(origin)
    if origin > FREEZE:
        raise ValueError("Origin exceeds research freeze")
    # A forecast/definition may describe a future target: retain its native target
    # separately. Selection concerns when the statement was publicly available.
    return frame[frame.info_public_date.le(origin)].copy()
