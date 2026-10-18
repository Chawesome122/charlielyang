#!/usr/bin/env python3
"""Curated source-checked discovery ledger, explicitly not a complete risk set."""
import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = json.loads((ROOT/"data/processed/rare_earths/source_index.json").read_text())
    # project, activity, country, parent, stage, source, reported state, date interval,
    # matching original-language evidence, native amount, native unit/product basis.
    specs = [
      ("MP_MountainPass","MP_mine","USA","MP Materials","mine","RE-MP-10K2025","O","2025-12-31","2025-12-31",r"REO Production Volume \(MTs\) 50,692",None,None,"total REO concentrate"),
      ("MP_MountainPass","MP_separation","USA","MP Materials","separation","RE-MP-10K2025","O","2023-01-01","2023-12-31",r"In 2023, the Company completed an optimization and recommissioning project and commenced midstream operations",6075,"metric tonnes/year planned nameplate","separated NdPr oxide"),
      ("MP_Independence","MP_metal","USA","MP Materials","metal_alloy","RE-MP-10K2024","Q","2024-12-01","2024-12-31",r"In December 2024, the Company commissioned its electrowinning capability to produce NdPr metal from NdPr oxide at Independence",None,None,"NdPr metal"),
      ("MP_Independence","MP_magnet","USA","MP Materials","magnet","RE-MP-10K2025","Q","2025-12-01","2025-12-31",r"At the end of 2025, the Company began commissioning the remaining commercial scale equipment for magnet manufacturing and commenced the manufacturing of its NdFeB permanent magnets",3000,"metric tonnes/year projected expanded capacity","finished NdFeB magnet"),
      ("MP_10X","MP_10X_magnet","USA","MP Materials","magnet","RE-MP-10K2025","A",None,None,r"10X Facility is expected to begin commissioning in 2028, and once completed and scaled, it will produce an estimated 7,000 MTs of magnets per year",7000,"metric tonnes/year projected","finished magnet"),
      ("EF_WhiteMesa","EF_Phase1","USA","Energy Fuels","separation","RE-EF-10K2024","Q","2024-01-01","2024-12-31",r"produced 38 tonnes of separated NdPr during 2024",1000,"metric tonnes/year upper nameplate; lower 800","separated NdPr oxide"),
      ("EF_WhiteMesa","EF_Phase2","USA","Energy Fuels","separation","RE-EF-10K2025","F",None,None,r"combined Phase 1 Circuit and Phase 2 Circuit",6000,"metric tonnes/year projected combined phases; do not add Phase1","NdPr product basis requires confirmation"),
      ("EF_Bahia","EF_Bahia_feed","BRA","Energy Fuels","mine","RE-EF-10K2025","F",None,None,r"potential to supply 3,000 to 10,000 tonnes of monazite per year",10000,"metric tonnes/year potential upper; lower 3000","monazite, not NdPr element"),
      ("EF_Donald","EF_Donald_feed","AUS","Donald JV; Energy Fuels earned interest 9.48% at 2025 year-end","mine","RE-EF-10K2025","F",None,None,r"Donald Project is an HMS and REE project in the pre-development phase",None,None,"monazite/xenotime feed"),
      ("EF_VaraMada_Toliara","EF_VaraMada_feed","MDG","Energy Fuels/Base Resources","mine","RE-EF-10K2025","S","2019-11-01","2019-11-30",r"development at the Project was suspended by the Government of Madagascar in November 2019",None,None,"mineral sands and monazite feed"),
      ("EF_VaraMada_Toliara","EF_VaraMada_feed","MDG","Energy Fuels/Base Resources","mine","RE-EF-10K2025","F","2024-11-01","2024-11-30",r"Government lifted the suspension in November 2024",None,None,"mineral sands and monazite feed"),
      ("RER_BearLodge","RER_BearLodge_feed","USA","Rare Element Resources","mine","RE-RAREELEMENT-10K2025","S","2016-01-01","2016-12-31",r"in 2016, we placed the Bear Lodge REE Project under care-and-maintenance",None,None,"resource is not annual feed"),
      ("RER_BearLodge","RER_BearLodge_feed","USA","Rare Element Resources","mine","RE-RAREELEMENT-10K2025","F","2026-01-01","2026-03-12",r"In early 2026, the Company formally restarted the licensing and permitting of the Bear Lodge REE Project",None,None,"resource is not annual feed"),
      ("RER_UptonDemo","RER_Upton_separation","USA","Rare Element Resources/General Atomics","separation","RE-RAREELEMENT-10K2025","Q","2026-01-01","2026-03-12",r"operations formally commencing in early 2026",10,"native tons TOTAL demonstration campaign, not per year; short/metric unresolved","NdPr oxide; finite stockpiled sample"),
      ("USARE_Stillwater","USARE_Phase1a","USA","USA Rare Earth","magnet","RE-USARE-10K2025","Q","2026-01-01","2026-03-30",r"commissioned Phase 1a of sintered NdFeB permanent magnet block production in the first quarter of 2026",600,"metric tonnes/year planned full rate","sintered NdFeB blocks; orders expected later"),
      ("USARE_Stillwater","USARE_Phase1b","USA","USA Rare Earth","magnet","RE-USARE-10K2025","F",None,None,r"currently procuring equipment and completing engineering for commissioning of Phase 1b",600,"metric tonnes/year projected incremental","sintered NdFeB blocks"),
      ("USARE_RoundTop","USARE_RoundTop_feed","USA","USA Rare Earth","mine","RE-USARE-10K2025","F",None,None,r"Round Top Project \(as defined below\) is at the exploration stage and we have not commenced construction or commission of the mine",None,None,"exploration asset; no operating mine feed"),
      ("LCM","LCM_metal_alloy","GBR","USA Rare Earth after November 2025 acquisition","metal_alloy","RE-USARE-10K2025","O",None,None,r"Current annual capacity is approximately 2,500 MTPA of REE and critical mineral metal and alloy",2500,"metric tonnes/year aggregate mixed REE AND critical minerals","element allocation unknown; not all NdPr"),
      ("Iluka_Eneabba","Iluka_Eneabba_separation","AUS","Iluka Resources","separation","RE-ILUKA-OFFTAKE2026","C",None,None,r"Eneabba refinery, which is now over 50% complete",None,None,"separated oxides; feedstock-dependent product mix"),
      ("Pensana_Longonjo","Pensana_Longonjo_feed","AGO","Pensana/Ozango; mixed ownership requires verification","mine","RE-PENSANA-CONSTRUCTION-PDF","C",None,None,r"main construction activities are now well underway",None,None,"MREC carbonate output requires assay"),
      ("Pensana_Saltend","Pensana_Saltend_separation","GBR","Pensana","separation","RE-PENSANA-ANNUAL2024","S",None,None,r"continued to be put on hold",None,None,"separation project on hold; vintage-public date unverified"),
      ("MP_MountainPass","MP_mine","USA","Molycorp, historical predecessor; MP acquired July 2017","mine","RE-MP-10K2022","S","2015-01-01","2015-12-31",r"Operations relating to mining, milling and separations resumed under Molycorp until they were placed into cold-idle status in mid-2015",None,None,"concentrate; retrospective predecessor history, not a separate duplicate mine"),
      ("MP_MountainPass","MP_separation","USA","Molycorp, historical predecessor; MP acquired July 2017","separation","RE-MP-10K2022","S","2015-01-01","2015-12-31",r"Operations relating to mining, milling and separations resumed under Molycorp until they were placed into cold-idle status in mid-2015",None,None,"historical separation; subsequent restart separately observed"),
      ("MP_MountainPass","MP_mine","USA","MP Materials after July 2017 acquisition","mine","RE-MP-10K2022","O","2017-07-01","2017-07-31",r"Since relaunching production at Mountain Pass in July 2017",None,None,"reported mine/concentrate production relaunch; not separation restart"),
    ]
    rows = []
    for i, (project, activity, country, parent, stage, sid, state, lower, upper, pattern, capacity, unit, product) in enumerate(specs):
        source = sources[sid]
        text = " ".join((ROOT/f"data/interim/{sid}.txt").read_text().replace("\u200b", "").split())
        match = re.search(pattern, text, re.I)
        if not match:
            raise ValueError(f"Unmatched project evidence {sid}: {pattern}")
        # These issuer notices are explicitly dated and discovered through issuer IR.
        public = source.get("publication_date") or {
            "RE-ILUKA-OFFTAKE2026":"2026-06-23",
            "RE-PENSANA-CONSTRUCTION-PDF":"2026-01-14"
        }.get(sid)
        rows.append(dict(record_id=f"PR-{i+1:03}", project_id=project, activity_id=activity,
                         site_country=country, owner_parent=parent, control_group_uncertainty="ultimate control and minority rights not fully adjudicated",
                         stage=stage, state=state, state_evidence="reported, not independently verified commercial operation",
                         event_date_lower=lower, event_date_upper=upper, exact_event_date=None,
                         valid_date=upper, info_public_date=public,
                         date_precision="interval" if lower else "source-date state snapshot only",
                         first_public_date_verified=False, publication_basis="conservative SEC filing/dated issuer release" if public else "missing; document signature is not public release evidence",
                         capacity_native=capacity, native_unit=unit, product_form=product,
                         feedstock_origin="not completely traced", financing="see source; not reduced to a binary financed flag",
                         routes="not fully observed", process_yield="not observed", utilization="not inferred from nameplate",
                         source_id=sid, source_sha256=source["sha256"], locator=pattern,
                         quote=match[0], eligible_for_asof=bool(public and public <= "2026-10-11"),
                         commercial_network_ready=False, cancelled_projects_coverage="incomplete; no claim of exhaustive failure discovery"))
    # Additional issuer histories use the same four production stages, while
    # retaining intermediate product identity and unknown commissioning dates.
    lynas = pd.read_csv(ROOT/"data/processed/rare_earths_additional/lynas_project_history.csv").fillna("")
    products = {
        "Lynas_MtWeld_base": "rare-earth concentrate; assays not entered",
        "Lynas_MtWeld_expansion_Stage1": "concentrate dewatering; shared upstream chain",
        "Lynas_MtWeld_expansion_Stage2": "rare-earth concentrate; expanded plant",
        "Lynas_Malaysia_LRE": "separated light rare-earth oxide product families",
        "Lynas_Malaysia_DyTb_circuit": "separated Dy/Tb oxides; shared mixed-SEGH feed circuit",
        "Lynas_Kalgoorlie_crack_leach": "mixed rare-earth carbonate intermediate, not separated NdPr oxide",
        "Lynas_Texas_HRE": "planned separated heavy rare-earth oxides; cancelled",
    }
    for item in lynas.to_dict("records"):
        rows.append(dict(record_id=item["claim_id"], project_id=item["project_id"], activity_id=item["activity_id"],
                         site_country=item["site_country"], owner_parent="Lynas Rare Earths Ltd",
                         control_group_uncertainty="ultimate control/minority rights not independently adjudicated",
                         stage=item["stage"], state=item["state"], state_evidence="issuer reported; independent stable qualification unverified",
                         event_date_lower=item["event_date_lower"], event_date_upper=item["event_date_upper"],
                         exact_event_date=item["event_date_lower"] if item["event_date_lower"] and item["event_date_lower"] == item["event_date_upper"] else None,
                         valid_date=item["valid_date"], info_public_date=item["info_public_date"], date_precision=item["date_precision"],
                         first_public_date_verified=False, publication_basis=item["publication_basis"],
                         capacity_native=None, native_unit=None, product_form=products[item["activity_id"]],
                         feedstock_origin="Mt Weld Australia for existing chain; complete auxiliary inputs and future third-party feeds untraced",
                         financing="see source; awards and allocations not treated as actual disbursement",
                         routes="some links documented; route capacities and recoveries unknown", process_yield="not observed",
                         utilization="not inferred from nameplate", source_id=item["source_id"], source_sha256=item["source_sha256"],
                         locator=item["locator"], quote=item["quote"], eligible_for_asof=True,
                         commercial_network_ready=False, cancelled_projects_coverage="Texas cancellation retained; global failure discovery incomplete"))
    industrial = pd.read_csv(ROOT/"data/processed/industrial_evidence/project_milestones.csv")
    rows.extend(industrial.to_dict("records"))
    frame = pd.DataFrame(rows)
    target = ROOT/"data/processed/rare_earths"
    frame.to_csv(target/"project_state_evidence.csv", index=False)
    # This roster includes suspended and delayed assets; it is a discovery ledger,
    # not an admissible project-quarter risk set with fully observed entries/exits.
    frame.drop_duplicates("activity_id").to_csv(target/"activity_discovery_registry.csv", index=False)
    pending = [
      ("Lynas_MtWeld_Kalgoorlie_Kuantan", "dated history admitted to discovery roster; ownership/recipes/recoveries/route capacities and full prior entry history still incomplete"),
      ("Arafura_Nolans", "primary site failed; permit/FID/capacity history to acquire"),
      ("NorthernMinerals_BrownsRange", "primary site inaccessible; suspended/demo histories to acquire"),
      ("Hastings_Yangibana", "primary site inaccessible; financing/restructure history to acquire"),
      ("Ucore_RapidSX_Louisiana", "SEC current submission history sparse; issuer stage/finance history needed"),
      ("Rainbow_Phalaborwa", "primary site inaccessible; permit/finance history needed"),
      ("Neo_Silmet_Narva", "primary site inaccessible; commissioning/qualification and feeds needed"),
      ("Noveon_SanMarcos", "primary operating/qualification and feed histories needed"),
      ("VAC_Evac_SouthCarolina", "government award, commissioning/qualification and feed histories needed"),
      ("Molycorp_MountainPass_historical", "retrospective MP filing supports 2015 cold-idle and July2017 production relaunch; original contemporary predecessor/insolvency records still needed"),
    ]
    log = pd.DataFrame(pending, columns=["candidate_project", "evidence_gap"]).assign(status="discovery candidate; not admitted to risk set")
    log.loc[log.candidate_project.str.startswith("Lynas"), "status"] = "dated discovery histories extracted; population hazard risk set still inadmissible"
    added = industrial.drop_duplicates("project_id", keep="last")
    extra = pd.DataFrame({"candidate_project":added.project_id,
                          "evidence_gap":"operator corroboration, entry/exit history, technical recipe, route capacity and independent qualified rate incomplete",
                          "status":"source-linked discovery snapshot; not admitted to representative risk set"})
    log = pd.concat([log, extra], ignore_index=True)
    log.to_csv(ROOT/"metadata/project_inclusion_log.csv", index=False)
    pd.DataFrame([dict(source_id="RE-MOLYCORP-SUBMISSIONS",decision="REJECT_ENTITY_MISMATCH",reason="CIK1287121 resolves to Canada Jetlines, not Molycorp; no claim uses this archive"),
                  dict(source_id="RE-USARE-10K2023;RE-USARE-10K2024",decision="EXCLUDE_INDUSTRIAL_PANEL",reason="pre-merger SPAC observations are not operating-company history"),
                  dict(source_id="RE-LYNAS-REPORTS;RE-LYNAS-ANNUAL2025",decision="EXCLUDE_CHALLENGE_RESPONSE",reason="short HTTP200 response is not the requested report")]).to_csv(ROOT/"metadata/adjudications.csv", index=False)
    print(json.dumps(dict(project_state_records=len(frame), unique_activities=frame.activity_id.nunique(),
                          unique_projects=frame.project_id.nunique(), eligible_public_date_records=int(frame.eligible_for_asof.sum()),
                          complete_statistical_risk_set=False), indent=2))


if __name__ == "__main__":
    main()
