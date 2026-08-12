import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.user_data.QuestDifficultySearchParamData",
    "app.user_data.QuestDifficultySearchParamData.cData",
    "app.user_data.GUIVariousData",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    print(" parent", obj.get("parent"))
    for k, v in (obj.get("fields") or {}).items():
        if isinstance(v, dict) and k != "value__":
            print(f"  F {k}: {v.get('type')} default={v.get('default')}")
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        if any(
            x in mk.lower()
            for x in ("quest", "diff", "search", "value", "get_", "param", "ex")
        ):
            print(f"  M {mk}({ps}) -> {ret}")

# any type with ChoiceValueList
print("==== ChoiceValueList owners / SearchParam value")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    fields = obj.get("fields") or {}
    if "ChoiceValueList" in fields or "SearchParamValue" in fields or "NetValue" in fields:
        if "050000" in k or "Difficulty" in k or "Rescue" in k or "Search" in k:
            print(k)
            for fk, fv in fields.items():
                if isinstance(fv, dict):
                    print(f"  F {fk}: {fv.get('type')}")
