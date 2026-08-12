import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

for name in [
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.EnemyDef.ID",
    "app.EnemyDef.ID_Fixed",
    "app.net_quest_session.cSearchQuestSessionInfo.SEARCH_QUEST_TYPE",
]:
    obj = data[name]
    print("====", name)
    fields = obj.get("fields") or {}
    for k, f in fields.items():
        if isinstance(f, dict):
            print(k, "offset", f.get("offset_from_base"), "init", f.get("init_data_index"), f)

# NetworkManager instance access
obj = data["app.NetworkManager"]
print("==== NetworkManager instance-ish methods")
for k, m in sorted((obj.get("methods") or {}).items()):
    if not isinstance(m, dict):
        continue
    if any(x in k.lower() for x in ("instance", "get_session", "get_request", "ctor", "element")):
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  {k}({ps}) -> {ret}")

# parent GAElement methods via parent type
parent = data.get("ace.GAElement`1<app.NetworkManager>")
print("==== GAElement NetworkManager", "yes" if parent else "no")
if parent:
    for k, m in sorted((parent.get("methods") or {}).items()):
        if isinstance(m, dict) and "nstance" in k.lower():
            print(" ", k)

# also check ace.Singleton etc
for k in data:
    if isinstance(k, str) and "GAElement" in k and "NetworkManager" in k:
        print("KEY", k)
