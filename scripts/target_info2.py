import json
from pathlib import Path

data = json.load(open(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json", encoding="utf-8", errors="ignore"))
for name in [
    "app.net_session_manager.SessionManager.cSearchResultQuest.TargetInfo",
    "ace.cLimitedArray`1<app.net_session_manager.SessionManager.cSearchResultQuest>",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')}")
