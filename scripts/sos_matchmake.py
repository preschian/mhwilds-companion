import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.net_quest_session.QuestMatchmakeSystem",
    "app.net_quest_session.cQuestSession",
    "app.net_session_manager.SessionManager.cSearchResultTblQuest",
    "app.net_session_manager.SessionManager.cSearchResultQuest",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    print(" parent", obj.get("parent"))
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if any(
            x in mk.lower()
            for x in (
                "search",
                "rescue",
                "rescure",
                "result",
                "join",
                "match",
                "callback",
                "auto",
            )
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict) and any(
            x in fk.lower() for x in ("search", "rescue", "result", "match", "tbl")
        ):
            print(f"  F {fk}: {fv.get('type')}")

# language setting values in member setting
print("==== language/platform setting item data")
for k in sorted(data):
    if not isinstance(k, str):
        continue
    if "Language" in k and "050000" in k:
        print(k)
    if "Platform" in k and "050000" in k:
        print(k)
    if "MemberSetting" in k and ("Language" in k or "Platform" in k or "Target" in k):
        print(k)
