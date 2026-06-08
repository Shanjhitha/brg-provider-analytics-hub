import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="BRG Provider Analytics Hub",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp { background: #0F172A; color: #F1F5F9; }
.main .block-container { padding: 2rem 2.5rem; max-width: 1500px; }

section[data-testid="stSidebar"] { background: #020617; }
section[data-testid="stSidebar"] * { color: #94A3B8 !important; }
section[data-testid="stSidebar"] .stSelectbox label {
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    color: #475569 !important;
}

div[data-testid="stRadio"] label {
    color: #64748B !important; padding: 9px 16px !important;
    border-radius: 8px !important; margin: 1px 6px !important;
    font-size: 13px !important; font-weight: 500 !important;
}
div[data-testid="stRadio"] label:hover { background: #1E293B !important; color: #CBD5E1 !important; }

.hero {
    background: linear-gradient(135deg, #1D4ED8 0%, #7C3AED 100%);
    border-radius: 20px; padding: 2.2rem 2.5rem;
    margin-bottom: 2rem; display: flex;
    justify-content: space-between; align-items: center;
}
.hero-title { font-size: 2rem; font-weight: 800; color: white; letter-spacing: -0.03em; }
.hero-sub { font-size: 0.95rem; color: rgba(255,255,255,0.7); margin-top: 4px; }
.hero-pill {
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);
    padding: 8px 18px; border-radius: 99px; color: white;
    font-size: 0.8rem; font-weight: 600; backdrop-filter: blur(8px);
}

.stats { display: flex; gap: 14px; margin-bottom: 2rem; }
.stat {
    flex: 1; background: #1E293B; border: 1px solid #334155;
    border-radius: 16px; padding: 1.4rem 1.2rem; position: relative; overflow: hidden;
}
.stat-accent { position: absolute; top: 0; left: 0; right: 0; height: 3px; background: #3B82F6; border-radius: 16px 16px 0 0; }
.stat-accent.purple { background: #7C3AED; }
.stat-accent.green  { background: #10B981; }
.stat-accent.red    { background: #EF4444; }
.stat-accent.amber  { background: #F59E0B; }
.stat-n { font-size: 2rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.04em; line-height: 1; margin-bottom: 6px; }
.stat-l { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #64748B; }

.card { background: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 1.6rem; margin-bottom: 1.4rem; }
.card-t { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: #64748B; margin-bottom: 1.2rem; }

.row { display: flex; align-items: center; padding: 11px 0; border-bottom: 1px solid #1E293B; gap: 12px; }
.row:last-child { border-bottom: none; }
.icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; }
.icon-b { background: #1D4ED820; }
.icon-r { background: #EF444420; }
.icon-g { background: #10B98120; }
.row-name { font-size: 0.92rem; font-weight: 600; color: #E2E8F0; }
.row-val { font-size: 1.2rem; font-weight: 800; color: #60A5FA; margin-left: auto; }
.row-val.red { color: #F87171; }
.row-val.green { color: #34D399; }

.pill-b { display:inline-block; background:#1D4ED840; color:#93C5FD; font-size:0.68rem; font-weight:700; padding:2px 10px; border-radius:99px; }
.pill-r { display:inline-block; background:#EF444430; color:#FCA5A5; font-size:0.68rem; font-weight:700; padding:2px 10px; border-radius:99px; }
.pill-g { display:inline-block; background:#10B98130; color:#6EE7B7; font-size:0.68rem; font-weight:700; padding:2px 10px; border-radius:99px; }

.opp { background: #0F172A; border: 1px solid #334155; border-left: 3px solid #7C3AED; border-radius: 0 12px 12px 0; padding: 1rem 1.2rem; margin-bottom: 0.7rem; display:flex; gap:14px; align-items:center; }
.opp-l { flex:1; }
.opp-sl { font-size:0.95rem; font-weight:700; color:#E2E8F0; margin-bottom:3px; }
.opp-d  { font-size:0.8rem; color:#64748B; }
.opp-g  { font-size:1.5rem; font-weight:800; color:#F87171; white-space:nowrap; }

.pain { background:#0F172A; border:1px solid #334155; border-left:3px solid #EF4444; border-radius:0 12px 12px 0; padding:1rem 1.2rem; margin-bottom:0.7rem; }
.str  { background:#0F172A; border:1px solid #334155; border-left:3px solid #10B981; border-radius:0 12px 12px 0; padding:1rem 1.2rem; margin-bottom:0.7rem; }

.disc { background:#1D4ED810; border:1px solid #1D4ED840; border-left:3px solid #3B82F6; border-radius:0 12px 12px 0; padding:1rem 1.4rem; margin-bottom:0.7rem; display:flex; gap:12px; }
.disc-n { background:#3B82F6; color:white; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:0.72rem; font-weight:800; flex-shrink:0; margin-top:2px; }
.disc-t { font-size:0.9rem; color:#CBD5E1; line-height:1.6; }

.sidebar-top { padding:22px 16px 16px; border-bottom:1px solid #1E293B; }
.brand { font-size:1.15rem; font-weight:800; color:#F1F5F9; }
.brand span { color:#818CF8; }
.tagline { font-size:0.65rem; color:#475569; text-transform:uppercase; letter-spacing:0.12em; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        user=os.environ.get('SNOWFLAKE_USER'),
        password=os.environ.get('SNOWFLAKE_PASSWORD'),
        account='lfzytsf-ot13072',
        warehouse='COMPUTE_WH',
        database='BRG_PROVIDER_ANALYTICS',
        schema='ANALYTICS'
    )

@st.cache_data(ttl=300)
def qry(sql):
    return pd.read_sql(sql, get_conn())

@st.cache_data(ttl=300)
def all_data():
    return qry("SELECT * FROM BRG_PROVIDER_ANALYTICS.ANALYTICS.VW_MARKET_SHARE")

@st.cache_data(ttl=300)
def states():
    return qry("SELECT DISTINCT STATE FROM BRG_PROVIDER_ANALYTICS.ANALYTICS.VW_MARKET_SHARE ORDER BY STATE")['STATE'].tolist()

DARK = '#0F172A'
CARD = '#1E293B'
BORD = '#334155'
T1   = '#F1F5F9'
T2   = '#94A3B8'
T3   = '#64748B'
BLUE = '#3B82F6'
PURP = '#818CF8'
GREE = '#34D399'
RED  = '#F87171'
AMBE = '#FBBF24'

def chart(fig, h=380, lm=20):
    fig.update_layout(
        plot_bgcolor=DARK, paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=T2, size=13),
        height=h, margin=dict(l=lm, r=20, t=36, b=20),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color=T2, size=12))
    )
    fig.update_xaxes(gridcolor=BORD, showline=False, tickfont=dict(color=T2, size=12), title_font=dict(color=T3))
    fig.update_yaxes(gridcolor=BORD, showline=False, tickfont=dict(color=T2, size=12), title_font=dict(color=T3))
    return fig

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("""
    <div class="sidebar-top">
        <div class="brand">BRG <span>Analytics</span></div>
        <div class="tagline">Provider Intelligence Hub</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='padding:12px 8px 8px'>", unsafe_allow_html=True)

    state_list = states()
    sel_state = st.selectbox("Market", state_list,
        index=state_list.index('VA') if 'VA' in state_list else 0)

    df = all_data()
    df_s = df[df['STATE']==sel_state]
    sys_list = sorted(df_s['HEALTH_SYSTEM'].unique())
    sel_sys = st.selectbox("Focus Provider", sys_list,
        index=list(sys_list).index('Inova Health System') if 'Inova Health System' in sys_list else 0)

    sl_list = sorted(df_s['SERVICE_LINE'].unique())
    sel_sl = st.selectbox("Service Line", ["All"] + list(sl_list))

    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()

    page = st.radio("", [
        "Executive Summary", "Market Share Analysis",
        "Service Line Analysis", "Competitor Landscape",
        "Pursuit Analytics", "Definitions & Sources"
    ], label_visibility="collapsed")

    st.markdown("<div style='padding:8px 16px'><p style='font-size:0.65rem;color:#334155'>CMS Medicare 2024 · BRG © 2026</p></div>", unsafe_allow_html=True)

def gs(state, system, sl="All"):
    d = df[(df['STATE']==state)&(df['HEALTH_SYSTEM']==system)]
    return d[d['SERVICE_LINE']==sl] if sl!="All" else d

def gst(state, sl="All"):
    d = df[df['STATE']==state]
    return d[d['SERVICE_LINE']==sl] if sl!="All" else d

# ════════════════════ PAGE 1 ════════════════════
if page == "Executive Summary":
    d_sys = gs(sel_state, sel_sys, sel_sl)
    d_full = gs(sel_state, sel_sys)

    st.markdown(f"""
    <div class="hero">
        <div>
            <div class="hero-title">{sel_sys}</div>
            <div class="hero-sub">Executive Summary &nbsp;·&nbsp; {sel_state} Market &nbsp;·&nbsp; CMS Medicare 2024</div>
        </div>
        <div class="hero-pill">Provider Analytics Hub</div>
    </div>""", unsafe_allow_html=True)

    if d_sys.empty:
        st.warning("No data for selected filters.")
    else:
        tv = d_full['SYSTEM_DISCHARGES'].sum()
        tm = df[df['STATE']==sel_state].groupby('SERVICE_LINE')['TOTAL_MARKET_DISCHARGES'].first().sum()
        ov = round(tv/tm*100,2) if tm>0 else 0
        top_sl = d_full.loc[d_full['MARKET_SHARE_PCT'].idxmax(),'SERVICE_LINE']
        wk_sl  = d_full.loc[d_full['MARKET_SHARE_PCT'].idxmin(),'SERVICE_LINE']
        br = int(d_full['MARKET_RANK'].min())
        nt = len(d_full[d_full['MARKET_RANK']<=2])

        st.markdown(f"""
        <div class="stats">
            <div class="stat"><div class="stat-accent purple"></div>
                <div class="stat-n">{ov}%</div><div class="stat-l">Overall Market Share</div></div>
            <div class="stat"><div class="stat-accent"></div>
                <div class="stat-n">#{br}</div><div class="stat-l">Best Rank</div></div>
            <div class="stat"><div class="stat-accent amber"></div>
                <div class="stat-n">{tv:,.0f}</div><div class="stat-l">Total Discharges</div></div>
            <div class="stat"><div class="stat-accent green"></div>
                <div class="stat-n" style="font-size:1.2rem;color:#34D399">{top_sl}</div>
                <div class="stat-l">Strongest Service Line</div></div>
            <div class="stat"><div class="stat-accent red"></div>
                <div class="stat-n" style="font-size:1.2rem;color:#F87171">{wk_sl}</div>
                <div class="stat-l">Watch Area</div></div>
            <div class="stat"><div class="stat-accent amber"></div>
                <div class="stat-n" style="color:#FBBF24">{nt}</div>
                <div class="stat-l">Top-2 Rankings</div></div>
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns([1.7, 1])
        with c1:
            st.markdown('<div class="card"><div class="card-t">Market Share by Service Line</div>', unsafe_allow_html=True)
            dc = d_sys.sort_values('MARKET_SHARE_PCT', ascending=True)
            clrs = [BLUE if v >= dc['MARKET_SHARE_PCT'].quantile(0.6) else '#334155' for v in dc['MARKET_SHARE_PCT']]
            fig = go.Figure(go.Bar(
                x=dc['MARKET_SHARE_PCT'], y=dc['SERVICE_LINE'], orientation='h',
                marker_color=clrs,
                text=dc['MARKET_SHARE_PCT'].apply(lambda x: f'{x:.1f}%'),
                textposition='outside', textfont=dict(size=13, color=T1)
            ))
            fig = chart(fig, 480, lm=160)
            fig.update_xaxes(title='Market Share %')
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card"><div class="card-t">Top Performers</div>', unsafe_allow_html=True)
            for _, r in d_sys.nlargest(4,'MARKET_SHARE_PCT').iterrows():
                st.markdown(f"""
                <div class="row">
                    <div class="icon icon-b">📊</div>
                    <div><div class="row-name">{r['SERVICE_LINE']}</div>
                        <span class="pill-b">Rank #{int(r['MARKET_RANK'])}</span></div>
                    <div class="row-val">{r['MARKET_SHARE_PCT']}%</div>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card"><div class="card-t">Watch Areas</div>', unsafe_allow_html=True)
            for _, r in d_sys.nsmallest(3,'MARKET_SHARE_PCT').iterrows():
                st.markdown(f"""
                <div class="row">
                    <div class="icon icon-r">⚠️</div>
                    <div><div class="row-name">{r['SERVICE_LINE']}</div>
                        <span class="pill-r">Rank #{int(r['MARKET_RANK'])}</span></div>
                    <div class="row-val red">{r['MARKET_SHARE_PCT']}%</div>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════ PAGE 2 ════════════════════
elif page == "Market Share Analysis":
    st.markdown(f"""
    <div class="hero">
        <div><div class="hero-title">Market Share Analysis</div>
            <div class="hero-sub">{sel_state} Market · All Health Systems</div></div>
        <div class="hero-pill">{sel_state} Market</div>
    </div>""", unsafe_allow_html=True)

    dst = gst(sel_state, sel_sl)
    dov = dst.groupby('HEALTH_SYSTEM').agg(t=('SYSTEM_DISCHARGES','sum')).reset_index()
    tm  = dov['t'].sum()
    dov['s'] = (dov['t']/tm*100).round(2)
    dov = dov.sort_values('s', ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><div class="card-t">Share Distribution</div>', unsafe_allow_html=True)
        fig = px.pie(dov, values='s', names='HEALTH_SYSTEM', hole=0.52,
            color_discrete_sequence=['#3B82F6','#7C3AED','#10B981','#F59E0B','#EF4444','#06B6D4','#8B5CF6','#F97316'])
        fig.update_traces(textposition='outside', textinfo='percent+label',
            textfont=dict(size=12, color=T1))
        fig = chart(fig, 360)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><div class="card-t">Share by System</div>', unsafe_allow_html=True)
        cb = [PURP if h==sel_sys else BLUE for h in dov['HEALTH_SYSTEM']]
        fig2 = go.Figure(go.Bar(
            x=dov['HEALTH_SYSTEM'], y=dov['s'], marker_color=cb,
            text=dov['s'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside', textfont=dict(size=13, color=T1)
        ))
        fig2 = chart(fig2, 360)
        fig2.update_xaxes(tickangle=-30)
        fig2.update_yaxes(title='Market Share %')
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-t">Service Line Breakdown</div>', unsafe_allow_html=True)
    sl_pick = st.selectbox("Service Line", sl_list, key='ms_sl')
    dsl = df[(df['STATE']==sel_state)&(df['SERVICE_LINE']==sl_pick)].sort_values('MARKET_SHARE_PCT',ascending=False)
    csl = [PURP if h==sel_sys else BLUE for h in dsl['HEALTH_SYSTEM']]
    fig3 = go.Figure(go.Bar(
        x=dsl['HEALTH_SYSTEM'], y=dsl['MARKET_SHARE_PCT'], marker_color=csl,
        text=dsl['MARKET_SHARE_PCT'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside', textfont=dict(size=14, color=T1)
    ))
    fig3 = chart(fig3, 360)
    fig3.update_layout(title=dict(text=f'{sl_pick} — {sel_state}', font=dict(size=15, color=T1)))
    fig3.update_xaxes(tickangle=-25)
    fig3.update_yaxes(title='Market Share %')
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Full Data Table"):
        d = dst[['HEALTH_SYSTEM','SERVICE_LINE','SYSTEM_DISCHARGES','MARKET_SHARE_PCT','MARKET_RANK','AVG_PAYMENT']].copy()
        d.columns=['Health System','Service Line','Discharges','Share %','Rank','Avg Payment']
        st.dataframe(d.sort_values(['Service Line','Rank']), use_container_width=True, hide_index=True)

# ════════════════════ PAGE 3 ════════════════════
elif page == "Service Line Analysis":
    dsys = gs(sel_state, sel_sys, sel_sl)
    st.markdown(f"""
    <div class="hero">
        <div><div class="hero-title">Service Line Analysis</div>
            <div class="hero-sub">{sel_sys} · {sel_state} Market</div></div>
        <div class="hero-pill">{len(dsys)} Lines</div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><div class="card-t">Discharge Volume</div>', unsafe_allow_html=True)
        dv = dsys.sort_values('SYSTEM_DISCHARGES', ascending=True)
        fig = px.bar(dv, x='SYSTEM_DISCHARGES', y='SERVICE_LINE', orientation='h',
            color='SYSTEM_DISCHARGES', color_continuous_scale=[BORD, BLUE],
            text=dv['SYSTEM_DISCHARGES'].apply(lambda x: f'{x:,.0f}'))
        fig.update_traces(textposition='outside', textfont=dict(size=12, color=T1))
        fig = chart(fig, 520, lm=160)
        fig.update_layout(coloraxis_showscale=False)
        fig.update_xaxes(title='Total Discharges')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><div class="card-t">Competitive Rank</div>', unsafe_allow_html=True)
        dr = dsys.sort_values('MARKET_RANK')
        rc = [GREE if r<=2 else AMBE if r<=3 else RED for r in dr['MARKET_RANK']]
        fig2 = go.Figure(go.Bar(
            x=dr['SERVICE_LINE'], y=dr['MARKET_RANK'], marker_color=rc,
            text=[f'#{int(r)}' for r in dr['MARKET_RANK']],
            textposition='outside', textfont=dict(size=14, color=T1)
        ))
        fig2 = chart(fig2, 520)
        fig2.update_yaxes(
            autorange='reversed',
            title='Rank (1=best)',
            tickvals=list(range(1, int(dr['MARKET_RANK'].max())+1)),
            ticktext=[f'#{i}' for i in range(1, int(dr['MARKET_RANK'].max())+1)],
            range=[0.5, int(dr['MARKET_RANK'].max())+0.5]
        )
        fig2.update_xaxes(tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-t">Market Share vs Payment (Bubble = Volume)</div>', unsafe_allow_html=True)
    fig3 = px.scatter(dsys, x='MARKET_SHARE_PCT', y='AVG_PAYMENT',
        size='SYSTEM_DISCHARGES', color='SERVICE_LINE', hover_name='SERVICE_LINE',
        size_max=55, color_discrete_sequence=['#3B82F6','#7C3AED','#10B981','#F59E0B',
            '#EF4444','#06B6D4','#8B5CF6','#F97316','#EC4899','#14B8A6','#A78BFA','#FB7185'],
        labels={'MARKET_SHARE_PCT':'Market Share %','AVG_PAYMENT':'Avg Medicare Payment ($)'})
    fig3 = chart(fig3, 400)
    fig3.update_traces(marker=dict(opacity=0.85, line=dict(width=1.5, color='white')))
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════ PAGE 4 ════════════════════
elif page == "Competitor Landscape":
    dst = gst(sel_state)
    st.markdown(f"""
    <div class="hero">
        <div><div class="hero-title">Competitor Landscape</div>
            <div class="hero-sub">{sel_sys} vs Peers · {sel_state} Market</div></div>
        <div class="hero-pill">Head-to-Head</div>
    </div>""", unsafe_allow_html=True)

    csl = st.selectbox("Service Line", sl_list, key='comp_sl')
    dc = dst[dst['SERVICE_LINE']==csl].sort_values('MARKET_SHARE_PCT', ascending=False)
    cc = [PURP if h==sel_sys else BLUE for h in dc['HEALTH_SYSTEM']]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="card"><div class="card-t">{csl} Market Share</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=dc['HEALTH_SYSTEM'], y=dc['MARKET_SHARE_PCT'], marker_color=cc,
            text=dc['MARKET_SHARE_PCT'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside', textfont=dict(size=14, color=T1)
        ))
        fig = chart(fig, 360)
        fig.update_xaxes(tickangle=-30)
        fig.update_yaxes(title='Market Share %')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><div class="card-t">Average Payment Comparison</div>', unsafe_allow_html=True)
        fig2 = go.Figure(go.Bar(
            x=dc['HEALTH_SYSTEM'], y=dc['AVG_PAYMENT'], marker_color=cc,
            text=dc['AVG_PAYMENT'].apply(lambda x: f'${x:,.0f}'),
            textposition='outside', textfont=dict(size=13, color=T1)
        ))
        fig2 = chart(fig2, 360)
        fig2.update_xaxes(tickangle=-30)
        fig2.update_yaxes(title='Avg Medicare Payment ($)')
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-t">Full Competitive Heatmap</div>', unsafe_allow_html=True)
    dh = dst.pivot_table(index='HEALTH_SYSTEM', columns='SERVICE_LINE',
        values='MARKET_SHARE_PCT', aggfunc='sum').fillna(0)
    fig3 = px.imshow(dh, color_continuous_scale=[DARK, BLUE],
        labels=dict(color='Share %'), aspect='auto')
    fig3 = chart(fig3, 400)
    fig3.update_xaxes(tickangle=-35, tickfont=dict(size=11, color=T2))
    fig3.update_yaxes(tickfont=dict(size=12, color=T2))
    fig3.update_coloraxes(colorbar=dict(tickfont=dict(color=T2)))
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════ PAGE 5 ════════════════════
elif page == "Pursuit Analytics":
    dsys = gs(sel_state, sel_sys)
    dst  = gst(sel_state)
    st.markdown(f"""
    <div class="hero">
        <div><div class="hero-title">Pursuit Analytics</div>
            <div class="hero-sub">{sel_sys} · Consulting Opportunity Assessment</div></div>
        <div class="hero-pill">Opportunity Report</div>
    </div>""", unsafe_allow_html=True)

    if dsys.empty:
        st.warning("No data.")
    else:
        pain   = dsys[dsys['MARKET_RANK']>=3].sort_values('MARKET_RANK',ascending=False)
        strong = dsys[dsys['MARKET_RANK']<=2].sort_values('MARKET_SHARE_PCT',ascending=False)
        opps   = []
        for sl in dsys['SERVICE_LINE'].unique():
            mine = dsys[dsys['SERVICE_LINE']==sl]['MARKET_SHARE_PCT'].values
            ldr  = dst[dst['SERVICE_LINE']==sl]['MARKET_SHARE_PCT'].max()
            if len(mine)>0 and ldr-mine[0]>5:
                ln = dst[(dst['SERVICE_LINE']==sl)&(dst['MARKET_SHARE_PCT']==ldr)]['HEALTH_SYSTEM'].values
                opps.append({'sl':sl,'mine':mine[0],'ldr':ldr,'gap':round(ldr-mine[0],2),
                    'ln': ln[0] if len(ln)>0 else 'Unknown'})

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card"><div class="card-t">⚠ Pain Points</div>', unsafe_allow_html=True)
            if pain.empty:
                st.success("No significant pain points.")
            else:
                for _, r in pain.head(6).iterrows():
                    ldr = dst[(dst['SERVICE_LINE']==r['SERVICE_LINE'])&(dst['MARKET_RANK']==1)]
                    ln = ldr['HEALTH_SYSTEM'].values[0] if len(ldr)>0 else 'Unknown'
                    ls = ldr['MARKET_SHARE_PCT'].values[0] if len(ldr)>0 else 0
                    g  = round(ls-r['MARKET_SHARE_PCT'],2)
                    st.markdown(f"""
                    <div class="pain">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div style="font-size:0.95rem;font-weight:700;color:#FCA5A5">{r['SERVICE_LINE']}</div>
                            <span class="pill-r">Rank #{int(r['MARKET_RANK'])}</span>
                        </div>
                        <div style="font-size:0.82rem;color:#64748B;margin-top:5px">
                            {r['MARKET_SHARE_PCT']}% share · Leader: {ln} at {ls}%
                        </div>
                        <div style="font-size:0.9rem;font-weight:700;color:#F87171;margin-top:4px">Gap: -{g}%</div>
                    </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card"><div class="card-t">✓ Strengths</div>', unsafe_allow_html=True)
            if strong.empty:
                st.info("No top-2 rankings.")
            else:
                for _, r in strong.iterrows():
                    st.markdown(f"""
                    <div class="str">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div style="font-size:0.95rem;font-weight:700;color:#6EE7B7">{r['SERVICE_LINE']}</div>
                            <span class="pill-g">Rank #{int(r['MARKET_RANK'])}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-top:5px">
                            <span style="font-size:0.82rem;color:#64748B">{r['SYSTEM_DISCHARGES']:,.0f} discharges</span>
                            <span style="font-size:1.1rem;font-weight:800;color:#34D399">{r['MARKET_SHARE_PCT']}%</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-t">Consulting Opportunities</div>', unsafe_allow_html=True)
        if not opps:
            st.info("No major gaps identified.")
        else:
            for o in sorted(opps, key=lambda x: x['gap'], reverse=True)[:5]:
                st.markdown(f"""
                <div class="opp">
                    <div class="opp-l">
                        <div class="opp-sl">{o['sl']} — Growth Opportunity</div>
                        <div class="opp-d">Current: {o['mine']}% · Leader ({o['ln']}): {o['ldr']}% · Service line strategy assessment</div>
                    </div>
                    <div class="opp-g">-{o['gap']}%</div>
                </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-t">Director Discussion Guide</div>', unsafe_allow_html=True)
        pts = []
        if not pain.empty:
            tp = pain.iloc[0]
            ldr = dst[(dst['SERVICE_LINE']==tp['SERVICE_LINE'])&(dst['MARKET_RANK']==1)]
            ln = ldr['HEALTH_SYSTEM'].values[0] if len(ldr)>0 else 'the market leader'
            pts.append(f"<strong style='color:{T1}'>Market Position:</strong> {sel_sys} ranks #{int(tp['MARKET_RANK'])} in {tp['SERVICE_LINE']} at {tp['MARKET_SHARE_PCT']}% share. What is driving the gap to {ln}?")
        if not strong.empty:
            ts = strong.iloc[0]
            pts.append(f"<strong style='color:{T1}'>Competitive Advantage:</strong> #{int(ts['MARKET_RANK'])} position in {ts['SERVICE_LINE']} ({ts['MARKET_SHARE_PCT']}%). How is this being leveraged system-wide?")
        if opps:
            to = sorted(opps, key=lambda x: x['gap'], reverse=True)[0]
            pts.append(f"<strong style='color:{T1}'>Growth Opportunity:</strong> {to['gap']}% share gap in {to['sl']} vs {to['ln']}. Is there appetite for a service line growth strategy?")
        pts.append(f"<strong style='color:{T1}'>Payment Efficiency:</strong> Average Medicare payment benchmarking reveals potential revenue cycle optimization opportunities.")
        for i, p in enumerate(pts,1):
            st.markdown(f"""
            <div class="disc">
                <div class="disc-n">{i}</div>
                <div class="disc-t">{p}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════ PAGE 6 ════════════════════
elif page == "Definitions & Sources":
    st.markdown("""
    <div class="hero">
        <div><div class="hero-title">Definitions & Sources</div>
            <div class="hero-sub">Methodology · Data sources · Known limitations</div></div>
        <div class="hero-pill">Transparency</div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><div class="card-t">KPI Definitions</div>', unsafe_allow_html=True)
        for k, v in {
            "Market Share %": "Provider discharges ÷ total market discharges × 100, within the same state and service line.",
            "Total Discharges": "Count of Medicare inpatient discharges for the provider, state, and service line.",
            "Market Rank": "Competitive rank by discharge volume. Rank 1 = highest volume in that market segment.",
            "Avg Medicare Payment": "Average amount Medicare paid per discharge for the DRG group.",
            "Service Line": "Clinical grouping via CMS Major Diagnostic Category (MDC) codes.",
            "Health System": "Parent organization grouping via keyword matching on hospital names.",
            "CCN": "CMS Certification Number — universal hospital identifier and join key.",
            "DRG": "Diagnosis Related Group — Medicare procedure classification (500+ codes).",
            "MDC": "Major Diagnostic Category — CMS grouping of all DRGs into 25 organ-system buckets.",
        }.items():
            st.markdown(f"""
            <div class="row">
                <div><div class="row-name" style="font-size:0.88rem">{k}</div>
                    <div style="font-size:0.8rem;color:{T3};margin-top:2px">{v}</div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><div class="card-t">Data Sources</div>', unsafe_allow_html=True)
        for t, d in [
            ("CMS Medicare Inpatient by Provider & Service (2024)", "data.cms.gov · 145,879 rows · All IPPS hospitals · CCN, DRG, discharges, payments"),
            ("CMS Hospital General Information (2024)", "data.cms.gov/provider-data · 5,432 hospitals · CCN, name, city, state, type, rating"),
            ("CMS MS-DRG MDC Crosswalk FY2024", "NBER / CMS IPPS Final Rule · 766 DRGs → 25 MDCs · Official clinical grouping"),
            ("Health System Reference Table", "68 keyword mappings · Proof-of-concept · Production: Definitive Healthcare crosswalk"),
        ]:
            st.markdown(f"""
            <div class="row">
                <div class="icon icon-b">📄</div>
                <div><div class="row-name" style="font-size:0.85rem">{t}</div>
                    <div style="font-size:0.78rem;color:{T3};margin-top:2px">{d}</div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-t">Known Limitations</div>', unsafe_allow_html=True)
        for lim in [
            "Medicare FFS only — excludes Medicaid, commercial, Medicare Advantage",
            "Keyword matching for health systems — may miss recent M&A",
            "~35-40% of discharges classified as Independent / Other",
            "Single year snapshot — no longitudinal trends",
            "CMS suppresses DRGs with ≤10 discharges per provider",
        ]:
            st.markdown(f"""
            <div class="row">
                <div class="icon icon-r" style="font-size:0.85rem">⚠️</div>
                <div style="font-size:0.83rem;color:{T2}">{lim}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#1D4ED820;border:1px solid #1D4ED840;border-radius:12px;padding:1.2rem 1.4rem">
            <div style="font-size:0.65rem;color:#60A5FA;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Architecture</div>
            <div style="font-size:0.8rem;color:{T2};line-height:1.9">
                CMS Files → Snowflake RAW → CLEAN (3-way join) → ANALYTICS (market share view) → Streamlit<br>
                Built by BRG Summer Associate · June 2026 · Not for client distribution
            </div>
        </div>""", unsafe_allow_html=True)
