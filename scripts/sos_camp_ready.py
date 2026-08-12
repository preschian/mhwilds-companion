import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

obj = data.get("app.GUI050002")
print("==== app.GUI050002 all methods")
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict):
        continue
    params = mv.get("params") or []
    ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
    ret = mv.get("returns")
    if isinstance(ret, dict):
        ret = ret.get("type")
    print(f"  M {mk}({ps}) -> {ret}")
print("==== fields")
for fk, fv in sorted((obj.get("fields") or {}).items()):
    if isinstance(fv, dict):
        print(f"  F {fk}: {fv.get('type')}")

print("==== GUI050002 Def / related")
for k in sorted(data):
    if isinstance(k, str) and k.startswith("app.GUI050002"):
        print(k)

# search message keys
print("==== string-ish session not found")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    for mk in (obj.get("methods") or {}):
        ml = mk.lower()
        if "session" in ml and any(
            x in ml for x in ("notfound", "noexist", "missing", "invalid", "fail", "error", "empty")
        ):
            print(f"{k}.{mk}")
    for fk in (obj.get("fields") or {}):
        fl = fk.lower()
        if "session" in fl and any(x in fl for x in ("not", "fail", "err", "miss", "invalid")):
            print(f"FIELD {k}.{fk}")

# OrderGuest join flow
for name in [
    "app.GUIFlowGUI050001View.Flow.OrderGuest",
    "app.GUI050001",
    "app.GUIUtilApp.QuestUtil",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if any(
            x in mk.lower()
            for x in ("join", "depart", "accept", "ready", "session", "order", "start", "rescue")
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
