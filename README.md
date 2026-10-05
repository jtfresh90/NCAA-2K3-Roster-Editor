# NCAA College Football 2K3 Roster Editor

**Version 1.0.0** | GameCube | Python + PyQt5

A roster editor for **NCAA College Football 2K3** (Nintendo GameCube, Game ID `GNAE8P`). Edit player ratings for all 7,091 players across 160 teams. Modeled on the 2K football mod tools architecture.

## Features

- **Team-based roster browsing** — 160 teams, players grouped by team
- **Player ratings editor** — Edit 16 ratings per player (values 0-99)
- **In-place ISO editing** — Modifies your ISO copy directly, no rebuild needed
- **Auto-save** — Changes write through to the ISO immediately

## Requirements

- Python 3.8+
- PyQt5 (`pip install PyQt5`)
- Your own legally dumped NCAA College Football 2K3 (USA) GameCube ISO
- **Work on a COPY of your ISO, never the original!**

## Usage

```bash
# Install PyQt5
pip install PyQt5

# Run the editor (will prompt for ISO if not specified)
python ncaa2k3_roster_editor_v2.py

# Or specify ISO directly
python ncaa2k3_roster_editor_v2.py /path/to/your/copy.iso
```

## What You Can Edit

- **16 player ratings** per player (speed, strength, agility, etc. — exact labels TBD)
- Ratings are bytes 43-58 in each 148-byte player record
- Values 0-99 (game uses ~25-87 range)

## Technical Details

### Format (Reverse-Engineered)

- **DAT archive** (`game.dat`): 1,212 files, 24-byte BE records
- **ROST database** (record 134): 1,232,576 bytes
  - Player section: 7,091 players × 148 bytes at ROST+0x248FD
  - Team section: 160 teams × 116 bytes at ROST+0x4E91
  - Team player counts: u8 at team record +114
  - Team names: UTF-16LE at ROST+0x129C13 (152+ teams)

### Files

- `ncaa_rost.py` — Core library (DAT parser, ROST parser, Player/Team classes)
- `ncaa2k3_roster_editor_v2.py` — PyQt5 GUI editor

## Limitations (v1.0.0)

- Team names not yet mapped (displayed as "Team 0"–"Team 159")
- Player names encrypted (displayed as "Player N")
- Rating labels are guesses ("Rating 1"–"Rating 16", exact meanings TBD)
- Uniforms/textures and playbooks not yet supported (formats need RE)

## Verification Status

- ✅ Offline round-trip verified (read → modify → write → re-read)
- ✅ DAT integrity verified after edits
- ⏳ Emulator/runtime verification pending (Dolphin)

## License

This tool ships **no game data**. You must supply your own legally dumped ISO. For research and modding purposes.

## Credits

- Format reverse-engineering and editor by Strider (Muse)
- For Joshua (jtfresh90)
- Modeled on [cruuz/2k-football-mod-tools](https://github.com/cruuz/2k-football-mod-tools) architecture
