import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

# GUI040205 fields/methods related to current/select
for name in ["app.GUI040205", "app.GUI040205PartsEnemyList", "app.GUI040205PartsEnemyDetail", "app.GUIManager"]:
    obj = data[name]
    print("====", name)
    fields = obj.get("fields") or {}
    for k, f in sorted(fields.items()):
        if isinstance(f, dict) and any(x in k.lower() for x in ("current", "select", "enemy", "boss", "focus", "index")):
            print(" F", k, f.get("type"))
    methods = obj.get("methods") or {}
    for k, m in sorted(methods.items()):
        if not isinstance(m, dict):
            continue
        if any(x in k.lower() for x in ("current", "select", "enemy", "get_gui", "find", "isopen", "getopen", "getcomponent")):
            params = m.get("params") or []
            ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params[:4])
            ret = m.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(" M", k, "(", ps, ") ->", ret)

# how to get open GUI by id
gm = data["app.GUIManager"]
print("==== GUIManager get GUI methods")
for k, m in sorted((gm.get("methods") or {}).items()):
    if not isinstance(m, dict):
        continue
    if any(x in k.lower() for x in ("getgui", "get_gui", "findgui", "opengui", "isopen", "getcomponent", "getactive")):
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params[:5])
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(" M", k, "(", ps, ") ->", ret)
