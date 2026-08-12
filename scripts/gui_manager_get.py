import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

for name in [
    "app.GUIManager",
    "ace.GUIManagerBase`2<app.GUIID.ID,app.GUIFunc.TYPE>",
    "ace.GUIManagerBase`2[[app.GUIID.ID, application, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null],[app.GUIFunc.TYPE, application, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null]]",
]:
    obj = data.get(name)
    print("====", name, "FOUND" if obj else "MISS")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        low = mk.lower()
        if any(x in low for x in ("getgui", "findgui", "get_gui", "opengui", "isopen", "getcomponent", "getitem", "getactive", "guilist")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  {mk}({ps}) -> {ret}")

# fuzzy find GUIManagerBase
print("==== keys with GUIManagerBase")
for k in data:
    if isinstance(k, str) and "GUIManagerBase" in k:
        print(k)
