"""Issued Entity List schedules, not consolidated law or numerical access loss.

The unit is a printed, destination-specific entry version. Aliases, address
continuations, revisions and repeated destinations must not become new firms.
"""
from collections import Counter
from datetime import date
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from weaponized.semiconductors.legal import issued_xml_text
from weaponized.semiconductors.provisions import normalize_text


def xml_paths(root):
    """Generate explicit original-document locators, preserving sibling order."""
    def walk(node, path):
        yield node, path
        counts = Counter()
        for child in node:
            counts[child.tag] += 1
            yield from walk(child, f"{path}/{child.tag}[{counts[child.tag]}]")
    yield from walk(root, ".")


def review_category(text):
    """Describe printed review language; never infer approval or severity."""
    lower = text.lower()
    if "case-by-case" in lower and "denial" in lower:
        return "mixed_denial_and_case_by_case"
    if re.fullmatch(r"presumption of denial\.?", lower):
        return "presumption_of_denial"
    if lower.startswith("policy of denial"):
        return "policy_of_denial"
    if "case-by-case" in lower:
        return "case_by_case"
    if lower.startswith("see "):
        return "cross_referenced_review_unresolved"
    raise ValueError(f"Unreviewed license review language: {text}")


def reported_filing_date(trailer, document_number):
    match = re.fullmatch(r"\[FR Doc\. " + re.escape(document_number) + r" Filed (\d{1,2}-\d{1,2}-\d{2}); .+\]", trailer)
    if not match:
        raise ValueError("Unreviewed original filing dateline")
    from datetime import datetime
    return datetime.strptime(match[1], "%m-%d-%y").date().isoformat()


def parse_entity_schedule(payload, spec):
    if hashlib.sha256(payload).hexdigest() != spec["source_sha256"]:
        raise ValueError("Original Entity List XML checksum mismatch")
    issued_xml_text(payload, spec["document_number"])
    root = ET.fromstring(payload)
    if root.tag != "RULE":
        raise ValueError("Entity schedule must be an issued rule, not a proposal/notice")
    paths = {id(node): path for node, path in xml_paths(root)}
    tables = root.findall(".//GPOTABLE")
    if len(tables) != 1 or tables[0].get("COLS") != "5":
        raise ValueError("Expected one reviewed five-column Entity List table")
    table = tables[0]
    headers = [normalize_text(x) for x in table.findall("./BOXHD/CHED")]
    if headers != ["Country", "Entity", "License requirement", "License review policy", "Federal Register citation"]:
        raise ValueError("Entity schedule column order changed")
    expected_countries = set(spec["country_headings"])
    country = None
    country_xpath = None
    seen_countries = set()
    entries, rows, pending = [], [], None
    notes = []
    for node in table.findall("TNOTE"):
        text = normalize_text(node)
        if not text or not text.replace("*", "").strip():
            continue
        match = re.match(r"(\d+)\s+", text)
        if not match:
            raise ValueError("Unregistered substantive table note")
        notes.append(dict(note_number=match[1], quote=text, xpath=paths[id(node)]))

    def finish():
        nonlocal pending
        if pending is not None:
            pending["entity_text"] = " ".join(pending.pop("entity_parts"))
            pending["source_row_ordinals"] = json.dumps(pending["source_row_ordinals"])
            entries.append(pending)
            pending = None

    def set_country(value, xpath):
        nonlocal country, country_xpath
        if value not in expected_countries:
            raise ValueError(f"Unreviewed destination heading: {value}")
        finish()
        country, country_xpath = value, xpath
        seen_countries.add(value)

    for ordinal, row in enumerate(table.findall("ROW"), 1):
        cells = row.findall("ENT")
        values = [normalize_text(x) for x in cells]
        xpath = paths[id(row)]
        role, entry_id = "decorative", None
        if len(cells) not in {1, 2, 5}:
            raise ValueError("Unreviewed source row layout")
        if len(cells) == 1:
            if values[0] and values[0].replace("*", "").strip():
                set_country(values[0], xpath+"/ENT[1]")
                role = "country_heading"
        else:
            if values[0]:
                set_country(values[0], xpath+"/ENT[1]")
                role = "country_heading"
            if len(cells) == 5 and values[2]:
                if not country or not values[1] or not values[3] or not values[4]:
                    raise ValueError("License entry has missing country/name/review/citation")
                finish()
                entry_id = f"EL:{spec['document_number']}:ROW{ordinal}"
                refs = sorted(set(re.findall(r"\d+", " ".join(normalize_text(x) for x in cells[2].findall(".//SU")))))
                pending = dict(entry_id=entry_id, document_number=spec["document_number"],
                               destination=country, country_xpath=country_xpath,
                               start_row_ordinal=ordinal, start_xpath=xpath,
                               entity_first_cell=values[1], entity_parts=[values[1]],
                               source_row_ordinals=[ordinal], license_scope_text=values[2],
                               review_policy_text=values[3], citation_cell_text=values[4],
                               review_category=review_category(values[3]),
                               entry_kind="address_entry" if re.match(r"Address\s+\d+\b", values[1], re.I) else "listed_person_or_organization_unresolved",
                               license_requirement="required_for_printed_scope",
                               license_footnote_refs=json.dumps(refs),
                               unprinted_footnote_refs=json.dumps([n for n in refs if n not in {v['note_number'] for v in notes}]),
                               action_adjudication="addition_or_revision_not_resolved_from_schedule_alone",
                               current_law_consolidation_verified=False,
                               observed_license_outcome=None, foreign_access_score=None,
                               domestic_capability_score=None, causal_effect=None)
                role = "entry_start"
            elif len(cells) == 5 and any(values[2:]):
                raise ValueError("Detached review/citation text without a license scope")
            elif values[1] and values[1].replace("*", "").strip():
                if values[0] or pending is None:
                    raise ValueError("Orphan entity/address continuation")
                pending["entity_parts"].append(values[1])
                pending["source_row_ordinals"].append(ordinal)
                entry_id = pending["entry_id"]
                role = "entity_continuation"
        rows.append(dict(row_ordinal=ordinal, xpath=xpath, quote=normalize_text(row),
                         cell_values_json=json.dumps(values, ensure_ascii=False), row_role=role,
                         entry_id=entry_id, destination_context=country))
    finish()
    if len(entries) != spec["expected_printed_entries"] or len(rows) != spec["expected_table_rows"]:
        raise ValueError("Reviewed original entry/row coverage changed")
    if seen_countries != expected_countries:
        raise ValueError("Reviewed destination coverage changed")
    instructions = [dict(xpath=path, quote=normalize_text(node)) for node, path in xml_paths(root) if node.tag == "AMDPAR"]
    action = spec["schedule_action"]
    if action not in {"addition", "mixed_document_addition_or_revision_requires_entry_adjudication"}:
        raise ValueError("Unregistered amendment-action coding")
    all_instructions = " ".join(x["quote"] for x in instructions).lower()
    if action == "addition" and ("adding" not in all_instructions or "revis" in all_instructions):
        raise ValueError("Uniform-addition coding conflicts with original amendatory instructions")
    for entry in entries:
        entry["action_adjudication"] = action
    return dict(entries=entries, source_rows=rows, table_notes=notes, amendatory_instructions=instructions,
                dates_xpath="./PREAMB[1]/EFFDATE[1]", dates_quote=normalize_text(root.find("./PREAMB/EFFDATE")))


def visible_issued_entries(frame, origin, freeze="2026-10-11", clock="info_public_date"):
    """Known and effective-by-origin *issued versions*, never a current-law list."""
    if date.fromisoformat(origin) > date.fromisoformat(freeze):
        raise ValueError("Origin after research freeze")
    if clock not in {"info_public_date", "publication_date"}:
        raise ValueError("Unregistered legal source clock")
    return frame[frame[clock].le(origin) & frame.effective_date.le(origin)].copy()


def adjudicate_entry_actions(payload, spec, entries, crosswalk):
    """Bind mixed-document operations to exact original named instructions.

    The one documented name-spelling discrepancy remains provisional. This
    adjudication does not perform company identity resolution or consolidate law.
    """
    root=ET.fromstring(payload)
    normalize_name=lambda s:re.sub(r"[\W_]+", "", s).casefold()
    instruction_country={};country=None
    for node,path in xml_paths(root):
        if node.tag!="AMDPAR":
            continue
        text=normalize_text(node)
        for heading in sorted(spec["country_headings"],key=len,reverse=True):
            if re.search(r"\bunder\s+(?:the\s+)?"+re.escape(heading)+r"\b",text,re.I):
                country=heading
                break
        instruction_country[path]=country
    mapping={r["entry_id"]:r for r in crosswalk}
    if len(mapping)!=len(crosswalk):
        raise ValueError("Duplicate entry-action crosswalk")
    if spec["schedule_action"]=="addition":
        if mapping:
            raise ValueError("Uniform-addition document must not have mixed-entry overrides")
        for entry in entries:
            entry.update(action_evidence_method="all_original_amendatory_instructions_are_additions",
                         action_source_xpath="", instruction_name="", name_variant_requires_expert_review=False)
        return entries
    if set(mapping)!={e["entry_id"] for e in entries}:
        raise ValueError("Mixed-document action crosswalk incomplete")
    for entry in entries:
        coded=mapping[entry["entry_id"]]
        nodes=root.findall(coded["amendatory_xpath"])
        if len(nodes)!=1 or nodes[0].tag!="AMDPAR" or normalize_text(nodes[0])!=coded["amendatory_quote"]:
            raise ValueError("Action evidence is not the exact original numbered instruction")
        if coded["source_sha256"]!=spec["source_sha256"] or coded["destination"]!=entry["destination"] or coded["entry_first_cell_anchor"]!=entry["entity_first_cell"]:
            raise ValueError("Action crosswalk attached to the wrong original entry")
        if instruction_country.get(coded["amendatory_xpath"])!=entry["destination"]:
            raise ValueError("Amendatory instruction is under another destination")
        text=coded["amendatory_quote"]
        if not normalize_name(coded["instruction_name"]) or coded["instruction_name"] not in text or coded["action"] not in {"addition","revision"}:
            raise ValueError("Action name or registered operation absent")
        verb="adding" if coded["action"]=="addition" else "revising"
        if not re.search(r"\b"+verb+r"\b",text,re.I):
            raise ValueError("Entry operation contradicts the original instruction")
        variant=coded["name_variant_requires_expert_review"]
        if not isinstance(variant,bool):
            raise ValueError("Name-variant adjudication must be an explicit boolean")
        direct=normalize_name(entry["entity_first_cell"]).startswith(normalize_name(coded["instruction_name"]))
        if direct==variant or not coded["adjudication_note"]:
            raise ValueError("Unregistered entry-name discrepancy")
        entry.update(action_adjudication=coded["action"]+"_provisional_name_variant" if variant else coded["action"],
                     action_evidence_method="single_researcher_exact_instruction_name_crosswalk",
                     action_source_xpath=coded["amendatory_xpath"], instruction_name=coded["instruction_name"],
                     name_variant_requires_expert_review=variant)
    return entries
