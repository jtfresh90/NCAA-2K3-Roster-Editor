#!/usr/bin/env python3
"""
ncaa_rost.py - Core library for NCAA College Football 2K3 (GameCube) roster editing.

Reverse-engineered format notes:
- game.dat is a Sega DAT archive with 24-byte BE records at +0x20
- ROST file (rec134): 1,232,576 bytes, contains roster database
- Player section: 7091 entries at ROST+0x248FD, 148 bytes each
- Player names: "QB #12" format (position + number, no licensed names)
  - Position: byte 31 (0=QB, 1=RB, 2=FB, 3=WR, 4=TE, 5=OT, 6=OG, 7=C,
               8=DT, 9=DE, 10=LB, 11=CB, 12=SS, 13=FS, 14=K, 15=P)
  - Jersey number: byte 18
- Team names: UTF-16LE at ROST+0x129C13+ (124 teams mapped)

CRITICAL CORRECTION (Oct 6 2026):
- Bytes 43-58 were previously misidentified as "16 ratings". They are
  actually an unknown 16-byte field (possibly encrypted data, checksum,
  or ID). The editor v1.0.0-v1.4.0 was corrupting this field, not ratings.
- Actual rating offsets are UNKNOWN. Candidate bytes 61-70 show rating-like
  values but no clean 16-byte block has been identified.
- DO NOT use RATING_OFF=43. Ratings are RESEARCH ONLY.

Status: v1.5.0 - QB #12 names correct. Ratings research-gated.
All offsets verified against NCAA College Football 2K3 (USA), Game ID GNAE8P.
"""

import struct
import os

# DAT archive constants (verified Oct 5 2026)
DAT_MAGIC = b'DAT\x00'
DAT_RECORD_SIZE = 24
DAT_RECORD_TABLE_OFF = 0x20
DAT_DATA_BASE_OFF = 0x0C  # u32be at +0x0C = data region start (0xA1E0)
DAT_NAME_TABLE_OFF = 0x71D2

# ROST file constants
ROST_MAGIC_LE = b'TSOR'  # 'ROST' as little-endian bytes
ROST_RECORD_NUM = 134
ROST_DAT_OFF = 0xC3D530
ROST_SIZE = 1232576

# Player section constants
PLAYER_SECTION_OFF = 0x248BD
PLAYER_HEADER_SKIP = 64  # zeros at start of section
PLAYER_REC_SIZE = 148
PLAYER_COUNT = 7091
PLAYER_BASE = PLAYER_SECTION_OFF + PLAYER_HEADER_SKIP  # 0x248FD

# Player name fields (QB #12 format - no licensed names due to NCAA rights)
POSITION_OFF = 31  # u8: 0=QB, 1=RB, 2=FB, 3=WR, 4=TE, 5=OT, 6=OG, 7=C,
                   #     8=DT, 9=DE, 10=LB, 11=CB, 12=SS, 13=FS, 14=K, 15=P
NUMBER_OFF = 18    # u8: jersey number (1-99)

POSITION_NAMES = ['QB', 'RB', 'FB', 'WR', 'TE', 'OT', 'OG', 'C',
                  'DT', 'DE', 'LB', 'CB', 'SS', 'FS', 'K', 'P']

# RATINGS: UNKNOWN - DO NOT USE
# Bytes 43-58 were misidentified as ratings in v1.0.0-v1.4.0.
# They are an unknown 16-byte field. Actual rating offsets not yet found.
# Candidate: bytes 61-70 show rating-like values but unverified.
# RATING_OFF = 43  # DEPRECATED - DO NOT USE - NOT RATINGS
# RATING_COUNT = 16

# Team section constants (160 entries at ROST+0x4E91, 116 bytes each)
TEAM_SECTION_OFF = 0x4E91
TEAM_REC_SIZE = 116
TEAM_COUNT = 160
TEAM_PLAYER_COUNT_OFF = 114  # u8 player count per team

# ISO constants for NCAA College Football 2K3 (USA)
ISO_DAT_OFF = 0xC5D68  # game.dat location in ISO


class DatArchive:
    """Parser for Sega DAT archive (game.dat)."""
    
    def __init__(self, data, base_offset=0):
        """
        data: bytes of the DAT file (or ISO)
        base_offset: offset of DAT start within data (0 if data is the DAT itself)
        """
        self.data = data
        self.base = base_offset
        if data[base_offset:base_offset+4] != DAT_MAGIC:
            raise ValueError("Not a DAT archive")
        self.data_base = struct.unpack('>I', data[base_offset+DAT_DATA_BASE_OFF:base_offset+DAT_DATA_BASE_OFF+4])[0]
        self.records = self._parse_records()
    
    def _parse_records(self):
        records = []
        off = self.base + DAT_RECORD_TABLE_OFF
        # Read until we hit the name table or invalid data
        # We know there are 1212 records from analysis
        for i in range(2000):  # safety limit
            if off + DAT_RECORD_SIZE > len(self.data):
                break
            rec = struct.unpack('>6I', self.data[off:off+DAT_RECORD_SIZE])
            size, field1, hash_id, z1, z2, end_offset = rec
            # Sanity check: end_offset should be reasonable
            if end_offset > 2_000_000_000 or (z1 != 0 or z2 != 0):
                # Might be name table start
                break
            start = self.data_base + end_offset - size
            end = self.data_base + end_offset
            records.append({
                'index': i,
                'size': size,
                'field1': field1,
                'hash_id': hash_id,
                'end_offset': end_offset,
                'dat_start': self.base + start,
                'dat_end': self.base + end,
            })
            off += DAT_RECORD_SIZE
            # Stop if next record looks like name table (ASCII)
            if off < len(self.data) and 32 <= self.data[off] < 127:
                # Check if it's the name table
                peek = self.data[off:off+16]
                if all(32 <= b < 127 or b == 0 for b in peek):
                    break
        return records
    
    def get_file(self, index):
        """Get file data by record index."""
        rec = self.records[index]
        return self.data[rec['dat_start']:rec['dat_end']]
    
    def get_file_offset(self, index):
        """Get (start, end) offsets of file in the underlying data."""
        rec = self.records[index]
        return (rec['dat_start'], rec['dat_end'])


class Player:
    """A single player record (148 bytes)."""
    
    def __init__(self, data, index):
        if len(data) != PLAYER_REC_SIZE:
            raise ValueError(f"Player record must be {PLAYER_REC_SIZE} bytes, got {len(data)}")
        self.data = bytearray(data)
        self.index = index
    
    @property
    def player_id(self):
        """Unique player ID (u32be at +4)."""
        return struct.unpack('>I', self.data[4:8])[0]
    
    @property
    def position(self):
        """Position code (u8 at +31): 0=QB, 1=RB, etc."""
        return self.data[POSITION_OFF]
    
    @property
    def position_name(self):
        """Position abbreviation (QB, RB, WR, etc.)."""
        pos = self.position
        return POSITION_NAMES[pos] if pos < len(POSITION_NAMES) else f"POS{pos}"
    
    @property
    def jersey_number(self):
        """Jersey number (u8 at +18)."""
        return self.data[NUMBER_OFF]
    
    @property
    def display_name(self):
        """Display name in 'QB #12' format (no licensed names)."""
        return f"{self.position_name} #{self.jersey_number}"
    
    # RATINGS: RESEARCH ONLY - DO NOT USE
    # The `ratings` property below is DEPRECATED and REMOVED.
    # Bytes 43-58 are NOT ratings. Actual rating offsets unknown.
    # See module docstring for details.
    
    def get_rating(self, idx):
        """Get a single rating (0-15). DEPRECATED - DO NOT USE."""
        raise NotImplementedError(
            "Ratings are disabled in v1.5.0+. Bytes 43-58 are not ratings."
        )
    
    def to_bytes(self):
        return bytes(self.data)


class RostDatabase:
    """Parser for the ROST roster database file."""
    
    def __init__(self, data):
        if data[0:4] != ROST_MAGIC_LE:
            raise ValueError("Not a ROST file (bad magic)")
        self.data = data
        self.players = self._parse_players()
        self.teams = self._parse_teams()
    
    def _parse_players(self):
        players = []
        for i in range(PLAYER_COUNT):
            off = PLAYER_BASE + i * PLAYER_REC_SIZE
            rec_data = self.data[off:off+PLAYER_REC_SIZE]
            players.append(Player(rec_data, i))
        return players
    
    def _parse_teams(self):
        """Parse 160 teams with player counts from team section."""
        teams = []
        player_idx = 0
        for i in range(TEAM_COUNT):
            off = TEAM_SECTION_OFF + i * TEAM_REC_SIZE
            # Player count is u8 at +114
            count = self.data[off + TEAM_PLAYER_COUNT_OFF]
            # Team IDs (u32be at +0, +4, +8)
            id1 = struct.unpack('>I', self.data[off:off+4])[0]
            id2 = struct.unpack('>I', self.data[off+4:off+8])[0]
            id3 = struct.unpack('>I', self.data[off+8:off+12])[0]
            teams.append({
                'index': i,
                'id1': id1,
                'id2': id2,
                'id3': id3,
                'player_start': player_idx,
                'player_count': count,
                'player_end': player_idx + count - 1,
            })
            player_idx += count
        # Adjust last team if needed (accounts for 7-player discrepancy)
        if player_idx < PLAYER_COUNT:
            remaining = PLAYER_COUNT - player_idx
            teams[-1]['player_count'] += remaining
            teams[-1]['player_end'] = PLAYER_COUNT - 1
        return teams
    
    def get_player(self, index):
        return self.players[index]
    
    def get_team(self, index):
        """Get team by index (0-159). Returns dict with player range."""
        return self.teams[index]
    
    def get_team_players(self, team_idx):
        """Get list of Player objects for a team."""
        team = self.teams[team_idx]
        return [self.players[i] for i in range(team['player_start'], team['player_end'] + 1)]
    
    def write_player(self, index):
        """Write a modified player record back to the data buffer."""
        # This is for in-memory; for ISO writing, use RostEditor
        off = PLAYER_BASE + index * PLAYER_REC_SIZE
        # Note: self.data is bytes, need bytearray for modification
        raise NotImplementedError("Use RostEditor for ISO writing")


class RostEditor:
    """
    High-level editor for NCAA 2K3 rosters in an ISO file.
    Works on a COPY of the ISO to avoid modifying the original.
    """
    
    def __init__(self, iso_path):
        self.iso_path = iso_path
        self.dat = None
        self.rost = None
        self._load()
    
    def _load(self):
        with open(self.iso_path, 'rb') as f:
            # Read DAT header to find ROST
            f.seek(ISO_DAT_OFF)
            magic = f.read(4)
            if magic != DAT_MAGIC:
                raise ValueError(f"DAT magic not found at ISO+0x{ISO_DAT_OFF:X}")
            # Parse DAT records to find ROST (rec134)
            # For efficiency, just compute the offset directly
            rost_iso_off = ISO_DAT_OFF + ROST_DAT_OFF
            f.seek(rost_iso_off)
            rost_data = f.read(ROST_SIZE)
            if rost_data[0:4] != ROST_MAGIC_LE:
                raise ValueError("ROST magic not found")
            self.rost = RostDatabase(rost_data)
            self.rost_iso_off = rost_iso_off
    
    def get_player(self, index):
        return self.rost.get_player(index)
    
    def set_player_rating(self, player_idx, rating_idx, value):
        """Set a player's rating and write through to the ISO. DEPRECATED."""
        raise NotImplementedError(
            "Ratings are disabled in v1.5.0+. Bytes 43-58 are not ratings."
        )
    
    def set_player_ratings(self, player_idx, values):
        """Set all 16 ratings for a player and write through to the ISO. DEPRECATED."""
        raise NotImplementedError(
            "Ratings are disabled in v1.5.0+. Bytes 43-58 are not ratings."
        )
    
    @property
    def player_count(self):
        return len(self.rost.players)
    
    @property
    def team_count(self):
        return len(self.rost.teams)
    
    def get_team(self, index):
        return self.rost.get_team(index)
    
    def get_team_players(self, team_idx):
        return self.rost.get_team_players(team_idx)


# Team names (extracted from ROST, UTF-16LE at 0x129C13)
# 124 names mapped to 160 team records (heuristic: first 124 in order)
# Remaining 36 teams show as "Team N"
TEAM_NAMES = [
    "Air Force",
    "Akron",
    "Ala. Birmingham",
    "Alabama",
    "Arizona",
    "Arizona State",
    "Arkansas",
    "Arkansas State",
    "Army",
    "Auburn",
    "Ball State",
    "Baylor",
    "Boise State",
    "Boston College",
    "Bowling Green State",
    "Buffalo",
    "California",
    "Central Florida",
    "Central Michigan",
    "Cincinnati",
    "Clemson",
    "Colorado",
    "Colorado State",
    "Connecticut",
    "Duke",
    "East Carolina",
    "Eastern Michigan",
    "Florida",
    "Florida State",
    "Fresno State",
    "Georgia",
    "Georgia Tech",
    "Hawaii",
    "Houston",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Iowa State",
    "Kansas",
    "Kansas State",
    "Kent State",
    "Kentucky",
    "Louisiana State",
    "Louisiana Tech",
    "Louisiana-Lafayette",
    "Louisiana-Monroe",
    "Louisville",
    "Marshall",
    "Maryland",
    "Memphis",
    "Miami",
    "Miami University",
    "Michigan",
    "Michigan State",
    "Middle Tennessee St.",
    "Minnesota",
    "Mississippi State",
    "Missouri",
    "Navy",
    "NC State",
    "Nebraska",
    "Nevada",
    "New Mexico",
    "New Mexico State",
    "North Carolina",
    "North Texas",
    "Northern Illinois",
    "Northwestern",
    "Notre Dame",
    "Ohio",
    "Ohio State",
    "Oklahoma",
    "Oklahoma State",
    "Ole Miss",
    "Oregon",
    "Oregon State",
    "Penn State",
    "Pittsburgh",
    "Purdue",
    "Rice",
    "Rutgers",
    "San Diego State",
    "San Jose State",
    "South Carolina",
    "South Florida",
    "Southern Miss",
    "Stanford",
    "Syracuse",
    "Temple",
    "Tennessee",
    "Texas",
    "Texas A&M",
    "Texas Tech",
    "Toledo",
    "Troy State",
    "Tulane",
    "Tulsa",
    "Utah",
    "Utah State",
    "Vanderbilt",
    "Virginia",
    "Virginia Tech",
    "Wake Forest",
    "Washington",
    "Washington State",
    "West Virginia",
    "Western Michigan",
    "Wisconsin",
    "Wyoming",
    "Chattanooga",
    "Eastern Illinois",
    "Furman",
    "Georgia Southern",
    "Montana",
    "Northern Iowa",
    "Samford",
    "SE Missouri State",
    "Southern Utah",
    "Weber State",
    "North All-Stars",
    "South All-Stars",
    "East All-Stars",
    "West All-Stars",
]

def get_team_name(index):
    """Get team name by index (0-159). Returns 'Team N' if not in list."""
    if 0 <= index < len(TEAM_NAMES):
        return TEAM_NAMES[index]
    return f"Team {index}"


def extract_rost_from_iso(iso_path, out_path):
    """Extract the ROST file from an ISO to a standalone file."""
    rost_iso_off = ISO_DAT_OFF + ROST_DAT_OFF
    with open(iso_path, 'rb') as fin:
        fin.seek(rost_iso_off)
        data = fin.read(ROST_SIZE)
    with open(out_path, 'wb') as fout:
        fout.write(data)
    return out_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: ncaa_rost.py <iso_path> [player_idx]")
        sys.exit(1)
    iso = sys.argv[1]
    editor = RostEditor(iso)
    print(f"Loaded {editor.player_count} players from {iso}")
    if len(sys.argv) >= 3:
        idx = int(sys.argv[2])
        p = editor.get_player(idx)
        print(f"Player {idx} (ID {p.player_id}): ratings = {p.ratings}")
    else:
        # Show first 5 players
        for i in range(5):
            p = editor.get_player(i)
            print(f"Player {i} (ID {p.player_id}): ratings = {p.ratings}")
