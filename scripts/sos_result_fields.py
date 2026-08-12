import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.net_session_manager.SessionManager.cSearchResultQuest",
    "app.net_session_manager.SessionManager.cSearchResultQuest.TargetInfo",
    "app.EnemyDef.ID",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    fields = obj.get("fields") or {}
    if name.endswith(".ID"):
        for k, v in fields.items():
            if not isinstance(v, dict) or k == "value__":
                continue
            if "0160" in k or v.get("default") == 27:
                print(f"  {k}={v.get('default')}")
        continue
    for k, v in fields.items():
        if isinstance(v, dict) and k != "value__":
            print(f"  F {k}: {v.get('type')} default={v.get('default')}")
