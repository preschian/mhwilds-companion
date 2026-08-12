import json

data = json.load(open(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json", encoding="utf-8", errors="ignore"))

for name in [
    "app.QuestDef.QUEST_TYPE_RESUCUE_SEARCH_PARAM",
    "app.QuestDef.QUEST_FIELD_RESCUE_SEARCH_PARAM",
    "app.MissionIDList.ID",
    "app.cGUI050000MemberSettingItemData.cTargetData.TARGET_DATA",
    "app.GUI050000",
    "app.cGUI050000ViewFlow.cGUI050000ViewFlowBase",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    parent = obj.get("parent")
    if parent:
        print(" parent", parent)
    fields = obj.get("fields") or {}
    # for big enums only print INVALID/NONE/ANY/ALL/WORLD etc and first few
    if name.endswith(".ID") or "PARAM" in name:
        for k, v in fields.items():
            if not isinstance(v, dict):
                continue
            if k == "value__":
                continue
            kl = k.upper()
            if any(x in kl for x in ("INVALID", "NONE", "ANY", "ALL", "WORLD", "CROSS", "SAME", "EX", "STORY", "HUNT", "MAX")) or len(fields) < 40:
                print(f"  {k}={v.get('default')}")
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if any(x in mk.lower() for x in ("search", "rescue", "rescure", "target", "setting", "make", "create", "build", "param", "open", "start")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted(fields.items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')}")

# language platform userdata
print("==== search language/platform userdata keys")
for k in data:
    if not isinstance(k, str):
        continue
    if ("Language" in k or "Platform" in k) and ("Search" in k or "Rescue" in k or "Quest" in k) and k.startswith("app.user_data"):
        print(k)
