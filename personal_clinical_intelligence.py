import hashlib
import json
import pandas as pd
import streamlit as st

ARTICLE_STATES=["Unread","Reviewed","Not Relevant","Archived For Me"]
def aid(a):
    key=a.get("id") or a.get("link") or a.get("url")
    if key:return str(key)
    return hashlib.sha256(json.dumps({"title":a.get("title"),"source":a.get("source"),"date":a.get("date_added")},sort_keys=True,default=str).encode()).hexdigest()[:24]
def articles(extra):
    c=extra.get("clinical_intelligence",{});return c.get("items",c.get("articles",[]))
def names(extra):return [str(x.get("name")) for x in extra.get("collaboration",{}).get("users",[]) if x.get("active",True) and x.get("name")]
def user_for(extra,current):
    n=(current or {}).get("name") if current else None
    return n if n in names(extra) else (st.selectbox("Clinical Intelligence for",names(extra),key="ci31_user") if names(extra) else n or "Current User")
def render_personal_clinical_intelligence(extra,save_extra,current_user=None):
    collab=extra.setdefault("collaboration",{}); states_all=collab.setdefault("article_user_state",{});user=user_for(extra,current_user);states=states_all.setdefault(user,{})
    st.subheader("Clinical Intelligence"); query=st.text_input("Search articles, including my archive",placeholder="Title, author, journal, topic, keyword",key="ci31_search").strip().lower()
    filters=st.multiselect("Show articles with my status",ARTICLE_STATES,default=ARTICLE_STATES if query else ["Unread"],key=f"ci31_filters_{user}")
    rows=[]
    for a in articles(extra):
        article_id=aid(a);status=states.get(article_id,"Unread"); hay=" ".join(str(a.get(k,"")) for k in ["title","author","authors","journal","topic","source","synopsis","summary","abstract","key_findings","practice_relevance"]).lower()
        if status in filters and (not query or query in hay):rows.append((a,article_id,status))
    counts={s:sum(states.get(aid(a),"Unread")==s for a in articles(extra)) for s in ARTICLE_STATES};cols=st.columns(4)
    for col,s in zip(cols,ARTICLE_STATES):col.metric(s,counts[s])
    if not rows:st.info("No articles match the search and status filters.")
    for index,(a,article_id,status) in enumerate(rows):
        st.markdown(f"### {a.get('title','Untitled article')}");st.caption(f"My status: {status}");buttons=st.columns(4);chosen=None
        for col,(label,state,suffix) in zip(buttons,[("Mark Unread","Unread","u"),("Mark Reviewed","Reviewed","r"),("Not Relevant","Not Relevant","n"),("Archive For Me","Archived For Me","a")]):
            if col.button(label,key=f"ci31_{suffix}_{user}_{article_id}_{index}",use_container_width=True):chosen=state
        if chosen:states[article_id]=chosen;save_extra(extra);st.rerun()
        st.write(a.get("synopsis") or a.get("summary") or a.get("abstract") or "No synopsis available.")
        with st.expander("Full article details"):
            for label,k in [("Authors","authors"),("Journal","journal"),("Topic","topic"),("Key Findings","key_findings"),("Practice Relevance","practice_relevance"),("Source","source"),("Date","date_added")]:
                if a.get(k):st.markdown(f"**{label}:** {a[k]}")
            link=a.get("link") or a.get("url")
            if link:st.link_button("Open source",link)
            if st.button("Convert to Growth Strategy Suggestion",key=f"ci31_strategy_{article_id}_{index}"):
                gs=extra.setdefault("growth_strategy_26",{});queue=gs.setdefault("suggestion_queue",[]);queue.append({"id":"SUG-ART-"+article_id,"section":"Clinical Services","bucket":"service_objects","title":a.get("title","Article-based suggestion"),"description":a.get("synopsis") or a.get("summary") or "Review this article for strategy implications.","submitted_by":user,"submitted_at":pd.Timestamp.utcnow().isoformat(),"reviewer":"Jackie Gurr","status":"Suggestion","source_article":link or article_id,"archive_reason":""});save_extra(extra);st.success("Strategy suggestion submitted.")
        st.divider()
