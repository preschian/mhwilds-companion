import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.GUI050002_DeparturePreparingLink.CONTENS_TYPE",
    "app.GUI050002_DeparturePreparingLink.MENU_ITEM_INDEX",
    "app.cGUIQuestOrderHelper.ORDER_TYPE",
]:
    obj = data.get(name)
    print("====", name)
    if not obj:
        print(" MISS")
        continue
    for k, v in (obj.get("fields") or {}).items():
        if isinstance(v, dict) and k != "value__":
            print(f"  {k}={v.get('default')}")
