import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pediatric Cardiology Practice Command Center", page_icon="❤️", layout="wide")
SNAPSHOT = Path(__file__).parent / "practice_snapshot.json"

st.title("Pediatric Cardiology Practice Command Center")
st.caption("Read-only practice view. No patient-specific information or PHI.")

if not SNAPSHOT.exists():
    st.warning("No practice snapshot has been published yet.")
    st.stop()

try:
    data = json.loads(SNAPSHOT.read_text())
except (OSError, json.JSONDecodeError):
    st.error("The practice snapshot could not be read.")
    st.stop()

with st.sidebar:
    page = st.radio("Navigate", ["Home", "Initiatives", "Decisions", "Roadmap", "Clinical Intelligence", "Practice Growth", "Physician RVUs"])
    st.caption(f"Snapshot: {data.get('generated_at_utc', '')}")

if page == "Home":
    cols = st.columns(5)
    cols[0].metric("Initiatives", len(data.get("initiatives", [])))
    cols[1].metric("Decisions", len(data.get("decisions", [])))
    cols[2].metric("Roadmap", len(data.get("roadmap", [])))
    cols[3].metric("Intelligence", len(data.get("clinical_intelligence", {}).get("items", [])))
    cols[4].metric("Growth rows", len(data.get("growth", [])))
    st.subheader("Active Initiatives")
    active = [x for x in data.get("initiatives", []) if not x.get("archived", False)]
    st.dataframe(pd.DataFrame(active), hide_index=True, use_container_width=True) if active else st.info("No active practice initiatives.")
elif page == "Initiatives":
    st.dataframe(pd.DataFrame(data.get("initiatives", [])), hide_index=True, use_container_width=True)
elif page == "Decisions":
    st.dataframe(pd.DataFrame(data.get("decisions", [])), hide_index=True, use_container_width=True)
elif page == "Roadmap":
    st.dataframe(pd.DataFrame(data.get("roadmap", [])), hide_index=True, use_container_width=True)
elif page == "Clinical Intelligence":
    for item in data.get("clinical_intelligence", {}).get("items", []):
        with st.expander(f"{item.get('content_type','')} | {item.get('title','Untitled')}"):
            st.write(item.get("summary", ""))
            if item.get("key_findings"):
                st.write(f"**Key findings:** {item['key_findings']}")
            if item.get("practice_relevance"):
                st.write(f"**Practice relevance:** {item['practice_relevance']}")
            if item.get("link"):
                st.link_button("Open original source", item["link"])
elif page == "Practice Growth":
    st.dataframe(pd.DataFrame(data.get("growth", [])), hide_index=True, use_container_width=True)
elif page == "Physician RVUs":
    rvu = data.get("rvu_metrics", {})
    st.subheader("Historical Practice Totals")
    st.dataframe(pd.DataFrame(rvu.get("historical_totals", [])), hide_index=True, use_container_width=True)
    st.subheader("Physician Monthly Entries")
    st.dataframe(pd.DataFrame(rvu.get("physician_rows", [])), hide_index=True, use_container_width=True)
