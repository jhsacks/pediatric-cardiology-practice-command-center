from pathlib import Path

path = Path("growth_strategy.py")
text = path.read_text()

import_line = "from strategy_agent_29 import enhanced_conversational_response\n"
if import_line not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Growth Strategy Streamlit import not found. No changes made.")
    text = text.replace(marker, marker + import_line, 1)

old = "response=conversational_response(prompt,extra); history.append"
new = "response=enhanced_conversational_response(prompt,extra); history.append"
if old in text:
    text = text.replace(old, new, 1)
elif "response=enhanced_conversational_response(prompt,extra); history.append" not in text:
    raise SystemExit("Strategy Agent response call not found. No changes made.")

# Add context display after the main answer, if the current compact agent renderer is present.
old_display = '        st.markdown(response["answer"]); st.markdown("#### Questions worth answering")'
new_display = '''        st.markdown(response["answer"])
        if response.get("context"):
            st.markdown("#### What I considered")
            for line in response["context"]:
                st.write("• " + line)
        st.markdown("#### Questions worth answering")'''
if old_display in text:
    text = text.replace(old_display, new_display, 1)
elif 'st.markdown("#### What I considered")' not in text:
    raise SystemExit("Strategy Agent display block not found. No changes made.")

for token in [
    import_line.strip(),
    "enhanced_conversational_response(prompt,extra)",
    'st.markdown("#### What I considered")',
]:
    if token not in text:
        raise SystemExit("Strategy Agent 29 validation failed: " + token)

path.write_text(text)
print("Context-aware Strategy Agent 29 installed.")
