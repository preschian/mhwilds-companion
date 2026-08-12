import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_methods.txt")

NAMES = [
    "app.cQuestAcceptArg.cResueuSearchParam",
    "app.net_quest_session.QuestMatchmakeSystem",
    "app.net_quest_session.cSearchQuestSessionInfo",
    "app.GUI040205PartsEnemyList",
    "app.GUI040205PartsEnemyDetail",
    "app.GUI040205",
    "app.GUI040205.BossReportInfo",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
    "app.cGUI050000ViewFlow.Flow.RescueSetting",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
    "app.cGUI050000MemberSettingItemData.cTargetData",
    "app.GUIUtilApp.QuestUtil",
    "app.cGUIQuestOrderHelper",
    "app.cGUICommonMenu_QuestDeparture",
    "app.cGUICommonMenu_ApprovalQuestJoin",
    "app.cGUI050000QuestSearchWindowCtrl",
    "app.user_data.EnemyReportBossData.cData",
    "app.EnemyDefID",
    "app.EnemyDef.ID",
    "app.EnemyID",
]

print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
lines = []

for name in NAMES:
    obj = data.get(name)
    if not obj:
        lines.append(f"==== MISS {name}")
        continue
    methods = obj.get("methods") or {}
    fields = obj.get("fields") or {}
    props = obj.get("properties") or {}
    lines.append(f"==== {name} methods={len(methods)} fields={len(fields)} props={len(props)} parent={obj.get('parent')}")
    for k, m in sorted(methods.items()):
        if not isinstance(m, dict):
            continue
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  M {k}({ps}) -> {ret}")
    for k, f in sorted(fields.items()):
        if isinstance(f, dict):
            lines.append(f"  F {k}: {f.get('type')}")
    for k, p in sorted(props.items()):
        if isinstance(p, dict):
            lines.append(f"  P {k}: get={p.get('getter')} set={p.get('setter')}")

# also find EnemyDef / FixedID type keys
enemy_keys = [k for k in data if isinstance(k, str) and ("EnemyDef" in k or k.endswith(".EnemyID") or "FixedID" in k) and k.startswith("app.") and "`" not in k and "<>" not in k]
lines.append("==== enemy-related type keys")
for k in sorted(enemy_keys)[:80]:
    lines.append(k)

OUT.write_text("\n".join(lines), encoding="utf-8")
print("wrote", OUT, "lines", len(lines))
