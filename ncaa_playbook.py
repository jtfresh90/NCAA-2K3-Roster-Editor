#!/usr/bin/env python3
"""
ncaa_playbook.py - Playbook index editor for NCAA College Football 2K3 (GameCube).

Each team has a playbook file (XXX-PB.IFF) containing 132 play references.
This tool allows swapping plays between teams by editing the index.

Format:
- XXX-PB.IFF: 132 null-terminated ASCII strings (e.g., "S138.IFF")
- Each string is a reference to a play scene file (S###.IFF, ENCS format)
- Strings are variable length, file is ~1.2KB

Usage:
    python ncaa_playbook.py <iso> list <team_abbr>
    python ncaa_playbook.py <iso> swap <team1> <play_idx1> <team2> <play_idx2> <output_iso>
    python ncaa_playbook.py <iso> copy <src_team> <dst_team> <output_iso>

Example:
    python ncaa_playbook.py game.iso list AFA
    python ncaa_playbook.py game.iso swap AFA 0 ALA 5 game_mod.iso
"""

import struct
import sys
import shutil
from pathlib import Path

# Constants
DAT_MAGIC = b'DAT\x00'
ISO_DAT_OFF = 0xC5D68
DAT_DATA_BASE_OFF = 0x0C
DAT_RECORD_TABLE_OFF = 0x20
DAT_RECORD_SIZE = 24
PLAYBOOK_COUNT = 132  # plays per team

def find_dat_record(iso_path, filename):
    """Find a file in the DAT archive by name. Returns (dat_offset, size)."""
    with open(iso_path, 'rb') as f:
        # Read data base
        f.seek(ISO_DAT_OFF + DAT_DATA_BASE_OFF)
        data_base = struct.unpack('>I', f.read(4))[0]
        
        # Read name table to find index
        f.seek(ISO_DAT_OFF + 0x71D2)
        name_data = f.read(60000)
        names = []
        start = 0
        for i in range(2000):
            end = name_data.find(b'\x00', start)
            if end == -1:
                break
            names.append(name_data[start:end].decode('ascii', errors='ignore'))
            start = end + 1
            if len(names) >= 1212:
                break
        
        try:
            idx = names.index(filename)
        except ValueError:
            raise ValueError(f"File {filename} not found in DAT")
        
        # Read record
        f.seek(ISO_DAT_OFF + DAT_RECORD_TABLE_OFF + idx * DAT_RECORD_SIZE)
        rec = struct.unpack('>6I', f.read(24))
        size, end_offset = rec[0], rec[5]
        dat_offset = ISO_DAT_OFF + data_base + end_offset - size
        
        return dat_offset, size

def read_playbook(iso_path, team_abbr):
    """Read a team's playbook. Returns list of 132 play filenames."""
    filename = f"{team_abbr}-PB.IFF"
    offset, size = find_dat_record(iso_path, filename)
    
    with open(iso_path, 'rb') as f:
        f.seek(offset)
        data = f.read(size)
    
    # Parse null-terminated strings
    plays = []
    i = 0
    while len(plays) < PLAYBOOK_COUNT and i < len(data):
        if data[i] == 0:
            i += 1
            continue
        end = data.find(b'\x00', i)
        if end == -1:
            break
        try:
            s = data[i:end].decode('ascii').strip()
            if s:
                plays.append(s)
        except:
            pass
        i = end + 1
    
    return plays

def write_playbook(iso_path, team_abbr, plays, output_path):
    """Write a team's playbook. Plays must be list of 132 strings."""
    if len(plays) != PLAYBOOK_COUNT:
        raise ValueError(f"Expected {PLAYBOOK_COUNT} plays, got {len(plays)}")
    
    filename = f"{team_abbr}-PB.IFF"
    offset, size = find_dat_record(iso_path, filename)
    
    # Build new data (null-terminated strings)
    new_data = bytearray()
    for play in plays:
        new_data.extend(play.encode('ascii'))
        new_data.append(0)
    
    # Pad to original size (should be same if strings are same length)
    # Original uses fixed-size entries? Let's check
    # For now, require exact size match
    if len(new_data) > size:
        raise ValueError(f"New data {len(new_data)} exceeds original {size} bytes. "
                        "Play filenames must be same length.")
    
    # Pad with zeros
    new_data.extend(b'\x00' * (size - len(new_data)))
    
    # Copy ISO and write
    shutil.copy2(iso_path, output_path)
    with open(output_path, 'r+b') as f:
        f.seek(offset)
        f.write(new_data)
    
    print(f"Wrote {len(plays)} plays to {team_abbr} in {output_path}")

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    
    iso = sys.argv[1]
    cmd = sys.argv[2]
    
    if cmd == 'list':
        team = sys.argv[3]
        plays = read_playbook(iso, team)
        print(f"{team} playbook ({len(plays)} plays):")
        for i, play in enumerate(plays):
            print(f"  {i:3d}: {play}")
    
    elif cmd == 'swap':
        # swap <team1> <idx1> <team2> <idx2> <output>
        if len(sys.argv) != 8:
            print("Usage: ncaa_playbook.py <iso> swap <team1> <idx1> <team2> <idx2> <output>")
            sys.exit(1)
        t1, i1, t2, i2, out = sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6]), sys.argv[7]
        
        plays1 = read_playbook(iso, t1)
        plays2 = read_playbook(iso, t2) if t1 != t2 else plays1
        
        # Swap
        plays1[i1], plays2[i2] = plays2[i2], plays1[i1]
        
        # Write back (copy ISO first, then write both)
        shutil.copy2(iso, out)
        # Write t1
        filename1 = f"{t1}-PB.IFF"
        offset1, size1 = find_dat_record(iso, filename1)
        new_data1 = bytearray()
        for p in plays1:
            new_data1.extend(p.encode('ascii'))
            new_data1.append(0)
        new_data1.extend(b'\x00' * (size1 - len(new_data1)))
        with open(out, 'r+b') as f:
            f.seek(offset1)
            f.write(new_data1)
        
        if t1 != t2:
            filename2 = f"{t2}-PB.IFF"
            offset2, size2 = find_dat_record(iso, filename2)
            new_data2 = bytearray()
            for p in plays2:
                new_data2.extend(p.encode('ascii'))
                new_data2.append(0)
            new_data2.extend(b'\x00' * (size2 - len(new_data2)))
            with open(out, 'r+b') as f:
                f.seek(offset2)
                f.write(new_data2)
        
        print(f"Swapped {t1}[{i1}] <-> {t2}[{i2}] in {out}")
    
    elif cmd == 'copy':
        # copy <src> <dst> <output> - copy entire playbook
        if len(sys.argv) != 6:
            print("Usage: ncaa_playbook.py <iso> copy <src_team> <dst_team> <output>")
            sys.exit(1)
        src, dst, out = sys.argv[3], sys.argv[4], sys.argv[5]
        plays = read_playbook(iso, src)
        write_playbook(iso, dst, plays, out)
        print(f"Copied {src} playbook to {dst}")
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
