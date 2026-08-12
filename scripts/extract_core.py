"""Re-extract type summaries — methods/fields are dicts in this dump format."""
import json
import re
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT_DIR = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CORE = [
    "app.GUI040205PartsEnemyList",
    "app.GUI040205PartsEnemyDetail",
    "app.GUI040200PartsEnemyReport",
    "app.GUI040205",
    "app.GUI040200",
    "app.cGUICommonMenu_EnemyReportBoss",
    "app.cGUIPartsEnemyReportPageBase",
    "app.cGUI050000QuestSearchWindowCtrl",
    "app.cGUI050000ViewFlow",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
    "app.cGUI050000ViewFlow.Flow.QuestSelect",
    "app.cGUI050000ViewFlow.Flow.RescueSetting",
    "app.cGUI050000ViewFlow.cContext",
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
    "app.GUI050000MonsterListParts",
    "app.QuestCounterGUIContext",
    "app.GUIUtilApp.QuestUtil",
    "app.cGUICreateQuestSessionHelper",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
    "app.cGUI050000MemberSettingItemData.cTargetData",
    "app.user_data.EnemyReportBossData.cData",
    "app.GUI040205.BossReportInfo",
]


def strip_id(name: str) -> str:
    return re.sub(r"\d+$", "", name)


def summarize(obj: dict) -> dict:
    methods = {}
    raw_methods = obj.get("methods") or {}
    if isinstance(raw_methods, dict):
        for k, m in raw_methods.items():
            if not isinstance(m, dict):
                continue
            nice = strip_id(k)
            args = []
            for a in m.get("args") or []:
                if isinstance(a, dict):
                    args.append({"name": a.get("name"), "type": a.get("type")})
            methods[nice] = {
                "id_key": k,
                "args": args,
                "returns": (m.get("returns") or {}).get("type") if isinstance(m.get("returns"), dict) else m.get("returns"),
            }

    fields = {}
    raw_fields = obj.get("fields") or {}
    if isinstance(raw_fields, dict):
        for k, f in raw_fields.items():
            if isinstance(f, dict):
                fields[k] = {"type": f.get("type"), "offset": f.get("offset_from_base")}

    props = {}
    raw_props = obj.get("properties") or {}
    if isinstance(raw_props, dict):
        for k, p in raw_props.items():
            if isinstance(p, dict):
                props[k] = {"getter": p.get("getter"), "setter": p.get("setter")}

    return {
        "parent": obj.get("parent"),
        "methods": methods,
        "fields": fields,
        "properties": props,
        "method_names": sorted(methods.keys()),
        "field_names": sorted(fields.keys()),
    }


def main():
    print("loading...")
    with DUMP.open("r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    index = []
    for name in CORE:
        obj = data.get(name)
        if not obj:
            print("MISS", name)
            continue
        summary = summarize(obj)
        out = OUT_DIR / (name.replace(".", "_") + ".json")
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        index.append({"name": name, "methods": len(summary["methods"]), "fields": len(summary["fields"])})
        print(f"OK {name} m={len(summary['methods'])} f={len(summary['fields'])}")
        # print interesting method names
        interesting = [m for m in summary["method_names"] if any(
            x in m.lower() for x in ("select", "search", "accept", "join", "depart", "start", "enemy", "target", "rescue", "sos", "quest", "open", "get_", "set_")
        )]
        for m in interesting[:40]:
            print("   ", m, summary["methods"][m].get("args"), "->", summary["methods"][m].get("returns"))

    (OUT_DIR / "_core_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
