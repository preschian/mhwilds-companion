import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_raw_samples.json")

names = [
    "app.GUI040205PartsEnemyList",
    "app.cGUI050000QuestSearchWindowCtrl",
    "app.cQuestAcceptArg",
    "app.cQuestAcceptArg.cResueuSearchParam",
    "app.net_quest_session.QuestMatchmakeSystem",
    "app.cGUICommonMenu_EnemyReportBoss",
    "app.GUIFlowQuestCounter",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
    "app.cGUI050000MemberSettingItemData.cTargetData",
]

print("loading...")
with DUMP.open("r", encoding="utf-8", errors="ignore") as f:
    data = json.load(f)

samples = {}
for n in names:
    obj = data.get(n)
    if obj is None:
        samples[n] = None
        continue
    # keep structure but truncate huge nested lists
    if isinstance(obj, dict):
        slim = {}
        for k, v in obj.items():
            if isinstance(v, list) and len(v) > 5:
                slim[k] = v[:5] + [f"...(+{len(v)-5} more)"]
            elif isinstance(v, dict) and len(v) > 30:
                # show keys only for huge dicts
                keys = list(v.keys())
                slim[k] = {"_keys_sample": keys[:40], "_key_count": len(keys)}
            else:
                slim[k] = v
        samples[n] = slim
    else:
        samples[n] = {"_typeof": str(type(obj)), "_value": str(obj)[:500]}

OUT.write_text(json.dumps(samples, indent=2, default=str)[:500000], encoding="utf-8")
print("wrote", OUT)
for n, v in samples.items():
    if v is None:
        print("MISS", n)
    elif isinstance(v, dict):
        print(n, "topkeys=", list(v.keys())[:20])
