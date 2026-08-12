import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

for name in [
    "app.Net_SessionService",
    "app.NetworkRequestManager",
    "app.NetworkManager",
    "app.NetManager",
    "app.GameService",
    "app.SaveDataManager",
]:
    obj = data.get(name)
    print("====", name, "exists" if obj else "MISS")
    if not obj:
        continue
    methods = obj.get("methods") or {}
    fields = obj.get("fields") or {}
    props = obj.get("properties") or {}
    print(" parent", obj.get("parent"), "m", len(methods), "f", len(fields))
    for k, m in sorted(methods.items()):
        if not isinstance(m, dict):
            continue
        if any(x in k.lower() for x in ("quest", "session", "instance", "get_", "set_", "init")):
            params = m.get("params") or []
            ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
            ret = m.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {k}({ps}) -> {ret}")
    for k, f in sorted(fields.items()):
        if isinstance(f, dict) and ("Session" in k or "Quest" in k or "Instance" in k or k.startswith("_")):
            print(f"  F {k}: {f.get('type')}")
    for k in sorted(props):
        print(f"  P {k}")

# find who holds Net_SessionService
want = {"app.Net_SessionService", "app.NetworkRequestManager"}
print("==== holders of Net_SessionService / NetworkRequestManager")
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app.") or "<>" in name or "`" in name:
        continue
    if not isinstance(obj, dict):
        continue
    fields = obj.get("fields") or {}
    if not isinstance(fields, dict):
        continue
    for fk, fv in fields.items():
        if isinstance(fv, dict) and fv.get("type") in want:
            print(f"  {name}.{fk}: {fv.get('type')}")
    methods = obj.get("methods") or {}
    if isinstance(methods, dict):
        for mk, mv in methods.items():
            if not isinstance(mv, dict):
                continue
            ret = mv.get("returns")
            rtype = ret.get("type") if isinstance(ret, dict) else ret
            if rtype in want:
                print(f"  {name}.{mk} -> {rtype}")
