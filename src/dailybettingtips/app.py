import datetime as dt
from typing import Dict, Any, List

import streamlit as st

from dailybettingtips.scanner import FlashscoreScanner


def day_offset(selected: dt.date, today: dt.date) -> int:
    return (selected - today).days


def render_team(name: str, s: Dict[str, Any]) -> str:
    if not s:
        return f"**{name}** — no season data yet"
    text = f"**{name}** — avg **{s.get('avg_goals', 0):.2f}** goals/match"
    if int(s.get("matches", 0)) > 0:
        text += (
            f" ({int(s['matches'])} played, {int(s['goals_scored'])} scored, "
            f"{int(s['goals_conceded'])} conceded)"
        )
    return text


def render_recent(name: str, recent: List[Dict[str, Any]]) -> str:
    if not recent:
        return f"**{name}** — no recent matches available"
    cells = []
    for m in recent:
        n = m.get("goals_scored", 0)
        color = "green" if n > 0 else "red"
        cells.append(f"<span style='color:{color};font-weight:bold'>{n}</span>")
    return f"**{name}** · last {len(recent)} matches: {' '.join(cells)}"


@st.dialog("Match analysis")
def dialog(p: Dict[str, Any]) -> None:
    kick = dt.datetime.fromtimestamp(p["kickoff"])
    st.markdown(f"### {p['team_a']} vs {p['team_b']}")
    st.caption(f"{p['league']} · {kick.strftime('%A %d/%m %H:%M')} · kickoff {kick.strftime('%H:%M')}")

    st.markdown("#### Filter checklist")
    for name, passed, msg in p["reasons"]:
        with st.expander(f"{'✅' if passed else '❌'} {name}", expanded=not passed):
            st.write(msg)

    if p.get("team_stats"):
        st.markdown("#### Season stats")
        st.markdown(render_team(p["team_a"], p["team_stats"].get("a", {})))
        st.markdown(render_team(p["team_b"], p["team_stats"].get("b", {})))

    if p.get("recent_a") or p.get("recent_b"):
        st.markdown("#### Recent form (goals scored per match)")
        st.markdown(render_recent(p["team_a"], p["recent_a"]), unsafe_allow_html=True)
        st.markdown(render_recent(p["team_b"], p["recent_b"]), unsafe_allow_html=True)

    h2h = p.get("h2h_matches") or []
    st.markdown(f"#### Head-to-head — {len(h2h)} matches")
    if h2h:
        with st.expander("View H2H results"):
            for m in h2h[:20]:
                d = dt.datetime.fromtimestamp(m["kickoff"]).strftime("%d/%m/%Y")
                st.write(f"{d} · {m['team_a']} {m['home_goals']}–{m['away_goals']} {m['team_b']}")
    else:
        st.write("No H2H available.")

    all_odds = p.get("all_odds") or {}
    st.markdown("#### Bookmaker odds (Over 1.5)")
    if all_odds:
        for bm, od in sorted(all_odds.items()):
            marker = "🌟" if bm in (p.get("over15_odds") or {}) else "⚪"
            st.markdown(f"{marker} **{bm}**: {od:.2f}")
    else:
        st.write("No odds returned for this match.")


def card(p: Dict[str, Any], highlight: bool = False, section: str = "all") -> None:
    border = "#ffaa00" if highlight else None
    with st.container(border=True):
        st.markdown(f"### {p['team_a']} vs {p['team_b']}")
        kick = dt.datetime.fromtimestamp(p["kickoff"])
        st.caption(f"{p['league']} · {kick.strftime('%d/%m %H:%M')}")
        if p["qualified"]:
            st.markdown(f"✅ **Over 1.5 @ {p['best_odds']:.2f}**")
        else:
            failed = next((name for name, ok, _ in reversed(p["reasons"]) if not ok), "")
            st.markdown(f"❌ Filtered at **{failed}**")
        if st.button("Details", key=f"det_{section}_{p['id']}", use_container_width=True):
            dialog(p)


# ------------------------------------------------------------------- main UI
st.set_page_config(
    page_title="Daily Betting Tips - Over 1.5 Goals Strategy",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ Daily Betting Tips — Over 1.5 Goals Strategy")
st.caption(
    "Automated daily scanner. Strategy: Season goal average → Head-to-head → Recent form → "
    "Betclic.pt / Betano.pt odds ≥ 1.15."
)

with st.container(border=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        scan_date = st.date_input("📅 Pick a date to scan", value=dt.date.today())
    with c2:
        geo = st.selectbox("🌍 Bookmaker region", ["PT", "US", "BR", "EN"], index=0)
    with c3:
        st.markdown("####")
        go = st.button("🔍 Scan this date", type="primary", use_container_width=True)

# Persist scan results across reruns (clicks on "Details" buttons otherwise
# wipe the results, because a rerun re-executes the whole script).
if "packets" not in st.session_state:
    st.session_state.packets = None
if "scan_date" not in st.session_state:
    st.session_state.scan_date = None

if go:
    st.session_state.scan_date = scan_date
    st.session_state.geo = geo
    st.session_state.packets = None  # trigger fresh scan below

if st.session_state.packets is None and st.session_state.scan_date is not None:
    offset = day_offset(st.session_state.scan_date, dt.date.today())
    if st.session_state.scan_date < dt.date.today():
        st.warning("That date is in the past — bookmaker odds will not be historical.")

    holder = st.empty()
    bar = holder.progress(0.0)
    status = holder.caption("")

    def tick(a, msg):
        bar.progress(min(1.0, a))
        status.caption(f"**{msg}**")

    with st.spinner("Scanning matches…"):
        packets = FlashscoreScanner().scan(
            day_offset=offset,
            geo_ip_code=st.session_state.get("geo", geo),
            progress=tick,
        )
    holder.empty()
    st.session_state.packets = packets

if st.session_state.packets is not None:
    packets = st.session_state.packets

    quals = [p for p in packets if p["qualified"]]
    st.metric("Qualified bets", len(quals), delta=f"{len(packets)} matches scanned")

    if quals:
        st.markdown("## 🔥 Qualified bets")
        cols = st.columns(3)
        for i, p in enumerate(quals):
            with cols[i % 3]:
                card(p, highlight=True, section="qualified")
    else:
        st.info("No match passed all 4 filters. Per strategy: **don't bet** today.")

    qual_ids = {p["id"] for p in quals}
    remaining = [p for p in packets if p["id"] not in qual_ids]
    st.markdown("## 📋 All matches")
    cols = st.columns(3)
    for i, p in enumerate(remaining):
        with cols[i % 3]:
            card(p, section="all")