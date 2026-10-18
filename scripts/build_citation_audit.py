"""Rebuild bibliography and claim audit from archived evidence; no network requests."""
from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = {
    "R01": "Asymmetric international networks can provide jurisdiction-dependent panopticon and chokepoint coercion mechanisms.",
    "R02": "Economies of scale and specialization create an integration/security tradeoff; uncoordinated security policies can cause excessive fragmentation.",
    "R03": "The paper proposes dynamic opacity signaling and reports Monte Carlo diversification scenarios; these are not this project's empirical forecasts.",
    "R04": "The publication is a U.S.-China rare-earth dynamic game; exact equilibrium assumptions require full-text review.",
    "R05": "The authors report PSM/DID innovation responses among listed firms and effects on U.S. suppliers; the abstract does not establish functional semiconductor substitution.",
    "R06": "The authors report increased R&D inputs but little or negative effects on innovation outputs; inputs are not demonstrated semiconductor capability.",
    "R07": "Matching analysis of 2015-2022 firm data finds no increase in R&D investment/intensity; this is not a foundry-yield estimate.",
    "R08": "Uncertainty-shock framework; no rare-earth structural parameter is imported.",
    "R09": "Policy-uncertainty and corporate-investment relationship; exact findings require original full-text review.",
    "R10": "Sunk export costs can lower investment under trade-policy uncertainty; original application concerns Portugal/European integration.",
    "R11": "Real-option investment-under-uncertainty reference; no project-hazard coefficient is imported.",
    "R12": "Cox models censored failure times using covariates and an unspecified baseline hazard.",
    "R13": "Competing-risk subdistribution hazard reference; not used mechanically as a multistate transition probability.",
    "R14": "Multiple-period difference-in-differences methods reference; exact estimator assumptions need full-text review.",
    "R15": "Heterogeneous-treatment event-study methods reference; exact estimator assumptions need full-text review.",
    "R16": "Continuous-treatment difference-in-differences working-paper methods reference.",
    "R17": "Proper scoring-rule methods reference; numerical implementation independently tested.",
    "R18": "Probability forecast verification methods reference; numerical Brier scoring independently tested.",
    "R19": "Markov-perfect-equilibrium concept reference; no global pure continuous-game existence claim imported.",
    "R20": "Finite stochastic-game equilibrium existence reference; exact theorem conditions require original reading.",
    "R21": "Computational Markov equilibrium reference; no convergence guarantee imported.",
    "R22": "HJB/viscosity methods reference; no unverified theorem claim imported.",
    "R23": "Threshold-model conceptual precedent; not empirical mineral-project evidence.",
    "R24": "Sparse-network threshold model can create rare global cascades; not evidence of industrial hysteresis.",
    "R36": "The model characterizes foreign-productivity sabotage with nonmonotone semiconductor income effects; not measured national strategic utility.",
    "R37": "Dynamic segregation-model conceptual precedent; no mineral empirical claim imported.",
    "R38": "Increasing-return lock-in conceptual precedent; no mineral empirical claim imported.",
}
OFFICIAL = {
    "R25": ("International Energy Agency", "Rare Earth Elements", "2026", "https://www.iea.org/reports/rare-earth-elements/executive-summary"),
    "R26": ("U.S. Bureau of Industry and Security", "Commerce strengthens export controls to restrict China's capability to produce advanced semiconductors for military applications", "2024", "https://www.bis.gov/press-release/commerce-strengthens-export-controls-restrict-chinas-capability-produce-advanced-semiconductors-military"),
    "R27": ("U.S. Geological Survey", "Mineral Commodity Summaries 2026", "2026", "https://doi.org/10.3133/mcs2026"),
    "R28": ("Government of the Netherlands", "Klever: Export controls on advanced semiconductor manufacturing equipment to be tightened", "2025", "https://www.government.nl/latest/news/2025/01/15/klever-export-controls-on-advanced-semiconductor-manufacturing-equipment-to-be-tightened"),
    "R29": ("Ministry of Economy, Trade and Industry", "Export-control amendments: official Japanese instrument index", "2023", "https://www.meti.go.jp/policy/anpo/law09-2.html"),
    "R30": ("U.S. Bureau of Industry and Security", "Department of Commerce revises license review policy for semiconductors exported to China", "2026", "https://www.bis.gov/press-release/department-commerce-revises-license-review-policy-semiconductors-exported-china"),
    "R31": ("Ministry of Commerce and General Administration of Customs of the People's Republic of China", "Announcement No. 18 of 2025: rare-earth-related export controls [translated description]", "2025", "https://english.mofcom.gov.cn/Policies/AnnouncementsOrders/art/2025/art_0dd87cbee7b045bf93fabe6ab2faceee.html"),
    "R32": ("Ministry of Commerce and General Administration of Customs of the People's Republic of China", "Announcement No. 70 of 2025: suspension of specified announcements [translated description]", "2025", "https://www.mofcom.gov.cn/zfxxgk/gkml/art/2025/art_b1bff63a6bdd412a99c84203dd30fd39.html"),
    "R33": ("U.S. International Trade Commission", "DataWeb API User Guide", "", "https://www.usitc.gov/applications/dataweb/api/dataweb_query_api.html"),
    "R34": ("UN Comtrade", "UN Comtrade API documentation", "", "https://uncomtrade.org/docs/un-comtrade-api/"),
    "R35": ("World Intellectual Property Organization", "PATENTSCOPE", "", "https://www.wipo.int/en/web/patentscope"),
    "R39": ("U.S. Securities and Exchange Commission", "EDGAR filings", "", "https://www.sec.gov/edgar/search/"),
    "R40": ("International Energy Agency", "Global Critical Minerals Outlook 2026: Outlook", "2026", "https://www.iea.org/reports/global-critical-minerals-outlook-2026/outlook"),
}

READ_OFFICIAL = {
    "R26": ("SC-BIS-2024-12-02", "The December 2, 2024 BIS release reports controls on 24 equipment types, 3 software types and HBM; it distinguishes delayed compliance for some controls. Binding ECCN details are in linked Federal Register rules."),
    "R28": ("SC-NL-2025-01-15", "The original January 15 Dutch government release announces an April 1, 2025 expansion of national authorisation to additional technologies and explicitly states case-by-case decisions and that it does not constitute an export ban."),
    "R30": ("SC-BIS-2026-01-13", "The original January 13 BIS release reports case-by-case H200/MI325X-class licensing subject to security requirements. Federal Register 2026-00789 supplies binding conditions and January 15 effective date."),
}


def component_verification(key: str) -> dict:
    rare_registry = ROOT / "metadata/rare_earth_acquisitions.jsonl"
    if key in {"R25", "R27"} and rare_registry.exists():
        records = [json.loads(line) for line in rare_registry.read_text().splitlines()]
        source_id = "RE-IEA2026" if key == "R25" else "RE-USGS2026-PAGE"
        source = next((record for record in records if record["source_id"] == source_id and record["status"] == "downloaded"), None)
        if source:
            excerpt = ("The IEA original executive summary reports 2024 Chinese shares of 60% of magnet-REE mining, 91% of refined output, and 94% of sintered permanent magnets. The main report landing page dates publication to 2026-04-08 and gives CC BY 4.0 licensing. These are source-reported aggregate statistics, not independently reconstructed project-level service."
                       if key == "R25" else "The USGS original publication entry confirms report title, DOI10.3133/mcs2026 and publication2026-02-06. The associated data-release entry gives2026-09-18, DOI10.5066/P1WKQ63T and CC0. The underlying report/data tables were not downloaded through the attempted endpoints, so numerical mineral observations are not certified.")
            return dict(metadata_status="ORIGINAL_AGENCY_ENTRY_VERIFIED", claim_status="ORIGINAL_TEXT_READ_FOR_CLAIM",
                        evidence_path=source["archive_path"], evidence_sha256=source["sha256"],
                        first_published="2026-04-08" if key == "R25" else "2026-02-06", freeze_eligible="True",
                        evidence_excerpt=excerpt,
                        limitations="Live navigation may contain postfreeze content and is excluded. Original source date is checked; historical article revisions are not independently archived. USGS metadata alone does not verify table values.")
    if key not in READ_OFFICIAL:
        return {}
    registry = ROOT / "metadata/semiconductor_sources.csv"
    if not registry.exists():
        return {}
    source_id, excerpt = READ_OFFICIAL[key]
    records = list(csv.DictReader(registry.open()))
    source = next((record for record in records if record["source_id"] == source_id and record["status"] == "retrieved"), None)
    if source is None:
        return {}
    return dict(metadata_status="ORIGINAL_AGENCY_ENTRY_VERIFIED", claim_status="ORIGINAL_TEXT_READ_FOR_CLAIM",
                evidence_path=source["path"], evidence_sha256=source["sha256"],
                first_published=source["publication_date"], freeze_eligible=source["freeze_eligible"],
                evidence_excerpt=excerpt, limitations="Press/news source establishes its stated policy description; binding transaction coverage requires the separate legal-code audit.")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", value))).strip()


def tex(value: str) -> str:
    for char, replacement in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")]:
        value = value.replace(char, replacement)
    return value


def date_string(message: dict, key: str) -> str:
    parts = message.get(key, {}).get("date-parts", [[]])[0]
    return "-".join(str(v).zfill(4 if i == 0 else 2) for i, v in enumerate(parts))


def main() -> None:
    rows, bibliography = [], []
    manuscripts = ROOT / "manuscript"
    manuscripts.mkdir(exist_ok=True)
    for index in range(1, 41):
        key = f"R{index:02d}"
        path = ROOT / "data/raw/literature" / (key + "_crossref.json")
        row = {"source_id": key, "metadata_status": "UNVERIFIED", "claim_status": "NOT_CHECKED",
               "claim": CLAIMS.get(key, "Official data/legal entry; see corresponding component source audit."),
               "evidence_path": "", "evidence_sha256": "", "first_published": "", "metadata_deposited": "",
               "freeze_eligible": "UNVERIFIED", "evidence_excerpt": "", "limitations": ""}
        if path.exists():
            message = json.loads(path.read_text())["message"]
            row.update(metadata_status="DOI_REGISTRATION_VERIFIED", evidence_path=str(path.relative_to(ROOT)),
                       evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       first_published=date_string(message, "published"), metadata_deposited=message.get("deposited", {}).get("date-time", ""))
            row["freeze_eligible"] = str(row["first_published"] <= "2026-10-11" and row["metadata_deposited"][:10] <= "2026-10-11")
            if message.get("abstract"):
                row.update(claim_status="PUBLISHER_DEPOSITED_ABSTRACT_READ", evidence_excerpt=clean(message["abstract"]))
            else:
                row["claim_status"] = "FULL_TEXT_REQUIRED"
            authors = " and ".join(a.get("family", "") + ", " + a.get("given", "") for a in message.get("author", []))
            note = "Bibliographic fields verified against archived DOI registration; claim reading level recorded in citation audit."
            if key == "R08":
                authors = "Bloom, N."
                row.update(metadata_status="PARTIAL_AUTHOR_MISSING", limitations="Crossref omits author; Bloom authorship remains blueprint-supplied pending original verification.")
                note = "Crossref title/venue/pages verified; author remains provisional from blueprint."
            if key == "R11":
                authors = "Dixit, Avinash K. and Pindyck, Robert S."
                row.update(metadata_status="CONFLICT_REQUIRES_ORIGINAL", limitations="Princeton DOI registration incorrectly/ambiguously lists Robert K. Dixit; identical-book DOI 10.2307/j.ctt7sncv lists Avinash K. Dixit. No original text read.")
                note = "Author-name conflict between identical-book DOI registrations; see citation audit. Original print year 1994; original publisher check outstanding."
            if key == "R09":
                row["limitations"] = "Crossref verifies online year 2015 but omits final issue/page metadata; blueprint final 2016 issue not independently verified."
            if key == "R19":
                row["limitations"] = "Deposited title omits blueprint subtitle I. Observable actions; original full title not independently checked."
            if key == "R20":
                row["limitations"] = "Registration uses modern Hiroshima Mathematical Journal container; historical original Series A-I title/pages require original scan."
            if key == "R02":
                row.update(claim_status="ORIGINAL_TEXT_READ_FOR_CLAIM", evidence_excerpt="Original PDF cover: December 2024, revised April 2025. Abstract and introduction: economies of scale/specialization create coercive power and gains-from-trade/security tradeoff; uncoordinated economic security policies cause inefficient fragmentation.", limitations="Working paper, not peer reviewed. Original file revision explicitly before freeze; full paper not independently replicated.")
                row["evidence_path"] += ";data/raw/literature/R02_pdf.pdf"
            kind = "book" if "book" in message.get("type", "") else "techreport" if key in {"R02", "R16"} else "article"
            fields = {"author": authors, "title": clean(message.get("title", [""])[0]), "year": row["first_published"][:4], "doi": message["DOI"], "note": note}
            if kind == "article":
                fields.update(journal=clean(message.get("container-title", [""])[0]), volume=message.get("volume", ""), number=message.get("issue", ""), pages=message.get("page", "").replace("-", "--"))
                if message.get("article-number"):
                    fields["eid"] = message["article-number"]
            elif kind == "techreport":
                fields.update(institution=message.get("publisher", ""), number="33309" if key == "R02" else "32117")
            else:
                fields["publisher"] = message.get("publisher", "")
        else:
            author, title, year, url = OFFICIAL[key]
            kind = "misc"
            fields = {"author": "{" + author + "}", "title": title, "year": year, "url": url, "note": "Discovery entry from blueprint; primary-source verification is tracked in citation audit and component source registries."}
            row["limitations"] = "Blueprint entry alone is not admissible substantive evidence; consult component source registry."
            verification = component_verification(key)
            if verification:
                row.update(verification)
                row["claim"] = verification["evidence_excerpt"]
                fields["note"] = "Original agency entry archived and read; see source-to-claim audit and legal chronology for binding details."
        bibliography.append("@" + kind + "{" + key + ",\n" + ",\n".join("  " + name + " = {" + tex(str(value)) + "}" for name, value in fields.items() if value) + "\n}\n")
        rows.append(row)
    with (ROOT / "metadata/citation_audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (manuscripts / "references.bib").write_text("% Generated from archived evidence. Verification limitations remain explicit.\n\n" + "\n".join(bibliography))
    print(f"Built {len(rows)} auditable bibliography entries; no network access.")


if __name__ == "__main__":
    main()
