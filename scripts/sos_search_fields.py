import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)


def dump(name, method_filter=None):
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        return
    print(" parent", obj.get("parent"))
    for k, v in (obj.get("fields") or {}).items():
        if not isinstance(v, dict) or k == "value__":
            continue
        print(f"  F {k}: {v.get('type')} default={v.get('default')}")
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if method_filter and not any(x in mk.lower() for x in method_filter):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")


for name in [
    "app.net_quest_session.cSearchQuestSessionInfo",
    "app.net_session_manager.cSearchSessionInfo",
    "app.net_quest_session.cSearchQuestSessionInfo.cTargetInfo",
    "app.net_quest_session.cSearchQuestSessionInfo.SEARCH_QUEST_TYPE",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.EnemyDef.LEGENDARY_ID",
    "app.QuestDef.QUEST_DIFFICULTY_RESCUE_SEARCH_PARAM",
    "app.QuestDef.QUEST_TYPE_RESUCUE_SEARCH_PARAM",
    "app.QuestDef.QUEST_FIELD_RESCUE_SEARCH_PARAM",
    "app.cQuestAcceptArg.cResueuSearchParam",
    "app.GUIUtilApp.QuestUtil",
]:
    dump(name)

print("==== methods mentioning make/create/build search or holder")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    methods = obj.get("methods") or {}
    for mk, mv in methods.items():
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(
            x in ml
            for x in (
                "makerescue",
                "createsearch",
                "makesearch",
                "buildsearch",
                "tosearch",
                "fromsetting",
                "searchinfo",
                "rescuesearch",
            )
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"{k}.{mk}({ps}) -> {ret}")
