import re


def _text(value):
    return str(value or "").strip()


def _contains(text, terms):
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _planning_context(extra):
    planning = extra.get("strategic_planning_12", {})
    strategy = extra.get("growth_strategy_26", {})
    collaboration = extra.get("collaboration", {})
    demand = planning.get("demand", [])

    locations = []
    for row in demand:
        site = _text(row.get("Site"))
        if site:
            locations.append(site)

    roadmap = [
        item for item in strategy.get("draft_items", [])
        if item.get("status") not in {"Declined", "Archived", "Superseded"}
    ]

    return {
        "planning": planning,
        "strategy": strategy,
        "collaboration": collaboration,
        "locations": locations,
        "roadmap": roadmap,
        "initiatives": collaboration.get("initiatives", []),
        "decisions": collaboration.get("decisions", []),
        "growth": collaboration.get("practice_growth", []),
        "risks": planning.get("risks", []),
        "milestones": planning.get("milestones", []),
    }


def _horizon(prompt):
    text = prompt.lower()
    if re.search(r"\b10\s*[- ]?year|ten[- ]year|long[- ]term|north star", text):
        return "10-Year Vision"
    if re.search(r"\b5\s*[- ]?year|five[- ]year", text):
        return "5 Years"
    if re.search(r"\b3\s*[- ]?year|three[- ]year", text):
        return "3 Years"
    if re.search(r"\b1\s*[- ]?year|one[- ]year|next year|near[- ]term", text):
        return "1 Year"
    return None


def _location(prompt, locations):
    aliases = {
        "griffin": "Griffin / Spalding",
        "spalding": "Griffin / Spalding",
        "lagrange": "LaGrange",
        "la grange": "LaGrange",
        "paulding": "Paulding",
        "acworth": "Acworth",
        "ackworth": "Acworth",
        "woodstock": "Woodstock",
        "avalon": "Avalon",
        "douglasville": "Douglasville",
        "douglas": "Douglasville",
        "smyrna": "Smyrna",
        "barrett": "Barrett",
        "wga": "WGA",
        "west georgia": "WGA",
    }
    lowered = prompt.lower()
    for alias, canonical in aliases.items():
        if alias in lowered:
            return canonical
    for site in locations:
        if site.lower() in lowered:
            return site
    return None


def _service(prompt):
    text = " " + prompt.lower() + " "
    mapping = [
        ("Pediatric Electrophysiology", ["electrophysiology", " pediatric ep ", " ablation", "device clinic"]),
        ("Interventional Pediatric Cardiology", ["interventional", "cath lab", "catheterization"]),
        ("Adult Congenital Cardiology", ["adult congenital", " achd ", "transition clinic"]),
        ("Pediatric Cardiac Surgery", ["cardiac surgery", "heart surgery", "surgical program"]),
        ("Advanced Cardiac Imaging", ["cross-sectional imaging", "cross sectional imaging", "cardiac mri", "cardiac ct", " ct/mri"]),
        ("Fetal Cardiology", ["fetal", " mfm "]),
        ("Telemedicine", ["telemedicine", "telehealth", "virtual clinic", "remote visit"]),
        ("NICU / PICU Integration", ["nicu", "picu", "hospital coverage", "hospital integration"]),
    ]
    for service, terms in mapping:
        if any(term in text for term in terms):
            return service
    return None


def _topic(prompt):
    text = prompt.lower()
    if _contains(text, ["telemedicine", "telehealth", "virtual", "remote"]):
        return "Telemedicine"
    if _contains(text, ["hire", "recruit", "physician", "doctor", "provider", "workforce"]):
        return "Physician Workforce"
    if _contains(text, ["staff", "sonographer", "nurse", "medical assistant", " ma ", "front desk"]):
        return "Staffing"
    if _contains(text, ["equipment", "echo machine", "probe", "ekg", "space", "infrastructure", "capital"]):
        return "Equipment & Infrastructure"
    if _service(text):
        return "Clinical Services"
    if _contains(text, ["clinic", "location", "site", "outreach", "expand", "access"]):
        return "Locations & Access"
    if _contains(text, ["risk", "barrier", "problem", "challenge"]):
        return "Risk"
    if _contains(text, ["roadmap", "strategy", "priorities", "vision", "future", "plan"]):
        return "Integrated Strategy"
    return "Open Strategy Question"


def _related_roadmap(context, prompt, topic, location, service):
    terms = [topic, location, service]
    prompt_words = {word for word in re.findall(r"[a-zA-Z]{4,}", prompt.lower())}
    scored = []
    for item in context["roadmap"]:
        haystack = " ".join([
            _text(item.get("title")), _text(item.get("description")),
            _text(item.get("domain")), _text(item.get("service")),
        ]).lower()
        score = sum(3 for term in terms if term and term.lower() in haystack)
        score += sum(1 for word in prompt_words if word in haystack)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:4]]


def _site_data(context, location):
    if not location:
        return None
    search_terms = {location.lower()}
    if location == "Griffin / Spalding":
        search_terms.update({"griffin", "spalding"})
    for row in context["planning"].get("demand", []):
        site = _text(row.get("Site")).lower()
        if any(term in site or site in term for term in search_terms):
            return row
    return None


def _recommendation(topic, horizon, location, service, site_row):
    horizon = horizon or "the next planning horizon"
    if topic == "Telemedicine":
        where = f" in {location}" if location else " across selected outreach locations"
        return (
            f"I would treat telemedicine{where} as a staged access model, not simply as a video-visit project. "
            "Start with visit types that do not require same-day advanced diagnostics, define local support and escalation, "
            "then use measured demand and completion data to decide whether to add more virtual access or permanent in-person clinic time."
        )
    if topic == "Physician Workforce":
        return (
            "I would not choose a hiring date from calendar preference alone. I would establish recruitment triggers using access, "
            "projected demand, physician-day capacity, hospital and call burden, outreach commitments, and the competencies needed for the next phase. "
            "Because recruitment and onboarding take time, the roadmap should trigger recruitment before the modeled shortage actually occurs."
        )
    if topic == "Staffing":
        return (
            "I would tie staffing additions to the operating model being created. Physician growth, hybrid outreach, fetal expansion, hospital work, "
            "and new diagnostics each create different needs, so the roadmap should specify the required role, location, trigger, and lead time rather than use one staffing ratio for everything."
        )
    if topic == "Equipment & Infrastructure":
        return (
            "I would separate immediate readiness needs from major capital investment. First determine what can be shared, transported, or supported through an existing hospital or MFM location. "
            "Then reserve permanent equipment and space commitments for locations or services that meet agreed volume, quality, and sustainability thresholds."
        )
    if topic == "Clinical Services":
        if service:
            return (
                f"I would place {service} into a staged readiness pathway over {horizon}: demand validation, expertise and partnership model, "
                "hospital and diagnostic dependencies, staffing and quality infrastructure, financial case, then a limited launch before scaling. "
                "The roadmap should not treat the final program as approved until these dependencies are resolved."
            )
        return (
            "I would prioritize clinical-service development by patient need, strategic fit, physician expertise, hospital readiness, referral leakage, and the number of foundational capabilities the service unlocks."
        )
    if topic == "Locations & Access":
        where = location or "the proposed location"
        return (
            f"For {where}, I would compare four choices: optimize the current schedule, add telemedicine between visits, add another in-person session, or establish a larger permanent presence. "
            "The decision should follow demand, access, diagnostic requirements, staff travel, available space, referral alignment, and the effect on nearby sites."
        )
    if topic == "Risk":
        return (
            "I would convert this into a named strategic risk with an owner, leading indicator, mitigation, decision deadline, and linked roadmap item. That keeps the concern visible without prematurely changing the official plan."
        )
    return (
        f"I would use {horizon} to define a small number of sequenced commitments rather than a long wish list. "
        "The strongest strategy will connect access and demand to workforce, telemedicine, clinical services, staffing, infrastructure, hospital alignment, quality, and measurable outcomes."
    )


def _questions(topic, location, service):
    if topic == "Telemedicine":
        return [
            f"Which patient and visit types are appropriate{f' in {location}' if location else ''}?",
            "What local room, check-in, clinical, diagnostic, and escalation support is available?",
            "What access, completion, quality, patient-experience, and referral-retention measures define success?",
            "What result would justify expansion, permanent clinic time, redesign, or discontinuation?",
        ]
    if topic == "Physician Workforce":
        return [
            "Which measurable thresholds should start recruitment?",
            "Which geographic, hospital, call, outreach, and subspecialty responsibilities must the next physician cover?",
            "What recruitment and onboarding lead time should the model use?",
            "Which staff, space, equipment, and diagnostic capacity must arrive with the physician?",
        ]
    if topic == "Clinical Services":
        return [
            f"What patient volume and referral leakage support {service or 'the service'}?",
            "Is the preferred model recruitment, partnership, visiting coverage, or an internal build?",
            "Which hospital, anesthesia, ICU, imaging, laboratory, staffing, and quality dependencies apply?",
            "What limited first-stage service could validate demand before a full program is built?",
        ]
    if topic == "Locations & Access":
        return [
            f"What are current demand, fill rate, wait time, referral sources, and nearby-site effects for {location or 'the location'}?",
            "Which patients require in-person diagnostics and which could use telemedicine?",
            "What space, staff, echo, EKG, and hospital or MFM support exists?",
            "What threshold should trigger another clinic day or a permanent site?",
        ]
    return [
        "What specific outcome should be true at the end of this horizon?",
        "Which evidence or assumptions drive the decision?",
        "What dependencies must be completed first?",
        "What measure and review date will tell leadership whether the strategy is working?",
    ]


def _actions(topic, horizon, location, service):
    label = location or service or topic
    return [
        f"Create or update a {horizon or '1 Year'} roadmap item for {label}",
        "Link the roadmap item to a Decision for unresolved leadership choices",
        "Create an Initiative for the next approved implementation step",
        "Add explicit dependencies, risks, success measures, and a review period",
    ]


def _specific_prompt(topic, horizon, location, service):
    parts = ["Analyze"]
    if location:
        parts.append(location)
    if service:
        parts.append(service)
    elif topic:
        parts.append(topic.lower())
    parts.append(f"over {horizon or 'the next 1 to 3 years'}")
    parts.append("using current demand, capacity, access, workforce, telemedicine, staffing, equipment, hospital dependencies, risks, and success measures")
    return " ".join(parts) + ". Recommend a sequence and propose specific roadmap changes."


def enhanced_conversational_response(prompt, extra):
    context = _planning_context(extra)
    horizon = _horizon(prompt)
    topic = _topic(prompt)
    location = _location(prompt, context["locations"])
    service = _service(prompt)
    related = _related_roadmap(context, prompt, topic, location, service)
    site_row = _site_data(context, location)

    recommendation = _recommendation(topic, horizon, location, service, site_row)
    context_lines = []
    if related:
        context_lines.append("Related roadmap work already in the system: " + "; ".join(_text(item.get("title")) for item in related))
    if site_row:
        available = []
        for field in ["FY26 Visits", "Growth %", "FY27 Override", "Projected Demand"]:
            if site_row.get(field) not in (None, ""):
                available.append(f"{field}: {site_row.get(field)}")
        if available:
            context_lines.append(f"Current planning inputs for {location}: " + ", ".join(available))
    context_lines.append(
        f"The current workspace includes {len(context['roadmap'])} active roadmap items, "
        f"{len(context['initiatives'])} initiatives, {len(context['decisions'])} decisions, "
        f"and {len(context['growth'])} growth items."
    )

    return {
        "horizon": horizon or "1 Year",
        "domain": topic if topic != "Integrated Strategy" else "Vision",
        "service": service or "General Pediatric Cardiology",
        "answer": recommendation,
        "context": context_lines,
        "questions": _questions(topic, location, service),
        "roadmap": _actions(topic, horizon or "1 Year", location, service),
        "suggested_prompt": _specific_prompt(topic, horizon, location, service),
        "topic": topic,
        "location": location,
        "related_titles": [_text(item.get("title")) for item in related],
    }
