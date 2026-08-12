import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.cGUIQuestOrderParam.QUEST_ORDER_FROM",
    "app.cGUIQuestOrderParam.QUEST_START_TYPE",
    "app.cGUIQuestViewData.cGUISessionData",
    "app.GUI050000.QUEST_TYPE",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for k, v in (obj.get("fields") or {}).items():
        if isinstance(v, dict) and k != "value__":
            print(f"  {k}={v.get('default')} type={v.get('type')}")
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
