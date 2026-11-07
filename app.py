import csv
import html
import io
from datetime import datetime, timedelta
import streamlit as st
from PIL import Image, ImageOps

from database.db import init_db
from core.authentication import create_user, authenticate, list_voters, set_voter_eligibility
from core.voting import (
    create_election, get_elections, get_election, cast_vote,
    close_election, has_voted, election_ballots, election_state, voting_window_open,
    update_election_schedule, get_pending_ballots, reconcile_pending_ballot,
)
from core.tally import tally_election
from core.blockchain import chain_ballot_count, transaction_details, verify_ballot_receipt
from core.candidate_profiles import (
    init_candidate_profiles, get_candidate_profile, save_candidate_profile,
    get_election_details, save_election_details,
)

st.set_page_config(
    page_title="VoteChain | Campus Elections",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Design system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
  --vc-ink:#17233b; --vc-muted:#71809a; --vc-blue:#315efb;
  --vc-blue2:#2349d8; --vc-bg:#f4f7fc; --vc-line:#e5eaf3;
  --vc-green:#138a63; --vc-navy:#101b33;
}
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:var(--vc-bg); color:var(--vc-ink);}
[data-testid="stHeader"] {background:rgba(244,247,252,.88);}
.block-container {max-width:1320px; padding-top:1.7rem; padding-bottom:3rem;}
h1,h2,h3,h4 {font-family:'Manrope',sans-serif!important; color:var(--vc-ink);}
h1 {font-weight:800!important; letter-spacing:-.045em;}
h2,h3 {font-weight:750!important; letter-spacing:-.025em;}
p, label, [data-testid="stMarkdownContainer"] {color:var(--vc-ink);}
[data-testid="stSidebar"] {background:#101b33; border-right:1px solid #1d2b49;}
[data-testid="stSidebar"] * {color:#e9efff!important;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#b7c4df!important;}
[data-testid="stSidebar"] .stRadio label {padding:8px 10px; border-radius:9px;}
[data-testid="stSidebar"] [data-testid="stRadio"] > div {gap:5px;}
.stButton > button, .stFormSubmitButton > button {
  border-radius:10px; border:0; background:var(--vc-blue); color:white;
  font-weight:700; min-height:2.7rem; padding:.55rem 1.1rem;
  box-shadow:0 5px 14px rgba(49,94,251,.16);
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background:var(--vc-blue2); color:white; border:0;
}
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
  border-radius:10px!important; background:white;
}
div[data-testid="stMetric"] {
  background:white; border:1px solid var(--vc-line); padding:17px 18px;
  border-radius:15px; box-shadow:0 3px 12px rgba(23,35,59,.035);
}
div[data-testid="stMetricLabel"] {color:var(--vc-muted)!important;font-weight:600;}
div[data-testid="stMetricValue"] {color:var(--vc-ink)!important;font-family:'Manrope',sans-serif;}
div[data-testid="stTabs"] button {font-weight:700;}
.vc-brand {display:flex;align-items:center;gap:12px;margin:2px 0 24px;}
.vc-logo {width:43px;height:43px;border-radius:13px;background:linear-gradient(135deg,#4e7bff,#2349d8);
display:flex;align-items:center;justify-content:center;color:white;font-size:23px;box-shadow:0 8px 18px #315efb40;}
.vc-brand-name {font-family:'Manrope',sans-serif;font-weight:800;font-size:21px;letter-spacing:-.7px;color:#fff;}
.vc-brand-sub {font-size:10px;letter-spacing:1.4px;color:#9eafd0;text-transform:uppercase;}
.vc-hero {background:linear-gradient(115deg,#142443 0%,#203d75 65%,#315efb 100%);
color:white;padding:28px 30px;border-radius:20px;margin:4px 0 22px;position:relative;overflow:hidden;}
.vc-hero:after {content:"";position:absolute;width:230px;height:230px;border:1px solid #ffffff24;border-radius:50%;right:-35px;top:-95px;box-shadow:0 0 0 25px #ffffff09,0 0 0 55px #ffffff06;}
.vc-hero h1 {color:white!important;font-size:30px!important;margin:0 0 7px!important;}
.vc-hero p {color:#dce6ff!important;margin:0;max-width:700px;}
.vc-eyebrow {font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:#b9ccff;font-weight:700;margin-bottom:10px;}
.vc-card {background:white;border:1px solid var(--vc-line);border-radius:16px;padding:19px 20px;box-shadow:0 4px 16px rgba(23,35,59,.035);margin-bottom:12px;}
.vc-card-title {font-family:'Manrope',sans-serif;font-weight:800;font-size:17px;color:var(--vc-ink);margin-bottom:5px;}
.vc-muted {color:var(--vc-muted);font-size:13px;}
.vc-pill {display:inline-block;border-radius:100px;padding:5px 10px;font-size:11px;font-weight:800;letter-spacing:.4px;background:#eaf8f2;color:#138a63;}
.vc-pill.closed {background:#eef1f6;color:#69758a;}
.vc-candidate {background:white;border:1px solid var(--vc-line);border-radius:15px;padding:16px;height:100%;margin-bottom:10px;}
.vc-avatar {width:42px;height:42px;border-radius:13px;background:#eaf0ff;color:#315efb;font-weight:800;display:flex;align-items:center;justify-content:center;margin-bottom:12px;}
.vc-section {font-family:'Manrope',sans-serif;font-weight:800;font-size:19px;margin:18px 0 10px;}
.vc-footer {border-top:1px solid var(--vc-line);padding-top:15px;margin-top:28px;color:#8793a8;font-size:12px;}
div[data-testid="stAlert"] {border-radius:12px;}
@media(max-width:700px){.block-container{padding:1rem 1rem 2rem}.vc-hero{padding:22px}.vc-hero h1{font-size:24px!important;}}
</style>
""", unsafe_allow_html=True)


def brand():
    st.markdown("""
    <div class="vc-brand">
      <div class="vc-logo">✓</div>
      <div><div class="vc-brand-name">VoteChain</div>
      <div class="vc-brand-sub">Campus election platform</div></div>
    </div>""", unsafe_allow_html=True)


def hero(kicker, title, subtitle):
    st.markdown(
        f'<section class="vc-hero"><div class="vc-eyebrow">{html.escape(kicker)}</div>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></section>',
        unsafe_allow_html=True,
    )


def section(title, caption=None):
    st.markdown(f'<div class="vc-section">{html.escape(title)}</div>', unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def card(title, description="", badge=None, badge_class=""):
    badge_html = f'<span class="vc-pill {badge_class}">{html.escape(badge)}</span>' if badge else ""
    st.markdown(
        f'<div class="vc-card">{badge_html}<div class="vc-card-title">{html.escape(title)}</div>'
        f'<div class="vc-muted">{html.escape(description)}</div></div>',
        unsafe_allow_html=True,
    )


def initials(name):
    bits = [part[0] for part in name.split() if part]
    return "".join(bits[:2]).upper() or "VC"


def display_candidate_photo(photo_path, width=110):
    """Display candidate photos as consistently sized square thumbnails."""
    try:
        with Image.open(photo_path) as image_file:
            image = ImageOps.fit(
                image_file.convert("RGB"),
                (320, 320),
                method=Image.Resampling.LANCZOS,
            )
        st.image(image, width=width)
    except (OSError, ValueError, TypeError):
        st.caption("Candidate photo unavailable.")


def election_label(election):
    return f"{election['title']} · {election_state(election)}"


def safe_error(exc, context):
    st.error(f"{context}: {exc}")


def render_public_verification():
    hero("PUBLIC BLOCKCHAIN CHECK", "Verify a ballot commitment", "Check that a transaction contains a confirmed VoteChain ballot event for the election and commitment you were given.")
    st.info("This verifies the transaction receipt and emitted on-chain commitment. It does not reveal the selected candidate or prove voter eligibility.")
    with st.form("public_commitment_verification"):
        public_election_id = st.text_input("Election ID", placeholder="e.g. DBIT-2026-DEMO")
        public_tx_hash = st.text_input("Blockchain transaction hash", placeholder="0x…")
        public_commitment = st.text_input("SHA-256 ballot commitment", placeholder="64 hexadecimal characters")
        verify_public = st.form_submit_button("Verify on blockchain", use_container_width=True)
    if verify_public:
        try:
            result = verify_ballot_receipt(public_election_id.strip(), public_tx_hash.strip(), public_commitment.strip())
            if result["verified"]:
                st.success("Verified: a confirmed VoteChain ballot event with this election ID and commitment exists on-chain.")
                c1, c2 = st.columns(2)
                c1.metric("Block number", result["block_number"])
                c2.metric("Confirmation", result["status"])
                st.code(result["transaction_hash"])
            else:
                st.error(result["reason"])
        except Exception as exc:
            safe_error(exc, "Verification could not be completed")


# ---------- Application bootstrap ----------
try:
    init_db()
    init_candidate_profiles()
except Exception as exc:
    st.error(f"VoteChain could not initialize its local database: {exc}")
    st.stop()

if "user" not in st.session_state:
    st.session_state.user = None
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

# ---------- Authentication screen ----------
if not st.session_state.user:
    left, right = st.columns([1.08, 0.92], gap="large")
    with left:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
        brand()
        hero(
            "A better way to run campus elections",
            "Your voice. Your vote. Verified.",
            "A simple, transparent election experience for student communities — with encrypted ballots and a tamper-evident audit trail.",
        )
        section("Built for campus communities")
        c1, c2 = st.columns(2)
        with c1:
            card("Private ballot", "Ballot selections are encrypted before being stored.")
        with c2:
            card("Verifiable record", "A commitment and transaction reference are recorded on the local blockchain.")
        st.markdown("<div class='vc-footer'>LOCAL DEMONSTRATION PROTOTYPE · NOT CERTIFIED FOR REAL-WORLD ELECTIONS</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div style='height:7vh'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Welcome back")
            st.caption("Sign in to your campus election workspace.")
            login_tab, register_tab, verify_tab = st.tabs(["Sign in", "Create account", "Public verification"])
            with login_tab:
                with st.form("login_form"):
                    uid = st.text_input("Voter ID", placeholder="e.g. voter1")
                    pwd = st.text_input("Password", type="password", placeholder="Enter your password")
                    submitted = st.form_submit_button("Sign in to VoteChain", use_container_width=True)
                if submitted:
                    user = authenticate(uid, pwd)
                    if user and user.get("pending_approval"):
                        st.warning("Your account is registered but is awaiting administrator eligibility approval.")
                    elif user:
                        st.session_state.user = user
                        st.session_state.login_error = ""
                        st.rerun()
                    else:
                        st.error("We couldn't verify those credentials. Check your voter ID and password.")
                st.markdown("<div class='vc-muted'>Demo admin: admin · Demo voters: voter1–voter4</div>", unsafe_allow_html=True)
            with register_tab:
                st.caption("Demo registration is open to non-admin voters. Real deployments require an external eligibility authority.")
                with st.form("register_form"):
                    name = st.text_input("Full name", placeholder="Your name")
                    rid = st.text_input("Voter ID", placeholder="Your assigned voter ID")
                    rp = st.text_input("Create password", type="password", help="Use at least 8 characters.")
                    register = st.form_submit_button("Create voter account", use_container_width=True)
                if register:
                    try:
                        create_user(rid, name, rp, False, eligible=False)
                        st.success("Account created. It will become active after administrator eligibility approval.")
                    except Exception as exc:
                        safe_error(exc, "Registration failed")
            with verify_tab:
                render_public_verification()
    st.stop()

# ---------- Signed-in shell ----------
user = st.session_state.user
is_admin = bool(user.get("is_admin"))
with st.sidebar:
    brand()
    st.markdown("---")
    st.caption("SIGNED IN AS")
    st.markdown(f"**{html.escape(user['display_name'])}**")
    st.caption("Administrator" if is_admin else "Student voter")
    st.markdown("---")
    if is_admin:
        page = st.radio("WORKSPACE", ["Overview", "Elections", "Voter eligibility", "Voter preview", "Audit & results", "Public verification"], label_visibility="visible")
    else:
        page = st.radio("CAMPUS PORTAL", ["My dashboard", "Cast your vote", "Verify participation", "Public verification"], label_visibility="visible")
    st.markdown("---")
    st.caption("LOCAL NETWORK · HARDHAT")
    try:
        # This checks connectivity without changing chain state.
        from core.blockchain import load_contract
        load_contract()
        st.markdown("🟢 Blockchain connected")
    except Exception:
        st.markdown("🟠 Blockchain unavailable")
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.markdown("<div class='vc-footer'>VoteChain v2.1 · Competition demo</div>", unsafe_allow_html=True)

elections = get_elections()
open_elections = [e for e in elections if election_state(e) == "OPEN"]
scheduled_elections = [e for e in elections if election_state(e) == "SCHEDULED"]
closed_elections = [e for e in elections if election_state(e) in ("CLOSED", "ENDED")]
unclosed_elections = [e for e in elections if e["status"] == "OPEN"]

# ---------- Admin workspace ----------
if is_admin:
    if page == "Overview":
        hero("ADMINISTRATOR WORKSPACE", "Election command center", "Monitor campus elections, participation and verification from one place.")
        total_ballots = 0
        chain_total = 0
        chain_ok = True
        for election in elections:
            try:
                total_ballots += len(election_ballots(election["election_id"]))
                chain_total += chain_ballot_count(election["election_id"])
            except Exception:
                chain_ok = False
        a, b, c, d = st.columns(4)
        a.metric("Total elections", len(elections))
        b.metric("Open elections", len(open_elections))
        c.metric("Ballots recorded", total_ballots)
        d.metric("Registered voters", len(list_voters()))
        section("Election activity", "A quick view of the current campus election cycle.")
        if elections:
            for election in elections:
                ballots = len(election_ballots(election["election_id"]))
                pill = "OPEN" if election["status"] == "OPEN" else "CLOSED"
                pill_class = "" if pill == "OPEN" else "closed"
                st.markdown(
                    f'<div class="vc-card"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap">'
                    f'<div><div class="vc-card-title">{html.escape(election["title"])}</div>'
                    f'<div class="vc-muted">{html.escape(election["election_id"])} · {len(election["candidates"])} candidates · {ballots} ballots</div></div>'
                    f'<span class="vc-pill {pill_class}">{pill}</span></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No elections yet. Create your first campus election from the Elections page.")
        if chain_ok:
            st.caption(f"Local chain reports {chain_total} ballot transactions across the listed elections.")
        else:
            st.warning("Some blockchain counts could not be loaded. Check that the Hardhat node is running.")

    elif page == "Elections":
        hero("ELECTION MANAGEMENT", "Manage campus elections", "Create an election, review its setup and close it when voting ends.")
        create_col, close_col = st.columns([1.1, .9], gap="large")
        with create_col:
            with st.container(border=True):
                st.subheader("Create a new election")
                with st.form("create_election_form"):
                    eid = st.text_input("Election ID", placeholder="e.g. DBIT-COUNCIL-2026")
                    title = st.text_input("Election title", placeholder="e.g. Student Council Election")
                    position_title = st.text_input("Position / election type", placeholder="e.g. Student Council President")
                    election_description = st.text_area("Election description", placeholder="Explain the purpose and scope of this election...", height=85)
                    schedule_start_default = datetime.now().replace(second=0, microsecond=0)
                    schedule_end_default = schedule_start_default + timedelta(days=7)
                    schedule_start = st.datetime_input("Voting starts", value=schedule_start_default, help="Uses this computer's local time zone.")
                    schedule_end = st.datetime_input("Voting ends", value=schedule_end_default, help="Voting is automatically blocked at or after this time.")
                    candidate_text = st.text_area("Candidates", placeholder="Enter one candidate name per line", height=150)
                    create = st.form_submit_button("Create election", use_container_width=True)
                if create:
                    try:
                        create_election(eid, title, candidate_text.splitlines(), schedule_start, schedule_end)
                        save_election_details(eid, position_title, election_description)
                        st.success("Election created and initialized on the local blockchain.")
                        st.rerun()
                    except Exception as exc:
                        safe_error(exc, "Could not create election")
        with close_col:
            with st.container(border=True):
                st.subheader("Close an election")
                if unclosed_elections:
                    selected_close_id = st.selectbox("Select election to close", [e["election_id"] for e in unclosed_elections], format_func=lambda eid: election_label(next(e for e in unclosed_elections if e["election_id"] == eid)))
                    selected_close = next(e for e in unclosed_elections if e["election_id"] == selected_close_id)
                    st.warning("Closing an election prevents further ballot submissions.")
                    if st.button("Close selected election", use_container_width=True):
                        try:
                            close_election(selected_close["election_id"])
                            st.success("Election closed.")
                            st.rerun()
                        except Exception as exc:
                            safe_error(exc, "Could not close election")
                else:
                    st.info("There are no open elections.")
        section("All elections")
        if elections:
            for e in elections:
                state = election_state(e)
                schedule_text = f"Starts: {e.get('start_at') or 'Immediately'} · Ends: {e.get('end_at') or 'No end time'}"
                card(e["title"], f"{e['election_id']} · {len(e['candidates'])} candidates · {len(election_ballots(e['election_id']))} ballots · {schedule_text}", state, "" if state == "OPEN" else "closed")
        else:
            st.info("No elections have been created.")

        # Election details can be edited without changing the ballot candidate order.
        if elections:
            section("Edit election information", "Update the public description and position. Candidate names are locked after creation to protect ballot indexing.")
            edit_election_id = st.selectbox("Election to edit", [e["election_id"] for e in elections], key="edit_election_details_selector")
            current_details = get_election_details(edit_election_id)
            with st.form("edit_election_details_form"):
                edit_position = st.text_input("Position / election type", value=current_details["position_title"])
                edit_description = st.text_area("Election description", value=current_details["description"], height=90)
                save_details = st.form_submit_button("Save election information")
            if save_details:
                try:
                    save_election_details(edit_election_id, edit_position, edit_description)
                    st.success("Election information updated.")
                    st.rerun()
                except Exception as exc:
                    safe_error(exc, "Could not update election information")

            selected_schedule = next(e for e in elections if e["election_id"] == edit_election_id)
            section("Election schedule", "Schedule can only be changed before any ballot is recorded.")
            schedule_start_value = datetime.fromisoformat(selected_schedule["start_at"]) if selected_schedule.get("start_at") else datetime.now().replace(second=0, microsecond=0)
            schedule_end_value = datetime.fromisoformat(selected_schedule["end_at"]) if selected_schedule.get("end_at") else schedule_start_value + timedelta(days=7)
            with st.form("edit_election_schedule_form"):
                new_schedule_start = st.datetime_input("Voting starts", value=schedule_start_value, key=f"edit_schedule_start_{edit_election_id}")
                new_schedule_end = st.datetime_input("Voting ends", value=schedule_end_value, key=f"edit_schedule_end_{edit_election_id}")
                save_schedule = st.form_submit_button("Save election schedule")
            if save_schedule:
                try:
                    update_election_schedule(edit_election_id, new_schedule_start, new_schedule_end)
                    st.success("Election schedule updated.")
                    st.rerun()
                except Exception as exc:
                    safe_error(exc, "Could not update schedule")

            section("Candidate profile management", "Add a photo, position, department, year, manifesto and campaign promises for each candidate.")
            profile_election_id = st.selectbox("Election", [e["election_id"] for e in elections], key="profile_election_selector")
            profile_election = next(e for e in elections if e["election_id"] == profile_election_id)
            selected_candidate = st.selectbox("Candidate", profile_election["candidates"], key="profile_candidate_selector")
            existing = get_candidate_profile(profile_election_id, selected_candidate)
            if existing.get("photo_path"):
                st.caption("Current candidate photo")
                display_candidate_photo(existing["photo_path"], width=110)
            with st.form("candidate_profile_form"):
                profile_position = st.text_input("Candidate position", value=existing["position"], placeholder="e.g. Student Council President")
                profile_department = st.text_input("Department", value=existing["department"], placeholder="e.g. Computer Science")
                profile_year = st.text_input("Academic year", value=existing["academic_year"], placeholder="e.g. 3rd Year")
                profile_manifesto = st.text_area("Manifesto", value=existing["manifesto"], height=120, placeholder="Candidate's vision and priorities...")
                profile_promises = st.text_area("Campaign promises (one per line)", value=existing["promises"], height=100, placeholder="Improve student facilities\nIncrease technical events\nStrengthen student feedback")
                profile_photo = st.file_uploader("Candidate photo (PNG/JPG/WEBP, max 5 MB)", type=["png", "jpg", "jpeg", "webp"])
                save_profile = st.form_submit_button("Save candidate profile", use_container_width=True)
            if save_profile:
                try:
                    save_candidate_profile(
                        profile_election_id, selected_candidate,
                        profile_position, profile_department, profile_year,
                        profile_manifesto, profile_promises,
                        profile_photo.getvalue() if profile_photo else None,
                        ("." + profile_photo.name.rsplit(".", 1)[-1].lower()) if profile_photo else None,
                    )
                    st.success(f"Profile saved for {selected_candidate}.")
                    st.rerun()
                except Exception as exc:
                    safe_error(exc, "Could not save candidate profile")

    elif page == "Voter eligibility":
        hero("ACCESS CONTROL", "Voter eligibility", "Review new registrations and approve or suspend voter accounts before they can submit a ballot.")
        voters = list_voters()
        pending_voters = [v for v in voters if not v["is_admin"] and not v["is_eligible"]]
        eligible_voters = [v for v in voters if not v["is_admin"] and v["is_eligible"]]
        x1, x2, x3 = st.columns(3)
        x1.metric("Registered accounts", len([v for v in voters if not v["is_admin"]]))
        x2.metric("Awaiting approval", len(pending_voters))
        x3.metric("Eligible voters", len(eligible_voters))
        section("Manage voter access", "New self-registered accounts are pending until an administrator approves them.")
        if voters:
            for voter in voters:
                if voter["is_admin"]:
                    continue
                with st.container(border=True):
                    vc1, vc2, vc3 = st.columns([2, 1, 1])
                    vc1.markdown(f"**{html.escape(voter['display_name'])}**")
                    vc1.caption(voter["voter_id"])
                    vc2.markdown("<span class='vc-pill'>ELIGIBLE</span>" if voter["is_eligible"] else "<span class='vc-pill closed'>PENDING</span>", unsafe_allow_html=True)
                    if voter["is_eligible"]:
                        action_label = "Suspend voter"
                        new_value = False
                    else:
                        action_label = "Approve voter"
                        new_value = True
                    if vc3.button(action_label, key=f"eligibility_{voter['voter_id']}", use_container_width=True):
                        try:
                            set_voter_eligibility(voter["voter_id"], new_value)
                            st.success(f"Eligibility updated for {voter['voter_id']}.")
                            st.rerun()
                        except Exception as exc:
                            safe_error(exc, "Could not update voter eligibility")
        else:
            st.info("No voter accounts have been registered yet.")

    elif page == "Public verification":
        render_public_verification()

    elif page == "Voter preview":
        hero("VOTER EXPERIENCE", "Preview the ballot", "Review the student-facing election flow using the signed-in demo account.")
        if not elections:
            st.info("Create an election before previewing the voter experience.")
        else:
            chosen_id = st.selectbox("Choose an election", [e["election_id"] for e in elections], format_func=lambda eid: election_label(next(e for e in elections if e["election_id"] == eid)))
            chosen = next(e for e in elections if e["election_id"] == chosen_id)
            if not voting_window_open(chosen):
                st.warning(f"Voting is not available. Current election state: {election_state(chosen)}.")
            elif has_voted(chosen["election_id"], user["voter_id"]):
                st.success("This account has already used its voting authorization for this election.")
            else:
                st.caption("Select one candidate. Your selection is encrypted before it is submitted.")
                selected = st.radio("Your candidate", chosen["candidates"], format_func=lambda x: x, horizontal=False)
                cols = st.columns(3)
                for i, candidate in enumerate(chosen["candidates"]):
                    with cols[i % 3]:
                        st.markdown(f'<div class="vc-candidate"><div class="vc-avatar">{html.escape(initials(candidate))}</div><b>{html.escape(candidate)}</b><div class="vc-muted">Candidate for student representation</div></div>', unsafe_allow_html=True)
                with st.form("admin_preview_vote"):
                    confirm = st.checkbox("I have reviewed my selection.")
                    submit = st.form_submit_button("Encrypt and submit ballot", use_container_width=True)
                if submit:
                    if not confirm:
                        st.warning("Please confirm that you reviewed your selection.")
                    else:
                        try:
                            result = cast_vote(chosen["election_id"], user["voter_id"], chosen["candidates"].index(selected))
                            st.success("Ballot submitted. The transaction was confirmed by the local blockchain.")
                            st.code(result["tx_hash"])
                            st.caption("Transaction hash · Keep this reference for the demo.")
                            try:
                                details = transaction_details(result["tx_hash"])
                                tx1, tx2, tx3 = st.columns(3)
                                tx1.metric("Block number", details["block_number"])
                                tx2.metric("Confirmation", details["status"])
                                tx3.metric("Gas used", details["gas_used"])
                            except Exception as detail_exc:
                                st.caption(f"Transaction metadata could not be loaded: {detail_exc}")
                        except Exception as exc:
                            safe_error(exc, "Ballot submission failed")

    elif page == "Audit & results":
        hero("TRANSPARENCY CENTER", "Audit & results", "Compare locally stored ballots with the on-chain ledger and verify the encrypted tally.")
        if not elections:
            st.info("There are no elections to audit.")
        else:
            selected_id = st.selectbox("Election to inspect", [e["election_id"] for e in elections], format_func=lambda eid: election_label(next(e for e in elections if e["election_id"] == eid)))
            selected = next(e for e in elections if e["election_id"] == selected_id)
            ballots = election_ballots(selected["election_id"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Local ballot records", len(ballots))
            try:
                on_chain = chain_ballot_count(selected["election_id"])
                m2.metric("On-chain ballot count", on_chain)
                m3.metric("Count comparison", "MATCH" if on_chain == len(ballots) else "REVIEW")
                if on_chain == len(ballots):
                    st.success("Local and on-chain ballot counts match. This is a count comparison, not a complete end-to-end election proof.")
                else:
                    st.warning("The local and on-chain counts differ. Investigate before tallying.")
            except Exception as exc:
                st.warning(f"Blockchain unavailable: {exc}")
            section("Ballot audit trail")
            if ballots:
                audit_buffer = io.StringIO()
                writer = csv.DictWriter(audit_buffer, fieldnames=["election_id", "created_at", "commitment", "tx_hash"])
                writer.writeheader()
                for ballot in ballots:
                    writer.writerow({"election_id": selected["election_id"], "created_at": ballot.get("created_at", ""), "commitment": ballot["commitment"], "tx_hash": ballot["tx_hash"] or ""})
                st.download_button("Download audit CSV", audit_buffer.getvalue(), file_name=f"{selected['election_id']}_audit.csv", mime="text/csv", use_container_width=False)
                for i, ballot in enumerate(ballots, 1):
                    with st.expander(f"Ballot record {i} · {ballot['tx_hash'][:14] if ballot['tx_hash'] else 'No transaction'}…"):
                        st.caption(f"Recorded locally · {ballot.get('created_at', 'Timestamp unavailable')}")
                        st.caption("SHA-256 commitment")
                        st.code(ballot["commitment"])
                        st.caption("Blockchain transaction")
                        st.code(ballot["tx_hash"] or "Unavailable")
                        if ballot["tx_hash"]:
                            try:
                                details = transaction_details(ballot["tx_hash"])
                                d1, d2, d3 = st.columns(3)
                                d1.metric("Block", details["block_number"])
                                d2.metric("Status", details["status"])
                                d3.metric("Gas used", details["gas_used"])
                            except Exception as detail_exc:
                                st.caption(f"Transaction details unavailable: {detail_exc}")
            else:
                st.info("No ballots have been submitted for this election.")
            section("Pending transaction reconciliation", "Recover blockchain-confirmed ballots whose local database finalization was interrupted.")
            pending_rows = [p for p in get_pending_ballots() if p["election_id"] == selected["election_id"]]
            if pending_rows:
                for pending in pending_rows:
                    with st.container(border=True):
                        st.markdown(f"**Pending record #{pending['pending_id']} · {pending['status']}**")
                        st.caption(f"Voter account: {pending['voter_id']} · Created: {pending['created_at']}")
                        st.code(pending["tx_hash"] or "No transaction hash recorded")
                        if pending["error_message"]:
                            st.caption(pending["error_message"])
                        if st.button("Reconcile this transaction", key=f"reconcile_{pending['pending_id']}"):
                            try:
                                result = reconcile_pending_ballot(pending["pending_id"])
                                if result["status"] == "CONFIRMED":
                                    st.success(result["message"])
                                elif result["status"] == "WAITING":
                                    st.warning(result["message"])
                                else:
                                    st.error(result["message"])
                                st.rerun()
                            except Exception as exc:
                                safe_error(exc, "Reconciliation failed")
            else:
                st.success("No pending ballot transactions require reconciliation.")

            section("Encrypted tally")
            if selected["status"] != "CLOSED":
                st.info("Close the election before calculating results.")
            elif st.button("Verify commitments and calculate results", use_container_width=True):
                try:
                    result = tally_election(selected["election_id"])
                    st.success("Stored ballot commitments verified and encrypted aggregate tallied.")
                    st.metric("Ballots included", result["ballot_count"])
                    st.bar_chart(result["totals"])
                    st.dataframe([{"Candidate": k, "Votes": v} for k, v in result["totals"].items()], use_container_width=True, hide_index=True)
                except Exception as exc:
                    safe_error(exc, "Tally verification failed")

# ---------- Voter workspace ----------
else:
    if page == "My dashboard":
        hero("STUDENT VOTER PORTAL", f"Welcome, {user['display_name']}", "Your campus election hub. Review open elections and keep track of your participation.")
        v1, v2, v3 = st.columns(3)
        v1.metric("Open elections", len(open_elections))
        v2.metric("Ended / closed elections", len(closed_elections))
        participated = sum(1 for e in elections if has_voted(e["election_id"], user["voter_id"]))
        v3.metric("Your participation", f"{participated}/{len(elections)}")
        section("Elections available to you")
        if elections:
            for e in elections:
                voted = has_voted(e["election_id"], user["voter_id"])
                status = "VOTED" if voted else election_state(e)
                cls = "closed" if status == "CLOSED" else ""
                st.markdown(
                    f'<div class="vc-card"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">'
                    f'<div><div class="vc-card-title">{html.escape(e["title"])}</div>'
                    f'<div class="vc-muted">{html.escape(e["election_id"])} · {len(e["candidates"])} candidates</div></div>'
                    f'<span class="vc-pill {cls}">{status}</span></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("There are no elections available yet. Check back later.")

    elif page == "Cast your vote":
        hero("SECURE BALLOT", "Make your voice count", "Choose one candidate, review your selection and submit your encrypted ballot.")
        if not elections:
            st.info("No elections are currently available.")
        else:
            chosen_id = st.selectbox("Select election", [e["election_id"] for e in elections], format_func=lambda eid: election_label(next(e for e in elections if e["election_id"] == eid)))
            chosen = next(e for e in elections if e["election_id"] == chosen_id)
            if not voting_window_open(chosen):
                st.warning(f"Voting is not available. Current election state: {election_state(chosen)}. Check the published start and end times.")
            elif has_voted(chosen["election_id"], user["voter_id"]):
                st.success("Your voting authorization has already been used for this election.")
                st.caption("Your selected candidate is not displayed or stored in your voter participation view.")
            else:
                election_info = get_election_details(chosen["election_id"])
                if election_info["position_title"]:
                    st.caption(f"Position: {election_info['position_title']}")
                if election_info["description"]:
                    st.write(election_info["description"])
                section("Meet the candidates", f"{len(chosen['candidates'])} candidates · Review their profiles before selecting one.")
                candidate_cols = st.columns(min(3, len(chosen["candidates"])))
                for i, candidate in enumerate(chosen["candidates"]):
                    profile = get_candidate_profile(chosen["election_id"], candidate)
                    with candidate_cols[i % len(candidate_cols)]:
                        with st.container(border=True):
                            if profile.get("photo_path"):
                                display_candidate_photo(profile["photo_path"], width=110)
                            else:
                                st.markdown(
                                    f'<div class="vc-avatar">{html.escape(initials(candidate))}</div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown(f"### {html.escape(candidate)}")
                            if profile["position"]:
                                st.caption(profile["position"])
                            meta = " · ".join(x for x in [profile["department"], profile["academic_year"]] if x)
                            if meta:
                                st.caption(meta)
                            st.markdown("**Manifesto**")
                            st.write(profile["manifesto"] or "Candidate manifesto has not been added yet.")
                            if profile["promises"]:
                                st.markdown("**Campaign promises**")
                                for promise in profile["promises"].splitlines():
                                    if promise.strip():
                                        st.markdown(f"- {promise.strip()}")
                with st.form("cast_vote_form"):
                    selected_candidate = st.radio("Select your candidate", chosen["candidates"])
                    st.markdown("---")
                    st.caption("Your ballot will be encrypted and a commitment will be recorded on the local blockchain.")
                    reviewed = st.checkbox("I have reviewed my selection and wish to submit this ballot.")
                    submit_vote = st.form_submit_button("Submit encrypted ballot", use_container_width=True)
                if submit_vote:
                    if not reviewed:
                        st.warning("Please confirm your selection before submitting.")
                    else:
                        try:
                            result = cast_vote(chosen["election_id"], user["voter_id"], chosen["candidates"].index(selected_candidate))
                            st.success("Your ballot was submitted and the blockchain transaction was confirmed.")
                            st.markdown("**Your verification references**")
                            st.caption("Ballot commitment")
                            st.code(result["commitment"])
                            st.caption("Transaction hash")
                            st.code(result["tx_hash"])
                            try:
                                details = transaction_details(result["tx_hash"])
                                x1, x2, x3 = st.columns(3)
                                x1.metric("Block number", details["block_number"])
                                x2.metric("Status", details["status"])
                                x3.metric("Gas used", details["gas_used"])
                            except Exception as detail_exc:
                                st.caption(f"Transaction metadata is temporarily unavailable: {detail_exc}")
                            st.info("Keep these references for the demonstration. They do not reveal your selected candidate.")
                        except Exception as exc:
                            safe_error(exc, "Could not submit your ballot")

    elif page == "Public verification":
        render_public_verification()

    elif page == "Verify participation":
        hero("PARTICIPATION RECEIPT", "Verify your participation", "Check whether your voting authorization was used without exposing your candidate selection.")
        if not elections:
            st.info("No elections are available.")
        else:
            for e in elections:
                voted = has_voted(e["election_id"], user["voter_id"])
                with st.container(border=True):
                    st.markdown(f"**{e['title']}**")
                    st.caption(f"{e['election_id']} · {e['status']}")
                    if voted:
                        st.success("Participation recorded · Authorization used")
                    else:
                        st.info("No participation record for this account yet.")

st.markdown("<div class='vc-footer'>VoteChain is an educational institutional-election prototype. It is not certified for public elections. Blockchain count matching and commitment checks are useful demo controls, not a guarantee of election security or voter anonymity.</div>", unsafe_allow_html=True)
