# NCAA College Football 2K3 Roster Editor

**Version 1.10.0+ (fixed drop)** | GameCube | Python + PyQt5  
**PWA**: https://jtfresh90.github.io/NCAA-2K3-Roster-Editor/mobile/

A roster editor for **NCAA College Football 2K3** (Nintendo GameCube, Game ID `GNAE8P`). Edit player ratings for all 7,091 players across 160 teams.

Modeled on the architecture and honesty standards of [cruuz/2k-football-mod-tools](https://github.com/cruuz/2k-football-mod-tools) (ESPN NFL 2K5 / APF 2K8).

## What this fixed drop improves

- Clearer status of what is verified vs research-boundary
- Desktop + core library remain the primary reliable path
- Team names for the first 124 teams + all-star teams are included
- Rating labels are statistically inferred (see `rating_names.json`) and marked unverified until confirmed in Dolphin

## Features

- **Team-based roster browsing** — 160 teams, players grouped by team
- **Player ratings editor** — Edit 16 ratings per player (0–99)
- **In-place ISO editing** — Modifies your ISO copy directly
- **Position / jersey number** editing
- **Appearance/equipment fields** (statistically identified, unverified)
- **Roster balancer** tool
- **Playbook** and **texture** research tools (explicitly research-preview)

## Requirements

- Python 3.8+
- PyQt5 (`pip install PyQt5`)
- Your own legally dumped NCAA College Football 2K3 (USA) GameCube ISO
- **Work on a COPY of your ISO, never the original**

## Usage

```bash
pip install PyQt5
python ncaa2k3_roster_editor_v2.py
# or
python ncaa2k3_roster_editor_v2.py /path/to/your/copy.iso
```

## Technical Details

### Format (Reverse-Engineered)

- **DAT archive** (`game.dat`): 1,212 files, 24-byte BE records
- **ROST database** (record 134): 1,232,576 bytes
  - Player section: 7,091 players × 148 bytes at ROST+0x248FD
  - Team section: 160 teams × 116 bytes at ROST+0x4E91
  - Team player counts: u8 at team record +114
  - Team names: UTF-16LE at ROST+0x129C13 (first 124 mapped)

### Ratings

Bytes 43–58 are the 16 player ratings. Statistical analysis across all 7,091 players shows clear position-specific distributions (CBs highest in Speed, LBs in Strength/Tackling, QBs in Throw Power/Accuracy, etc.). Labels in `rating_names.json` are inferred and **not yet confirmed in-game**.

### Capability boundary (cruuz-style honesty)

| Feature              | Status                  | Notes                                      |
|----------------------|-------------------------|--------------------------------------------|
| Ratings edit         | Editable (offline)      | Statistically verified offsets             |
| Position / number    | Editable                | Confirmed                                  |
| Team grouping        | Working                 | Uses player-count field                    |
| Team names           | Partial (124/160)       | Remaining show as “Team N”                 |
| Player names         | Display only (“QB #12”) | No licensed names in this game             |
| Appearance fields    | Research / unverified   | Small enums, labels are guesses            |
| Texture replacement  | Research preview        | Format guessed, hash-verified write path   |
| Playbook             | Research / partial      | Basic swap support                         |
| Emulator proof       | Pending                 | Dolphin runtime verification still needed  |

## Safety

- The tools ship **no game data**. You must supply your own legally dumped ISO.
- Always work on a **copy**. The editor will remind you.
- Texture tools refuse to write if the original hash does not match (fail-closed).

## Files in this drop

- `ncaa_rost.py` — Core library (DAT + ROST parser, Player/Team classes)
- `ncaa2k3_roster_editor_v2.py` — PyQt5 GUI editor
- `ncaa_balance_rosters.py` — Roster size balancer
- `team_names.txt` — Mapped team names
- `rating_names.json` — Inferred rating labels (edit to correct)

## License

For research and modding purposes with legally obtained copies of the game.

## Credits

- Format reverse-engineering and editor by Strider (Muse) / jtfresh90
- Architecture and honesty standard inspired by cruuz/2k-football-mod-tools
