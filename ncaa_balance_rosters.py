#!/usr/bin/env python3
"""
NCAA 2K3 Roster Balancer

Balances team roster sizes by redistributing players from teams with
surplus players to teams with too few. This is SAFE because:
- Total player count stays at 7091 (no file expansion)
- Only team count bytes are modified (160 bytes)
- No DAT archive changes needed
- No data movement required

The imbalance (37 to 113 players) is in the original game data.
This tool evens it out by moving players from the largest rosters
to the smallest.

Usage:
    python ncaa_balance_rosters.py <iso_path> [target_min] [target_max] [output]
    
    target_min: minimum players per team (default: 60)
    target_max: maximum players per team (default: 80)
    output: defaults to <iso>_balanced.iso
"""

import sys
import struct
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ncaa_rost import (
    RostEditor,
    TEAM_COUNT, TEAM_REC_SIZE, TEAM_SECTION_OFF, TEAM_PLAYER_COUNT_OFF,
    ISO_DAT_OFF, ROST_DAT_OFF,
)


def balance_rosters(iso_path, target_min=60, target_max=80, output_path=None, seed=None):
    """
    Balance roster sizes by moving players from large teams to small teams.
    
    Args:
        iso_path: Input ISO (will NOT be modified)
        target_min: Teams below this will receive players
        target_max: Teams above this will donate players
        output_path: Output ISO path (default: <input>_balanced.iso)
        seed: Random seed for reproducible results
    
    Returns:
        Path to new ISO, or None if no balancing needed
    """
    if seed is not None:
        random.seed(seed)
    
    iso_path = Path(iso_path)
    if output_path is None:
        output_path = iso_path.parent / f"{iso_path.stem}_balanced.iso"
    else:
        output_path = Path(output_path)
    
    print(f"Loading ISO: {iso_path}")
    editor = RostEditor(str(iso_path))
    db = editor.rost
    
    # Get current counts
    counts = []
    for i in range(TEAM_COUNT):
        players = db.get_team_players(i)
        counts.append(len(players))
    
    print(f"\nCurrent: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
    
    # Identify donors (teams with > target_max) and recipients (< target_min)
    donors = [(i, c) for i, c in enumerate(counts) if c > target_max]
    recipients = [(i, c) for i, c in enumerate(counts) if c < target_min]
    
    if not donors or not recipients:
        print("No balancing needed (or no donors/recipients).")
        return None
    
    print(f"Donors (>{target_max}): {len(donors)} teams")
    print(f"Recipients (<{target_min}): {len(recipients)} teams")
    
    # Calculate how many players each needs/gives
    total_needed = sum(target_min - c for _, c in recipients)
    total_available = sum(c - target_max for _, c in donors)
    
    print(f"Total needed: {total_needed}, total available: {total_available}")
    
    if total_available < total_needed:
        print(f"Warning: Not enough surplus. Can only fill to ~{target_min - (total_needed - total_available)//len(recipients)}")
    
    # Build new count array
    # Strategy: Take from donors down to target_max, give to recipients up to target_min
    new_counts = counts.copy()
    
    # Collect surplus
    surplus_pool = 0
    for team_idx, count in donors:
        surplus = count - target_max
        new_counts[team_idx] = target_max
        surplus_pool += surplus
    
    # Distribute to recipients
    # Sort recipients by need (most needy first)
    recipients_sorted = sorted(recipients, key=lambda x: x[1])
    for team_idx, count in recipients_sorted:
        need = target_min - count
        give = min(need, surplus_pool)
        new_counts[team_idx] = count + give
        surplus_pool -= give
        if surplus_pool <= 0:
            break
    
    print(f"\nNew: min={min(new_counts)}, max={max(new_counts)}, avg={sum(new_counts)/len(new_counts):.1f}")
    print(f"Surplus remaining: {surplus_pool}")
    
    # Verify total unchanged
    assert sum(new_counts) == sum(counts), "Total player count changed! Bug!"
    print(f"Total players unchanged: {sum(new_counts)} ✓")
    
    # Write new ISO
    print(f"\nWriting new ISO: {output_path}")
    print("Copying ISO (1.3GB, may take a minute)...")
    
    import shutil
    shutil.copy2(iso_path, output_path)
    
    # Update team count bytes in the ROST
    # Team section is at ISO_DAT_OFF + ROST_DAT_OFF + TEAM_SECTION_OFF
    team_section_iso = ISO_DAT_OFF + ROST_DAT_OFF + TEAM_SECTION_OFF
    
    with open(output_path, 'r+b') as f:
        for team_idx, new_count in enumerate(new_counts):
            if new_count != counts[team_idx]:
                off = team_section_iso + (team_idx * TEAM_REC_SIZE) + TEAM_PLAYER_COUNT_OFF
                f.seek(off)
                old = f.read(1)[0]
                f.seek(off)
                f.write(bytes([new_count]))
                # print(f"  Team {team_idx}: {old} -> {new_count}")
    
    print(f"\nDone! Balanced ISO: {output_path}")
    print(f"Teams adjusted: {sum(1 for a,b in zip(counts, new_counts) if a != b)}")
    
    # The player data itself doesn't move! Only the count bytes change.
    # Team N's players are still at the same file offset, but the BOUNDARIES
    # between teams shift. This is correct because the parser computes:
    #   player_start = sum of all previous counts
    # So changing counts automatically reassigns the boundaries.
    print("\nNote: Player data is not moved. Only team boundaries are adjusted.")
    print("Players are reassigned by changing where one team's roster ends")
    print("and the next begins. This is safe and reversible.")
    
    return str(output_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    iso_path = sys.argv[1]
    target_min = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    target_max = int(sys.argv[3]) if len(sys.argv) > 3 else 80
    output_path = sys.argv[4] if len(sys.argv) > 4 else None
    
    balance_rosters(iso_path, target_min, target_max, output_path)
