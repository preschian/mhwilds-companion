import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

# find message / method related to missing quest session
hits = []
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    kl = k.lower()
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(
            x in ml
            for x in (
                "noquest",
                "questsession",
                "syncquestdepart",
                "questdepart",
                "departquest",
                "requestquestdepart",
                "ondepart",
                "campdepart",
            )
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            hits.append(f"{k}.{mk}({ps}) -> {ret}")

print("==== method hits", len(hits))
for h in hits[:80]:
    print(h)

# GUI related to camp depart / quest start
print("==== GUI camp / depart types")
for k in sorted(data):
    if not isinstance(k, str):
        continue
    if any(x in k for x in ("GUI02000", "CampMenu", "QuestDepart", "QuestStart", "GUI01000")):
        if k.startswith("app.GUI") and "[]" not in k and "`" not in k:
            print(k)

for name in [
    "app.GUIManager",
    "app.GUIUtilApp.QuestUtil",
]:
    obj = data.get(name)
    print("====", name, "depart-ish")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if any(x in mk.lower() for x in ("depart", "camp", "start", "ready", "accept", "session")):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            if len(ps) < 100:
                print(f"  M {mk}({ps}) -> {ret}")
