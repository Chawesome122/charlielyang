"""Source-vintage audit helpers; auxiliary metadata never supplies release dates."""
from datetime import date, datetime, timezone
import json
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup


def _absolute(base, href):
    return urldefrag(urljoin(base, href))[0]


def report_link_metadata(html, page_url, report_url):
    """Inspect exact links and local link conflicts without inferring publication."""
    soup = BeautifulSoup(html, "html.parser")
    links = [a for a in soup.find_all("a", href=True)
             if _absolute(page_url, a["href"]) == report_url]
    sibling_urls = set()
    for link in links:
        item = link.find_parent("li")
        if item:
            sibling_urls.update(_absolute(page_url, a["href"])
                                for a in item.find_all("a", href=True)
                                if a.find_parent("li") is item
                                and _absolute(page_url, a["href"]).split("?", 1)[0].lower().endswith(".pdf")
                                and _absolute(page_url, a["href"]) != report_url)
    page_dates = []
    for script in soup.find_all("script", type="application/ld+json"):
        value = json.loads(script.string or script.get_text())
        nodes = value.get("@graph", [value]) if isinstance(value, dict) else value
        for node in nodes:
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if "WebPage" in types:
                page_dates.extend(dict(kind="WebPage."+field, value=node[field])
                                  for field in ["datePublished", "dateModified"] if field in node)
    return dict(exact_report_link_count=len(links),
                exact_report_link_titles=[a.get_text(" ", strip=True) for a in links],
                off_target_same_list_item_urls=sorted(sibling_urls),
                rejected_page_date_candidates=page_dates)


def source_vintage_readiness(publication_date, retrieval_timestamp, origin,
                             freeze="2026-10-11"):
    """Separate issuer-stated availability from certification of at-origin bytes.

    Retrieval is not publication. A later exact issuer association can support a
    conservative source-reported availability date but cannot certify that these
    downloaded bytes are unchanged from the claimed historical release.
    """
    cut = date.fromisoformat(origin)
    if cut > date.fromisoformat(freeze):
        raise ValueError("Research information freeze exceeded")
    retrieved = datetime.fromisoformat(retrieval_timestamp.replace("Z", "+00:00"))
    if retrieved.tzinfo is None:
        raise ValueError("Retrieval timestamp requires an explicit timezone")
    if publication_date is None:
        status = "UNKNOWN_PUBLICATION_DATE"
        available = False
    else:
        public = date.fromisoformat(publication_date)
        if public > date.fromisoformat(freeze):
            raise ValueError("Post-freeze publication date cannot enter this audit")
        available = public <= cut
        status = "SOURCE_REPORTED_AVAILABLE" if available else "NOT_YET_PUBLIC"
    return dict(status=status, source_reported_available=available,
                archive_retrieved_by_origin=retrieved.astimezone(timezone.utc).date() <= cut,
                historical_byte_vintage_certified=False,
                independently_certified_historical_forecast_eligible=False)
