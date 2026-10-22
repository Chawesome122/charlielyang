"""Append source-visible industrial snapshots; never manufacture risk spells."""
import pandas as pd


def supplied_project_snapshots(claims):
    by_variable=claims.set_index('variable')
    specs=[
        ('MP_MountainPass','MP_mine','mine','O','MP Materials','mp_reo_production_2026Q2','positive_reported_period_output'),
        ('MP_MountainPass','MP_separation','separation','O','MP Materials','mp_ndpr_production_2026Q2','positive_reported_period_output'),
        ('MP_10X','MP_10X_magnet','magnet','C','MP Materials','mp_10x_construction_snapshot','source_date_snapshot_event_day_unknown'),
        ('RER_UptonDemo','RER_Upton_separation','separation','Q','Rare Element Resources/General Atomics','rer_demo_start','formal_demonstration_not_full_processing_or_commercial'),
        ('USARE_WheatRidge','USARE_WheatRidge_separation','separation','Q','USA Rare Earth','usar_wheat_ridge_start','hydrometallurgical_demonstration_not_commercial_rate'),
        ('USARE_Blacksburg','USARE_Blacksburg_magnet','magnet','F','USA Rare Earth','usar_blacksburg_plan','engineering_procurement_development_not_commissioned'),
        ('USARE_Blacksburg','USARE_Blacksburg_alloy','metal_alloy','F','USA Rare Earth','usar_blacksburg_plan','engineering_procurement_development_not_commissioned'),
        ('EF_WhiteMesa','EF_Phase1_heavies','separation','C','Energy Fuels','wm_heavies_construction_announcement','construction_announced_actual_start_day_unknown'),
    ]
    rows=[]
    for i,(project,activity,stage,state,owner,variable,meaning) in enumerate(specs,1):
        r=by_variable.loc[variable].fillna('').to_dict()
        # A future commissioning target can document current development, but
        # cannot supply an observed commissioning/state-entry interval.
        window=variable in ['rer_demo_start','usar_wheat_ridge_start']
        lower=r.get('event_start','') if window else r.get('period_start','') if variable.endswith('2026Q2') else ''
        upper=r.get('event_end','') if window else r.get('period_end','') if variable.endswith('2026Q2') else ''
        rows.append(dict(record_id=f'SP-{i:03d}',project_id=project,activity_id=activity,site_country='USA',owner_parent=owner,
                         stage=stage,state=state,state_evidence=meaning+'; issuer reporting, not independent qualification',
                         event_date_lower=lower or None,event_date_upper=upper or None,exact_event_date=None,
                         valid_date=upper or None,info_public_date=r['info_public_date'],date_precision='reported_interval' if lower else 'source_date_snapshot_only',
                         first_public_date_verified=False,publication_basis='verified filing clock for supplied later copy; earliest availability not certified',
                         capacity_native=None,native_unit=None,product_form=r['product_basis'],
                         feedstock_origin='not completely traced',financing='award, commitment, disbursement and FID require distinct evidence',
                         routes='proposed or incomplete; not full China-free network',process_yield='not observed',utilization='not inferred from nameplate',
                         source_id=r['source_id'],source_sha256=r['source_sha256'],locator=r['locator'],pdf_page=int(r['pdf_page']),quote=r['quote'],
                         eligible_for_asof=r['info_public_date']<='2026-10-11',commercial_network_ready=False,
                         cancelled_projects_coverage='selected discovery extension; global failure discovery remains incomplete',
                         control_group_uncertainty='ultimate control, minority rights and all-input origins not fully adjudicated'))
    return pd.DataFrame(rows)
