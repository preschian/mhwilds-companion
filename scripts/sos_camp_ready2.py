import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.GUI050002_DeparturePreparingLink",
    "app.GUI050002.Def.DEPART_PATTERN",
    "app.GUI050002.Def.PREPARING_STATUS",
    "app.cGUIQuestOrderHelper",
    "app.GUI050001",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict) and fk != "value__":
            print(f"  F {fk}: {fv.get('type')} d={fv.get('default')}")

# NETWORK_ERROR LOCAL_SESSION_NOT_FOUND value
nec = data.get("app.NETWORK_ERROR_CODE") or {}
for k, v in (nec.get("fields") or {}).items():
    if isinstance(v, dict) and "SESSION" in k and ("NOT_FOUND" in k or "QUEST" in k):
        print(f"ERR {k}={v.get('default')}")
