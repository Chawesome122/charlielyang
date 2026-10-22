"""Descriptive ownership and documentary event clocks from original MP filings."""
from pathlib import Path
import json
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/weaponized-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'data/processed/operating_origin_extension'
    frame=pd.read_csv(source/'observations.csv',keep_default_na=False)
    equity=pd.read_csv(source/'reported_equity_closure.csv')
    admission=pd.read_csv(source/'route_evidence_admission.csv')
    if frame.claim_id.duplicated().any() or len(frame)!=33 or equity.share_sum_percent.ne(100).any():
        raise ValueError('Operating-origin input/count/equity identity changed')
    if admission.full_route_data_admitted.any():raise ValueError('Incomplete physical routes were admitted')
    events=[('MPOR-2023-VREX-MP-EQUITY','MP equity acquisition','Dec 2023'),
            ('MPOR-2025-VREX-DISPOSAL','MP equity disposal','May 2025'),
            ('MPOR-2025-CHINA-SALES-CEASE','China sales cessation','Jul 2025'),
            ('MPOR-2025-INTERNAL-FEED','Internal oxide feed','Oct--Dec 2025')]
    rows=[]
    for identifier,label,interval in events:
        row=frame[frame.claim_id.eq(identifier)].iloc[0]
        low,high,public=[pd.Timestamp(row[k]) for k in ['event_date_lower','event_date_upper','info_public_date']]
        if not low<=high<=public or public>pd.Timestamp('2026-10-11'):raise ValueError('Invalid documentary event/public clock')
        rows.append(dict(claim_id=identifier,event=label,reported_interval=interval,event_date_lower=str(low.date()),event_date_upper=str(high.date()),
                         selected_original_public_date=str(public.date()),source_id=row.source_id,source_sha256=row.source_sha256,
                         exact_event_day_identified=False,globally_earliest_disclosure_identified=False,
                         reporting_delay_identified=False,causal_restriction_effect_identified=False))
    out=ROOT/'outputs/empirical/rare_earths/operating_origin_extension';out.mkdir(parents=True,exist_ok=True)
    clocks=pd.DataFrame(rows);clocks.to_csv(out/'event_clock_table.csv',index=False)
    fig,(ax,clockax)=plt.subplots(1,2,figsize=(11.5,4.6),gridspec_kw={'width_ratios':[1,1.9]})
    x=range(len(equity))
    ax.bar(x,equity.MP_percent,color='#246a8a',label='MP')
    ax.bar(x,equity.Shenghe_percent,bottom=equity.MP_percent,color='#bb6b37',label='Shenghe')
    for i in x:
        ax.text(i,24.5,'49%',ha='center',va='center',color='white')
        ax.text(i,74.5,'51%',ha='center',va='center',color='white')
    ax.set(ylim=(0,104),xticks=list(x),xticklabels=['FY2023 original','FY2024 original'],ylabel='Reported equity share (%)',title='VREX Holdco ownership snapshots')
    ax.legend(loc='lower left',bbox_to_anchor=(0,-.23),ncol=2,fontsize=8)
    ax.text(.5,-.31,'Holdco: Singapore; operating plant: Vietnam',transform=ax.transAxes,ha='center',fontsize=8)
    for i,row in enumerate(rows):
        low,high,public=[pd.Timestamp(row[k]) for k in ['event_date_lower','event_date_upper','selected_original_public_date']]
        clockax.plot([low,high],[i,i],lw=7,color='#246a8a',solid_capstyle='butt',label='Reported event interval' if i==0 else None)
        clockax.plot([high,public],[i,i],ls=':',color='#888888',lw=1)
        clockax.scatter([public],[i],marker='D',color='#222222',s=28,zorder=3,label='Selected original available' if i==0 else None)
    clockax.set(yticks=range(len(rows)),yticklabels=[r['event'] for r in rows],title='Reported intervals and selected-file public dates',xlim=(pd.Timestamp('2023-10-01'),pd.Timestamp('2026-05-01')))
    clockax.invert_yaxis();clockax.xaxis.set_major_locator(mdates.MonthLocator(interval=6));clockax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    clockax.tick_params(axis='x',rotation=25,labelsize=8);clockax.grid(axis='x',alpha=.2)
    clockax.legend(loc='lower left',bbox_to_anchor=(0,-.40),fontsize=8)
    fig.suptitle('Issuer-reported commercial relationships; no full China-free route or causal-effect certification',fontsize=11)
    fig.tight_layout()
    for extension in ['pdf','png']:fig.savefig(out/f'ownership_and_documentary_clocks.{extension}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    lines=[r'\begin{tabular}{lll}\toprule',r'Event & Reported interval & Selected original public date \\\midrule']
    for row in rows:lines.append(f"{row['event']} & {row['reported_interval']} & {row['selected_original_public_date']}"+r' \\')
    lines.append(r'\bottomrule\end{tabular}')
    (ROOT/'manuscript/operating_origin_extension_table.tex').write_text('\n'.join(lines)+'\n')
    result=dict(passed=True,classification='actual_issuer_disclosures_and_archive_public_clocks_not_causal_or_service_estimates',
                exact_quoted_event_clocks=len(rows),reported_ownership_snapshots=len(equity),empirical_service_estimated=False,
                current_ownership_certified=False,global_first_public_dates_certified=False,reporting_delay_distribution_estimated=False,
                China_sales_cessation_certifies_all_input_origins=False,procurement_dollars_are_physical_quantities=False)
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
