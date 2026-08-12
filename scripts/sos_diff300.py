import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

# cQuestDifficultyData + related
for name in [
    "app.cGUI050000MemberSettingItemData.cQuestDifficultyData",
    "app.cGUI050000MemberSettingItemData.cTargetData",
    "app.cGUI050000MemberSettingItemData.cTargetData.TARGET_DATA",
    "app.EnemyDef.ROLE_ID",
    "app.QuestDef.QUEST_RANK",
    "app.QuestDef.Difficulty",
    "app.QuestDef.QUEST_LEVEL",
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
        print(f"  M {mk}({ps}) -> {ret}")

# find set_QuestDifficulty usages / methods that mention QuestDifficulty assignment context
print("==== methods with QuestDifficulty in name or RescueSearchDifficulty")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if "questdifficulty" in ml or "rescuesearchdiff" in ml or "difficultyrescue" in ml:
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"{k}.{mk}({ps}) -> {ret}")

# enums containing EX and value near 300 or named QuestLevel
print("==== enums with EX or HIGH and small field count")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    if "Quest" not in k:
        continue
    fields = obj.get("fields") or {}
    if "EX" in fields or "HIGH" in fields or "HIGH_RANK" in fields:
        parent = obj.get("parent")
        if parent != "System.Enum":
            continue
        print(k)
        for fk, fv in fields.items():
            if isinstance(fv, dict) and fk != "value__":
                print(f"  {fk}={fv.get('default')}")
