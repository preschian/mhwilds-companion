import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.net_quest_session.cJoinQuestSessionInfo",
    "app.net_session_manager.SessionManager.cSearchResultQuest",
    "app.net_quest_session.QuestMatchmakeSystem",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(x in ml for x in ("join", "from", "search", "setup", "ctor", "set_", "get_", "rescue", "session")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict) and fk != "value__":
            print(f"  F {fk}: {fv.get('type')}")
