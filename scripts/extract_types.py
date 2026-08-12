"""Extract selected type definitions from il2cpp_dump.json into smaller JSON files."""
import json
import re
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT_DIR = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "app.GUI040205PartsEnemyList",
    "app.GUI040205PartsEnemyDetail",
    "app.GUI040200PartsEnemyReport",
    "app.cGUICommonMenu_EnemyReportBoss",
    "app.cGUIPartsEnemyReportPageBase",
    "app.cGUIPartsEnemyReportBossGuidance",
    "app.cGUI050000QuestSearchWindowCtrl",
    "app.cGUI050000ViewFlow",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
    "app.cGUI050000ViewFlow.Flow.QuestSelect",
    "app.cGUI050000ViewFlow.Flow.RescueSetting",
    "app.cQuestAcceptArg",
    "app.cQuestAcceptArg.cResueuSearchParam",
    "app.GUIFlowQuestCounter",
    "app.GUIFlowQuestCounter.cContext",
    "app.GUIFlowQuestCounter.Flow.QuestCounter",
    "app.GUIFlowQuestCounter.Flow.StartQuestOrder",
    "app.GUIFlowQuestCounter.Flow.SelectStartingPoint",
    "app.cGUICommonMenu_QuestCounter",
    "app.cGUICommonMenu_QuestDeparture",
    "app.cGUICommonMenu_ApprovalQuestJoin",
    "app.cGUICommonMenu_QuestOrder",
    "app.cGUIQuestOrderHelper",
    "app.cGUIQuestOrderParam",
    "app.cGUIQuestViewData",
    "app.net_quest_session.QuestMatchmakeSystem",
    "app.GUI050000QuestListParts",
    "app.GUI050000PrevQuestParts",
    "app.QuestCounterGUIContext",
    "app.GUIUtilApp.QuestUtil",
    "app.cGUICreateQuestSessionHelper",
    "app.user_data.EnemyReportBossData",
    "app.user_data.EnemyReportBossData.cData",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
]

PREFIXES = (
    "app.GUI040205",
    "app.GUI040200",
    "app.cGUICommonMenu_EnemyReport",
    "app.cGUIPartsEnemyReport",
    "app.cGUI050000",
    "app.GUI050000",
    "app.cQuestAccept",
    "app.GUIFlowQuestCounter",
    "app.cGUICommonMenu_Quest",
    "app.cGUIQuest",
    "app.net_quest_session.QuestMatchmake",
    "app.QuestCounter",
    "app.GUIUtilApp.QuestUtil",
    "app.cGUICreateQuestSession",
    "app.user_data.EnemyReportBoss",
)


def safe_name(name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", name)[:180]


def summarize(obj: dict) -> dict:
    methods = []
    for m in obj.get("methods") or []:
        if isinstance(m, dict):
            methods.append(
                {
                    "name": m.get("name"),
                    "args": [a.get("type") if isinstance(a, dict) else a for a in (m.get("args") or [])],
                    "returns": m.get("returns") or m.get("return_type"),
                }
            )
    fields = []
    for f in obj.get("fields") or []:
        if isinstance(f, dict):
            fields.append({"name": f.get("name"), "type": f.get("type")})
    return {
        "fqname": obj.get("fqname") or obj.get("full_name") or obj.get("name"),
        "parent": obj.get("parent"),
        "methods": methods,
        "fields": fields,
        "method_count": len(methods),
        "field_count": len(fields),
    }


def main():
    print("Loading dump...")
    with DUMP.open("r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    print("keys:", len(data))

    wanted = set(TARGETS)
    for k in data:
        if not isinstance(k, str):
            continue
        if k.startswith("app.") and any(k.startswith(p) or k == p for p in PREFIXES):
            # skip compiler-generated nested display classes noise somewhat
            if "<>c" in k or "`" in k:
                continue
            wanted.add(k)

    index = []
    for name in sorted(wanted):
        obj = data.get(name)
        if not obj or not isinstance(obj, dict):
            print("MISS", name)
            continue
        summary = summarize(obj)
        out = OUT_DIR / (safe_name(name) + ".json")
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        index.append({"name": name, "methods": summary["method_count"], "fields": summary["field_count"], "file": out.name})
        print(f"OK {name} m={summary['method_count']} f={summary['field_count']}")

    (OUT_DIR / "_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print("done", len(index), "types")


if __name__ == "__main__":
    main()
