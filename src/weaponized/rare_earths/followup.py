"""Validate source clocks and native capacity presentations for selected projects."""

from datetime import date
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from weaponized.io.original_text import (
    evidence_pdf_page,
    normalize_evidence,
    verified_original_text,
)
from weaponized.rare_earths.plant_ledger import capacity_identity

FREEZE = date(2026, 10, 11)
CAPACITY_ROWS = (
    "Phase 1: NdPr (Existing)",
    "Phase 1: Heavies (Planned)",
    "Phase 2: (Planned)",
    "Total (Phase 1 + Phase 2) (1)",
)
ELEMENTS = ("ndpr", "tb", "dy")


def verified_html(root, source):
    payload = (root / source["archive_path"]).read_bytes()
    if (
        sha256(payload).hexdigest() != source["sha256"]
        or len(payload) != source["byte_count"]
        or Path(source["archive_path"]).suffix != ".html"
    ):
        raise ValueError(f"HTML source identity mismatch: {source['source_id']}")
    return BeautifulSoup(payload, "html.parser")


def source_clocks(root, sources):
    """Bind each date to the archived dateline, index or exact link."""
    result = {}
    for sid, source in sources.items():
        public = date.fromisoformat(source["info_public_date"])
        clock = sources[source["public_clock_source_id"]]
        text = verified_original_text(root / clock["archive_path"], clock["sha256"])
        method = source["publication_basis"]
        locator = "dated release text"

        if public > FREEZE or clock["info_public_date"] != public.isoformat():
            raise ValueError(f"Missing, conflicting or post-freeze public clock: {sid}")
        if method in {"sec_filing_index", "sec_index_dateline"}:
            index = verified_html(root, clock)
            fields = {
                node.get_text(strip=True): node.find_next_sibling().get_text(strip=True)
                for node in index.select("div.infoHead")
            }
            if fields["Filing Date"] != public.isoformat():
                raise ValueError(f"SEC filing date mismatch: {sid}")
            locator = f"EDGAR index, Filing Date; Accepted {fields['Accepted']}"
            if method == "sec_filing_index":
                path = urlsplit(source["source_url"]).path
                links = [
                    parse_qs(urlsplit(link["href"]).query).get("doc", [link["href"]])[0]
                    for link in index.select("table.tableFile a[href]")
                ]
                if links.count(path) != 1:
                    raise ValueError(f"SEC index does not identify exactly one filing: {sid}")
        elif method == "exact_link_from_dated_release":
            release = verified_html(root, clock)
            links = {
                parse_qs(urlsplit(link["href"]).query).get("u", [link["href"]])[0]
                for link in release.select("a[href]")
            }
            if source["source_url"] not in links:
                raise ValueError(f"No exact dated release link: {sid}")
            document = verified_original_text(root / source["archive_path"], source["sha256"])
            if source["dateline"] not in normalize_evidence(document.split("\f")[1]):
                raise ValueError(f"Engineering effective date changed: {sid}")
            locator = "exact report URL in dated issuer release; effective date on PDF page 2"
        elif method in {"issuer_dateline", "exchange_announcement_dateline"}:
            if method == "exchange_announcement_dateline":
                text = text.split("\f")[0]
                locator = "PDF page 1, exchange announcement dateline"
            month = public.strftime("%B")
            dates = {
                f"{month} {public.day}, {public.year}",
                f"{month[:3]}. {public.day}, {public.year}",
                f"{public.day} {month} {public.year}",
            }
            if source["dateline"] not in dates or source["dateline"] not in normalize_evidence(text):
                raise ValueError(f"Source dateline mismatch: {sid}")
        else:
            raise ValueError(f"Unreviewed publication basis: {sid}")
        result[sid] = dict(
            source_id=sid, info_public_date=public.isoformat(),
            public_clock_source_id=clock["source_id"], public_clock_sha256=clock["sha256"],
            publication_basis=method, public_clock_locator=locator,
            original_at_vintage_bytes_certified=False,
        )
    return result


def extract_claims(root, specs, sources, clocks, *, preserve_native_tokens=False):
    originals = {}
    claims = []
    values = {}
    for spec in specs:
        sid = spec["source_id"]
        cid = spec["claim_id"]
        source = sources[sid]
        if sid not in originals:
            originals[sid] = verified_original_text(root / source["archive_path"], source["sha256"])
        original = originals[sid]
        page = evidence_pdf_page(spec)
        if Path(source["archive_path"]).suffix == ".pdf":
            pages = original.split("\f")
            if page is None or page > len(pages) or not pages[page - 1].strip():
                raise ValueError(f"Explicit source page required: {cid}")
            original = pages[page - 1]
        elif page is not None:
            raise ValueError(f"PDF page supplied for HTML claim: {cid}")

        matches = {
            (match[0], tuple(match.groupdict().items()))
            for match in re.finditer(spec["pattern"], normalize_evidence(original))
        }
        if len(matches) != 1 or cid in values:
            raise ValueError(f"Missing, ambiguous or repeated source claim: {cid}")
        quote, named_values = matches.pop()
        values[cid] = dict(named_values) if preserve_native_tokens else {
            key: int(value.replace(",", "")) for key, value in named_values
        }
        lower, upper = (date.fromisoformat(spec[field]) if spec[field] else None
                        for field in ("event_date_lower", "event_date_upper"))
        if lower and (upper is None or upper < lower):
            raise ValueError(f"Invalid event interval: {cid}")
        if spec["evidence_role"].startswith("observed") and (
            upper is None or upper > date.fromisoformat(clocks[sid]["info_public_date"])
        ):
            raise ValueError(f"Observed event exceeds its public clock: {cid}")
        fields = {key: value for key, value in spec.items() if key != "pattern"}
        claims.append(fields | clocks[sid] | dict(
            source_sha256=source["sha256"], source_url=source["source_url"],
            retrieved_utc=source["retrieved_utc"], pdf_page=page, quote=quote,
        ))
    return claims, values


def capacity_cells(soup):
    """Read the named circuit table, preserving displayed dashes."""
    candidates = [table for table in soup.select("table")
                  if CAPACITY_ROWS[-1] in normalize_evidence(table.get_text(" ", strip=True))]
    if len(candidates) != 1:
        raise ValueError("Expected one named White Mesa capacity table")
    rows = [
        [normalize_evidence(cell.get_text(" ", strip=True)) for cell in
         row.find_all(["td", "th"], recursive=False) if cell.get_text(strip=True)]
        for row in candidates[0].find_all("tr")
    ]
    rows = [row for row in rows if row]
    if rows[0] != ["Phase", "NdPr (tpa)", "Tb (tpa)", "Dy (tpa)"] or tuple(
        row[0] for row in rows[1:]
    ) != CAPACITY_ROWS:
        raise ValueError("Unexpected circuit rows, column order or native capacity units")
    if any(len(row) != 4 for row in rows):
        raise ValueError("Unexpected White Mesa table cell count")
    cells = []
    for row in rows[1:]:
        for element, token in zip(ELEMENTS, row[1:], strict=True):
            if token != "—" and re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)", token) is None:
                raise ValueError(f"Unexpected native capacity token: {token}")
            cells.append(dict(
                phase=row[0], element=element, native_token=token, native_unit="tpa",
                value=None if token == "—" else int(token.replace(",", "")),
                displayed_dash=token == "—",
            ))
    return cells


def compare_capacities(cells, march_design, july_design, august_design, july_combined):
    lookup = {(row["phase"], row["element"]): row["value"] for row in cells}
    if july_design != august_design:
        raise ValueError("July and August prose figures do not match")
    result = []
    for element in ELEMENTS:
        base_phase = CAPACITY_ROWS[0 if element == "ndpr" else 1]
        base, phase2, combined = (lookup[(phase, element)]
                                  for phase in (base_phase, *CAPACITY_ROWS[2:]))
        identity = capacity_identity(base, phase2, combined)
        result.append(dict(
            element=element, table_phase1=base, table_phase2=phase2, table_total=combined,
            table_components_reconcile=identity["passed"],
            march_phase1_prose=march_design.get(element), july_phase1_prose=july_design.get(element),
            august_phase1_prose=august_design.get(element), july_combined_prose=july_combined[element],
            august_phase1_prose_minus_table=None if element == "ndpr" else august_design[element] - base,
            july_combined_prose_minus_august_table=july_combined[element] - combined,
            native_unit="tpa", achieved_output=False, selected_operating_capacity=None,
        ))
    return result


def donald_as_of(origins, targets):
    """Show the target visible at each origin, even when the target is future."""
    result = []
    for origin in origins:
        if not isinstance(origin, date) or origin > FREEZE:
            raise ValueError("Origin must be a calendar date at or before the freeze")
        visible = [row for row in targets if row["info_public_date"] <= origin.isoformat()]
        latest = max(visible, key=lambda row: row["info_public_date"], default=None)
        result.append(dict(
            origin=origin.isoformat(), target_versions_visible=len(visible),
            latest_target_claim=latest["claim_id"] if latest else None,
            latest_target_end=latest["event_date_upper"] if latest else None,
            actual_fid_date=None,
        ))
    return result
