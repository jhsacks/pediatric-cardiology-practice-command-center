from pathlib import Path
import re
MODE="practice"
app=Path("app.py"); text=app.read_text()
if MODE=="practice":
    # Force all work routes to signed-in identity and disable View As.
    text=text.replace("allow_view_as=True","allow_view_as=False")
    for label,func in [("🚀 Initiatives","render_work_initiatives"),("⚖️ Decisions","render_work_decisions"),("🌱 Practice Growth","render_work_growth")]:
        pattern=rf'(?ms)^elif page == "{re.escape(label)}":.*?(?=^elif page == |\Z)'; call=f'elif page == "{label}":\n    {func}(extra, lambda updated: store.save(raw_data), current_user=user, allow_view_as=False)\n'; text,n=re.subn(pattern,call,text,count=1)
        if n!=1:raise SystemExit("Practice route not found: "+label)
    pattern=r'(?ms)^elif page == "📊 Strategic Planning":.*?(?=^elif page == |\Z)'; call='elif page == "📊 Strategic Planning":\n    render_strategic_planning_center(extra, lambda updated: store.save(raw_data), current_user=user)\n'; text,n=re.subn(pattern,call,text,count=1)
    if n!=1:raise SystemExit("Practice Strategic Planning route not found")
    if "allow_view_as=True" in text:raise SystemExit("Practice still contains View As enabled")
app.write_text(text)
print(f"Fix 24 routes applied for {MODE}")
