"""Bind public clocks to exact report links, never filenames or nearby dates."""
from datetime import datetime
import json
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup


def _url(base, href):
    return urldefrag(urljoin(base, href))[0]


def linked_publication_clock(html, page_url, report_url, method, freeze="2026-10-11"):
    soup = BeautifulSoup(html, "html.parser")
    links = [a for a in soup.find_all("a", href=True) if _url(page_url, a["href"]) == report_url]
    if not links:
        raise ValueError("No exact report link on the evidence page")
    if method == "dated_link_card":
        matches = []
        for link in links:
            dates = link.select(".document-date")
            if len(dates) == 1:
                native = dates[0].get_text(" ", strip=True)
                matches.append((datetime.strptime(native, "%d %b %Y").date().isoformat(),
                                " ".join(link.get_text(" ", strip=True).split())))
        if not matches:
            raise ValueError("Exact report link lacks its own dated card; adjacent/page dates are insufficient")
        if len({x[0] for x in matches}) != 1:
            raise ValueError("Conflicting dated cards require adjudication")
        public, support = matches[0]
    elif method == "article_jsonld":
        # A related-post/footer link cannot borrow an article's publication date.
        articles = soup.find_all("article")
        if len(articles) != 1 or not any(a.find_parent("article") is articles[0] for a in links):
            raise ValueError("Report link is not in the article body")
        matches = []
        for script in soup.find_all("script", type="application/ld+json"):
            payload = json.loads(script.string or script.get_text())
            nodes = payload.get("@graph", [payload]) if isinstance(payload, dict) else payload
            for item in nodes:
                types = item.get("@type", [])
                types = [types] if isinstance(types, str) else types
                if "Article" not in types:
                    continue
                main = item.get("mainEntityOfPage", {})
                main = main.get("@id", "") if isinstance(main, dict) else main
                if not isinstance(main, str) or not main or _url(page_url, main) != _url(page_url, page_url):
                    continue
                native = item.get("datePublished")
                if native:
                    public = datetime.fromisoformat(native.replace("Z", "+00:00")).date().isoformat()
                    matches.append((public, "Article.datePublished="+native))
        if len({x[0] for x in matches}) != 1:
            raise ValueError("No unique Article.datePublished tied to this page; dateModified/WebPage dates are insufficient")
        public, support = matches[0]
    else:
        raise ValueError("Unsupported publication-evidence method")
    if public > freeze:
        raise ValueError("Post-freeze publication clock")
    return dict(info_public_date=public, support=support, method=method,
                historical_byte_vintage_certified=False,
                basis="dated exact issuer report link; conservative availability, not a certified historical web snapshot or search-certified earliest release")
