import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

for name in [
    "app.net_session_manager.SessionManager.cSearchResultTblQuest",
    "app.net_session_manager.SessionManager.cSearchResultQuest",
    "app.net_session_manager.cSearchSessionInfo",
    "app.Net_SessionService",
]:
    obj = data.get(name) or {}
    print("====", name)
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict): continue
        low = mk.lower()
        if any(x in low for x in ("search", "result", "get_", "set_", "count", "item", "list", "quest", "join", "accept", "filter")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict): ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')}")
