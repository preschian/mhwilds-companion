import re

path = r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json"

pats = [
    ("guide", re.compile(rb'"(app\.[^"]*(?:Zukan|HunterNote|FieldGuide|EnemyBook|Ecology|PictureBook|AnimalBook|MonsterBook|GuideBook|EnemyGuide|BossGuide|LargeEnemy|EnemyList|HunterGuide)[^"]*)"')),
    ("sos", re.compile(rb'"(app\.[^"]*(?:Sos|SOS|Flare|MatchMake|Matchmake|QuestSearch|QuestJoin|QuestAccept|QuestCounter|QuestBoard|Rescue)[^"]*)"')),
    ("gui", re.compile(rb'"(app\.GUI[^"]*(?:Quest|Sos|SOS|Note|Guide|Enemy|Book|Zukan|Ecology)[^"]*)"')),
    ("cgui", re.compile(rb'"(app\.cGUI[^"]*(?:Quest|Sos|SOS|Note|Guide|Enemy|Book|Zukan|Ecology)[^"]*)"')),
    ("enemyid", re.compile(rb'"(app\.[^"]*Enemy(?:Def)?ID[^"]*)"')),
]

found = {k: set() for k, _ in pats}

with open(path, "rb") as f:
    buf = b""
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if not chunk:
            break
        data = buf + chunk
        for key, pat in pats:
            for m in pat.finditer(data):
                found[key].add(m.group(1).decode("ascii", "ignore"))
        buf = data[-4000:]

out = r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_hits.txt"
with open(out, "w", encoding="utf-8") as o:
    for key, _ in pats:
        o.write(f"==== {key} ({len(found[key])})\n")
        for x in sorted(found[key]):
            o.write(x + "\n")
        o.write("\n")
print("wrote", out)
for key, _ in pats:
    print(key, len(found[key]))
