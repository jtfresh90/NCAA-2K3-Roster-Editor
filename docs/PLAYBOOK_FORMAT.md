# NCAA 2K3 Playbook Format

**Date:** October 5, 2026  
**Status:** Index structure parsed. Play diagram format (ENCS) needs RE.

## Playbook Files

Each team has a playbook index file: `XXX-PB.IFF` (e.g., `AFA-PB.IFF` for Air Force)
- Size: ~1.2KB
- Contains: 132 null-terminated ASCII strings
- Format: List of play scene filenames (e.g., `S138.IFF`, `S139.IFF`, ...)

Example (AFA-PB.IFF):
- 132 entries: S138.IFF through S269.IFF (sequential)

## Play Scene Files

Individual plays: `S###.IFF` (e.g., `S138.IFF`)
- Size: ~2.4MB each
- Magic: `ENCS` (same as stadium ENV files!)
- Content: 3D play diagram scene data

The ENCS format is a scene graph containing:
- 3D models (player icons, field, arrows)
- Camera data
- Animation data (for play art)

## Editable Features (Proposed)

### Level 1: Playbook Index Editing (Achievable)
- Swap plays between teams
- Example: Give Alabama's playbook to Air Force
- Implementation: Overwrite the 132 strings in XXX-PB.IFF
- Risk: Low (fixed-size strings, simple format)

### Level 2: Play Diagram Editing (Hard)
- Modify the 3D play art in S###.IFF
- Requires: Full ENCS scene parser, vertex editing
- Status: Blocked on ENCS RE (same as stadium models)

## 2K Mod Comparison

The 2K football mod's playbook editor likely works at the index level too —
reordering and swapping plays, not redrawing the diagrams. Our Level 1
approach matches this methodology.

## Next Steps

1. Build playbook index parser (read 132 strings from XXX-PB.IFF)
2. Build playbook index writer (overwrite strings, verify size)
3. GUI for swapping plays between teams
4. ENCS scene parsing (future, blocked on model RE)
