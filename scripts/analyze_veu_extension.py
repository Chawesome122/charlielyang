"""Source-descriptive VEU scope/clock exhibits, not a technological-access index."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR','/tmp/weaponized-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'data/processed/veu_extension'
    events=pd.read_csv(source/'issued_events.csv').fillna('')
    clocks=pd.read_csv(source/'source_clocks.csv')
    phases=pd.read_csv(source/'origin_phase_checks.csv')
    if len(events)!=5 or len(clocks)!=2 or len(phases)!=11:
        raise ValueError('VEU analysis input shape mismatch')
    if (events.current_law_consolidation_verified.astype(str).str.lower()!='false').any() or any(events[field].ne('').any() for field in ['domestic_capability_score','foreign_access_score','observed_license_outcome']):
        raise ValueError('VEU scope analysis cannot carry measured access or current-law claims')
    permission=events[events.event_kind.eq('permission_scope_amendment')].copy()
    removed=events[events.event_kind.eq('authorization_removal')]
    if not (permission.eligible_items.str.contains('extreme ultraviolet',regex=False)&permission.eligible_items.str.contains('748.15(d)',regex=False)).all():
        raise ValueError('VEU permission scope lost material exclusions/cross-reference')
    if set(removed.effective_date)!= {'2025-12-31'} or len(permission)!=2 or len(removed)!=3:
        raise ValueError('VEU source event action/date mismatch')
    out=ROOT/'outputs/empirical/semiconductors/veu_extension';out.mkdir(parents=True,exist_ok=True)
    table=[]
    for row in permission.to_dict('records'):
        matching=removed[removed.party_id.eq(row['party_id'])]
        if len(matching)!=1:raise ValueError('VEU paired removal missing or duplicated')
        table.append(dict(party_id=row['party_id'],party_name=row['party_name'],memory_scope=row['memory_scope'],
                          eligible_destination=row['eligible_destination'],eligible_items=row['eligible_items'],
                          permission_amendment_effective=row['effective_date'],paired_removal_effective=matching.iloc[0].effective_date,
                          actual_access_observed=False,complete_authorization_history_verified=False))
    pd.DataFrame(table).to_csv(out/'scope_summary.csv',index=False)
    tex=[r'\begin{tabular}{llll}\toprule',r'Named recipient / location & Memory & Scope amendment & Removal \\\midrule',
         r'Samsung / Xi\textquotesingle an & NAND & 2023-10-17 & 2025-12-31 \\',
         r'SK hynix / Wuxi & DRAM & 2023-10-17 & 2025-12-31 \\',
         r'Intel / Dalian & Not extracted & Not extracted & 2025-12-31 \\',r'\bottomrule\end{tabular}']
    (out/'scope_table.tex').write_text('\n'.join(tex)+'\n')
    fig,ax=plt.subplots(figsize=(8.2,3.2))
    for y,row in enumerate(clocks.to_dict('records')):
        ax.plot([-row['reported_filing_lead_days'],0],[y,y],color='#b5b5b5',lw=1)
        ax.scatter(-row['reported_filing_lead_days'],y,marker='o',s=60,color='#236a8a',label='Reported filing' if y==0 else None,zorder=3)
        ax.scatter(-row['publication_lead_days'],y,marker='s',s=42,color='#bd6b29',label='FR publication' if y==0 else None,zorder=4)
        ax.scatter(0,y,marker='|',s=210,color='black',label='Legal effect' if y==0 else None,zorder=5)
        ax.annotate(f"{row['reported_filing_lead_days']} / {row['publication_lead_days']} days",(-row['reported_filing_lead_days'],y),xytext=(-3 if row['reported_filing_lead_days']<20 else 3,12),ha='right' if row['reported_filing_lead_days']<20 else 'left',textcoords='offset points',fontsize=8)
    ax.set(yticks=[0,1],yticklabels=['2023 scope amendments','2025 named removals'],xlabel='Days relative to the printed legal effective date',xlim=(-135,10),ylim=(-.5,1.5),title='Selected VEU instruments: notice and legal effect are separate clocks')
    ax.legend(loc='lower left',fontsize=8,ncol=3);ax.grid(axis='x',alpha=.2)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(out/f'document_clocks.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    result=dict(passed=True,classification='primary_legal_descriptive_selected_issued_instruments',
                permission_scope_entries=2,removal_entries=3,paired_named_recipients=2,
                removal_publication_to_effect_days=120,removal_reported_filing_to_effect_days=124,
                both_2023_scopes_explicitly_exclude_EUV=True,source_scope_is_a_complete_EAR_classifier=False,
                domestic_capability_identified=False,foreign_access_identified=False,license_outcome_observed=False,
                continuous_authorization_between_sources_certified=False,current_law_consolidated=False,
                causal_effect_identified=False,scope='Documentary permission/removal and clock evidence only; original clauses and other EAR conditions remain essential')
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
