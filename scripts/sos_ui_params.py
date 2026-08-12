import json
from pathlib import Path

data = json.load(open(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json", encoding="utf-8", errors="ignore"))
out = []

def dump(name, limit_methods=None):
    obj = data.get(name)
    out.append(f"==== {name} {'MISS' if not obj else ''}")
    if not obj:
        return
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        if limit_methods and not any(x in mk.lower() for x in limit_methods):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        out.append(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            out.append(f"  F {fk}: {fv.get('type')} default={fv.get('default')}")

# enums likely used by SOS UI
for name in [
    "app.QuestDef.QUEST_DIFFICULTY_RESCUE_SEARCH_PARAM",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.EnemyDef.LEGENDARY_ID",
    "app.FieldDef.STAGE",
]:
    obj = data.get(name) or {}
    out.append(f"==== ENUM {name}")
    for k, v in (obj.get("fields") or {}).items():
        if isinstance(v, dict) and k != "value__":
            out.append(f"  {k}={v.get('default')}")

# language / platform search enums
out.append("==== keys language/platform/rescue")
for k in data:
    if not isinstance(k, str) or not k.startswith("app."):
        continue
    if "<>" in k or "`" in k:
        continue
    if any(x in k for x in (
        "RescueSearch", "SEARCH_PARAM", "SearchLang", "LanguageSetting",
        "PlatformType", "CrossPlay", "WORLDWIDE", "QuestSearch",
        "cTargetData", "TARGET_DATA",
    )):
        out.append(k)

dump("app.cGUI050000ViewFlow.Flow.SearchQuest")
dump("app.cGUI050000ViewFlow.Flow.RescueSetting")
dump("app.cGUI050000QuestSearchWindowCtrl")
dump("app.GUI050000PartsBase.cRescueSearchSettingParamHolder")
dump("app.cGUI050000MemberSettingItemData.cTargetData")
dump("app.cGUI050000MemberSettingItemData.cTargetData.TARGET_DATA")
dump("app.cQuestAcceptArg.cResueuSearchParam")

# find methods that create search info from rescue params
out.append("==== methods referencing cSearchQuestSessionInfo or RescueSearch")
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app."):
        continue
    if "<>" in name or "`" in name:
        continue
    if not isinstance(obj, dict):
        continue
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        types = [p.get("type") for p in params if isinstance(p, dict)]
        ret = mv.get("returns")
        rtype = ret.get("type") if isinstance(ret, dict) else ret
        blob = " ".join([mk] + [t or "" for t in types] + [rtype or ""])
        if "cSearchQuestSessionInfo" in blob or "RescueSearch" in blob or "ResueuSearch" in blob:
            if name.startswith("System."):
                continue
            out.append(f"{name}.{mk}({', '.join(types)}) -> {rtype}")

Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_sos_ui_params.txt").write_text("\n".join(out), encoding="utf-8")
print("lines", len(out))
print("\n".join(out[:80]))
