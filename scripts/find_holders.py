import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_holders.txt")
print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
want_types = {
    "app.net_quest_session.cQuestSession",
    "app.net_quest_session.QuestMatchmakeSystem",
    "app.net_session_manager.SessionManager",
}
lines = []
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app."):
        continue
    if "<>" in name or "`" in name:
        continue
    if not isinstance(obj, dict):
        continue
    fields = obj.get("fields") or {}
    if not isinstance(fields, dict):
        continue
    hits = []
    for fk, fv in fields.items():
        if isinstance(fv, dict) and fv.get("type") in want_types:
            hits.append(f"{fk}: {fv.get('type')}")
    methods = obj.get("methods") or {}
    mhits = []
    if isinstance(methods, dict):
        for mk, mv in methods.items():
            if not isinstance(mv, dict):
                continue
            ret = mv.get("returns")
            rtype = ret.get("type") if isinstance(ret, dict) else ret
            if rtype in want_types:
                mhits.append(f"{mk} -> {rtype}")
    if hits or mhits:
        lines.append(f"==== {name}")
        for h in hits:
            lines.append("  F " + h)
        for h in mhits:
            lines.append("  M " + h)

OUT.write_text("\n".join(lines), encoding="utf-8")
print("wrote", OUT, "holders", lines.count("===="))
