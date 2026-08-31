import pandas as pd
import streamlit as st
from practice_home_dashboard import render_practice_home
from strategic_planning import render_strategic_planning_center
from shared_identity import active_directory, verify_pin
from collaboration_governance import render_collaboration_center, render_clinical_intelligence, render_initiatives_page, render_decisions_page, render_growth_page, render_pin_admin
from call_schedule import ensure_store, render_editor, render_readonly

from team_backend import TeamStore

st.set_page_config(page_title="Practice Command Center", page_icon="❤️", layout="wide")

STATUSES = [
    "Discovery", "Planned", "In progress", "Blocked",
    "On Hold", "Backlog", "Complete", "Cancelled",
]
MONTHS = [
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
]


def users():
    roster = []
    for row in st.secrets.get("TEAM_USERS", []):
        try:
            pin = int(row.get("pin", 0))
        except (TypeError, ValueError):
            continue
        if 1 <= pin <= 100:
            roster.append(
                {
                    "name": str(row.get("name", "")).strip(),
                    "email": str(row.get("email", "")).strip().casefold(),
                    "pin": str(pin),
                    "admin": bool(row.get("admin", False)),
                }
            )
    return roster


def sign_in():
    if st.session_state.get("practice_user"):
        return st.session_state.practice_user
    roster = users()
    if not roster:
        st.error("TEAM_USERS is missing or contains no PINs from 1 through 100.")
        st.stop()
    st.title("Practice Command Center Sign In")
    name = st.selectbox("Team member", [person["name"] for person in roster])
    pin = st.text_input("PIN number (1-100)", type="password")
    if st.button("Sign in", type="primary"):
        match = next(person for person in roster if person["name"] == name)
        if pin.strip() == match["pin"]:
            st.session_state.practice_user = {
                key: match[key] for key in ["name", "email", "admin"]
            }
            st.rerun()
        st.error("The selected user and PIN did not match.")
    st.caption("Do not place PHI or patient identifiers in this app.")
    st.stop()


def owner_emails(item):
    values = item.get("owner_emails", [])
    if isinstance(values, str):
        values = [value.strip() for value in values.split(",") if value.strip()]
    if not values and item.get("owner_email"):
        values = [item["owner_email"]]
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def render_initiative(item, user, store, roster):
    archived = "ARCHIVED | " if item.get("archived") else ""
    with st.expander(
        f"{archived}{item.get('id', '')} | "
        f"{item.get('name', 'Untitled')} | {item.get('progress', 0)}%"
    ):
        names = item.get("owners") or ([item.get("owner")] if item.get("owner") else [])
        st.caption(
            f"Owners: {', '.join(str(name) for name in names) or 'Unassigned'} | "
            f"{item.get('status', '')} | {item.get('priority', '')}"
        )
        editable = user["admin"] or user["email"] in owner_emails(item)

        if user["admin"]:
            options = {person["email"]: person["name"] for person in roster}
            selected = st.multiselect(
                "Assigned owners",
                list(options),
                default=[email for email in owner_emails(item) if email in options],
                format_func=lambda email: options[email],
                key=f"owners_{item.get('id')}",
            )
            if st.button("Save owners", key=f"save_owners_{item.get('id')}"):
                store.update_initiative(
                    item.get("id"),
                    {
                        "owner_emails": selected,
                        "owners": [options[email] for email in selected],
                    },
                    user,
                )
                st.rerun()

        actions = item.get("next_actions") or (
            [item.get("next_action")] if item.get("next_action") else []
        )
        if editable:
            with st.form(f"edit_{item.get('id')}"):
                current_status = item.get("status") if item.get("status") in STATUSES else "Planned"
                status = st.selectbox(
                    "Status",
                    STATUSES,
                    index=STATUSES.index(current_status),
                )
                progress = st.slider("Progress", 0, 100, int(item.get("progress", 0)))
                next_actions = st.text_area(
                    "Next actions, one per line",
                    "\n".join(str(action).lstrip("⭐ ") for action in actions),
                )
                owner_update = st.text_area("Owner update", item.get("owner_update", ""))
                if st.form_submit_button("Save Initiative Update"):
                    action_list = [
                        f"⭐ {line.strip().lstrip('⭐* ').strip()}"
                        for line in next_actions.splitlines()
                        if line.strip()
                    ]
                    store.update_initiative(
                        item.get("id"),
                        {
                            "status": status,
                            "progress": progress,
                            "next_actions": action_list,
                            "next_action": action_list[0] if action_list else "",
                            "owner_update": owner_update.strip(),
                        },
                        user,
                    )
                    st.rerun()
        else:
            st.info("Only an assigned owner or administrator can edit. Everyone can comment.")

        st.markdown("**Comments**")
        for comment in item.get("comments", []):
            st.write(
                f"{comment.get('timestamp_utc', '')} | "
                f"**{comment.get('author_name', '')}**: {comment.get('comment', '')}"
            )
        with st.form(f"comment_{item.get('id')}"):
            text = st.text_area("Add a comment")
            if st.form_submit_button("Post Comment") and text.strip():
                store.add_comment(item.get("id"), text, user)
                st.rerun()
        with st.expander("History"):
            history = pd.DataFrame(item.get("history", []))
            if history.empty:
                st.write("No history yet.")
            else:
                st.dataframe(history, hide_index=True, use_container_width=True)


def practice_visible(item, default="Private"):
    return str(item.get("visibility", default)).strip().title() in ["Practice", "Shared"]


def visible_records(records, default="Private"):
    return [item for item in records if practice_visible(item, default)]


def add_annual_metrics(frame):
    if frame.empty:
        return frame
    result = frame.copy()
    for month in MONTHS:
        if month not in result.columns:
            result[month] = None
        result[month] = pd.to_numeric(result[month], errors="coerce")
    result["FY Total"] = result[MONTHS].sum(axis=1, min_count=1)
    result["Months Entered"] = result[MONTHS].notna().sum(axis=1)
    denominator = result["Months Entered"].astype("float64").where(lambda value: value > 0)
    result["Monthly Average"] = result["FY Total"].astype("float64").div(denominator).round(1)
    result["Projected FY RVUs"] = (result["Monthly Average"] * 12).round(0)
    return result


def add_yoy(frame, group=None):
    if frame.empty:
        return frame
    keys = ([group] if group else []) + ["Fiscal Year"]
    result = frame.sort_values(keys).copy()
    if group:
        result["Prior FY Total"] = result.groupby(group)["FY Total"].shift(1)
    else:
        result["Prior FY Total"] = result["FY Total"].shift(1)
    result["YoY Change"] = result["FY Total"] - result["Prior FY Total"]
    result["YoY %"] = ((result["FY Total"] / result["Prior FY Total"] - 1) * 100).round(1)
    return result


def practice_total_rows(rvu):
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))
    if physician.empty:
        return historical
    for month in MONTHS:
        if month not in physician.columns:
            physician[month] = None
        physician[month] = pd.to_numeric(physician[month], errors="coerce")
    calculated = physician.groupby("Fiscal Year", as_index=False)[MONTHS].sum(min_count=1)
    calculated["Source"] = "Calculated from physician entries"
    if historical.empty:
        return calculated
    historical["Source"] = "Imported historical total"
    calculated_years = set(calculated["Fiscal Year"].astype(str))
    historical = historical[~historical["Fiscal Year"].astype(str).isin(calculated_years)]
    return pd.concat([historical, calculated], ignore_index=True, sort=False)


service_account = dict(st.secrets["google_service_account"])
drive_settings = st.secrets["google_drive"]
store = TeamStore(service_account, str(drive_settings["folder_id"]), str(drive_settings["file_name"]))
raw_data = store.load()
extra = TeamStore.extras(raw_data)

def shared_users():
    directory = active_directory(extra)
    return directory if any(row.get("pin_hash") for row in directory) else users()

def shared_sign_in():
    if st.session_state.get("practice_user"):
        return st.session_state.practice_user
    roster = shared_users()
    st.title("Practice Command Center Sign In")
    name = st.selectbox("Team member", [person["name"] for person in roster])
    pin = st.text_input("PIN number (1-100)", type="password")
    if st.button("Sign in", type="primary"):
        match = next(person for person in roster if person["name"] == name)
        valid = verify_pin(name, pin, match.get("pin_hash")) if match.get("pin_hash") else pin.strip() == str(match.get("pin", ""))
        if valid:
            st.session_state.practice_user = {key: match.get(key) for key in ["name", "email", "admin"]}
            st.rerun()
        st.error("The selected user and PIN did not match.")
    st.stop()

user = shared_sign_in()
roster = shared_users()
all_initiatives = TeamStore.initiatives(raw_data)
initiatives = visible_records(all_initiatives, "Practice")
extra = TeamStore.extras(raw_data)

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio(
        "Navigate",
        [
            "Home",  "Physician RVUs",
            "📅 Call & Vacation",
            
            "📚 Clinical Intelligence",
            "🚀 Initiatives",
            "⚖️ Decisions",
            "🌱 Practice Growth",
            "📊 Strategic Planning",
        ],
    )
    st.caption(f"Signed in: {user['name']}")
    if st.button("Refresh"):
        st.rerun()
    if st.button("Sign out"):
        st.session_state.pop("practice_user", None)
        st.rerun()


target_page = st.session_state.pop("practice_home_target_page", None)
if target_page:
    page = target_page

if page == "Home":
    render_practice_home(extra, user)

elif page == "Physician RVUs":
    rvu = extra.get("rvu_metrics", {})
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))
    totals = add_annual_metrics(practice_total_rows(rvu))
    physician_annual = add_annual_metrics(physician)

    tabs = st.tabs([
        "Practice Totals",
        "Monthly Trends",
        "Year-over-Year",
        "Physician Self-Trends",
        "Physician Data",
    ])

    with tabs[0]:
        if totals.empty:
            st.info("No RVU totals.")
        else:
            st.dataframe(totals, hide_index=True, use_container_width=True)

    with tabs[1]:
        if totals.empty or "Fiscal Year" not in totals.columns:
            st.info("No graphable RVU data.")
        else:
            months = [month for month in MONTHS if month in totals.columns]
            long = totals.melt(
                id_vars=["Fiscal Year"],
                value_vars=months,
                var_name="Month",
                value_name="RVUs",
            ).dropna(subset=["RVUs"])
            long["Order"] = long["Month"].map(
                {month: index for index, month in enumerate(months)}
            )
            chart = long.pivot_table(
                index="Order",
                columns="Fiscal Year",
                values="RVUs",
                aggfunc="sum",
            )
            chart.index = [months[int(index)] for index in chart.index]
            st.line_chart(chart)
            st.dataframe(
                long[["Fiscal Year", "Month", "RVUs"]],
                hide_index=True,
                use_container_width=True,
            )

    with tabs[2]:
        practice_yoy = add_yoy(totals)
        if practice_yoy.empty:
            st.info("No year-over-year RVU data.")
        else:
            st.bar_chart(practice_yoy.set_index("Fiscal Year")["FY Total"])
            columns = [
                "Fiscal Year", "FY Total", "Months Entered",
                "Monthly Average", "Projected FY RVUs",
                "Prior FY Total", "YoY Change", "YoY %",
            ]
            available = [column for column in columns if column in practice_yoy.columns]
            st.dataframe(
                practice_yoy[available],
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Year-over-year comparisons are most meaningful when both fiscal years "
                "contain the same number of entered months."
            )

    with tabs[3]:
        if physician_annual.empty or "Physician" not in physician_annual.columns:
            st.info("No physician trend data.")
        else:
            physicians = sorted(
                value for value in physician_annual["Physician"].dropna().unique()
                if str(value).strip()
            )
            selected = st.multiselect(
                "Physician",
                physicians,
                default=physicians,
            )
            filtered = physician_annual[
                physician_annual["Physician"].isin(selected)
            ].copy()
            if not filtered.empty:
                st.line_chart(
                    filtered.pivot_table(
                        index="Fiscal Year",
                        columns="Physician",
                        values="FY Total",
                        aggfunc="sum",
                    )
                )
                self_yoy = add_yoy(filtered, "Physician")
                columns = [
                    "Fiscal Year", "Physician", "FY Total", "Months Entered",
                    "Monthly Average", "Projected FY RVUs", "Prior FY Total",
                    "YoY Change", "YoY %",
                ]
                available = [column for column in columns if column in self_yoy.columns]
                st.dataframe(
                    self_yoy[available].sort_values(["Physician", "Fiscal Year"]),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(
                    "No ranking is used. Each physician is shown only against that "
                    "physician's own prior history."
                )

    with tabs[4]:
        if physician.empty:
            st.info("No physician data.")
        else:
            st.dataframe(physician, hide_index=True, use_container_width=True)


elif page == "📅 Call & Vacation":
    render_readonly(ensure_store(extra))


elif page == "📚 Clinical Intelligence":
    render_clinical_intelligence(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "🚀 Initiatives":
    render_initiatives_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "⚖️ Decisions":
    render_decisions_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "🌱 Practice Growth":
    render_growth_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "📊 Strategic Planning":
    render_strategic_planning_center(extra, lambda updated: store.save(raw_data))
