import json
from pathlib import Path

data = json.load(open(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json", encoding="utf-8", errors="ignore"))

for name in [
    "app.QuestDef.RANK",
    "app.QuestDef.EM_REWARD_RANK",
    "app.QuestDef.QUEST_TYPE",
    "app.QuestDef.DIFFICULTY",
    "app.QuestDef.QUEST_DIFFICULTY",
    "app.cGUI050000MemberSettingItemData.cQuestDifficultyData",
    "app.GUI050000PartsBase.SETTING_ITEM_RESCUESEARCH",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for k, v in (obj.get("fields") or {}).items():
        if isinstance(v, dict):
            print(f"  {k} = {v.get('default')}")
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if any(x in mk.lower() for x in ("diff", "rank", "high", "low", "rescue", "search", "get_", "set_")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")

# search for difficulty-related enums
print("==== type keys with Difficulty/RescueSearch")
for k in data:
    if not isinstance(k, str):
        continue
    if ("Difficulty" in k or "RescueSearch" in k or "QUEST_SEARCH" in k) and k.startswith("app.") and "<>" not in k and "`" not in k:
        print(k)
