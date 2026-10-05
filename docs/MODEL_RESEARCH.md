# NCAA 2K3 Model Format Research

**Date:** October 5, 2026  
**Status:** Locations identified. Format parsing not yet achieved.

## Candidate Model Files

### Stadium/Environment Models
- `ENV_A_D.IFF` (1.1MB), `ENV_A_R.IFF` (2.7MB), `ENV_A_S.IFF` (2.6MB), `ENV_D_D.IFF` (2.7MB)
- Magic: `TCRD` (multiple chunks)
- Contains strings: "Director", "DirectorDBDebug"
- Structure: Scene graph, not raw vertices
- Likely the equivalent of 2K's SCNE (scene) format

### Player Models
- `PLAYERS.IFF` (2.4MB) - Header looks compressed/encrypted, no clear magics
- `PLAYERS.BIN` (17KB) - Too small for models, likely config
- `PLAYER9900.IFF` - Unknown

## 2K Mod's Approach (Stadium Studio)

From `mod_editor/apf_studio/model_export.py`:
- "Bounded private glTF round trips for APF's stock helmet and player body"
- "The paired importer can write same-count POSITION edits only"
- "Every other vertex lane and SCNE structure remains outside the authoring boundary"

The 2K mod:
1. Parses SCNE scene structures
2. Extracts vertex POSITION arrays
3. Exports to glTF
4. User edits positions in Blender (same vertex count!)
5. Imports back modified positions only

## GameCube Model Format Challenges

GameCube models use:
- Display lists (GX commands)
- Vertex arrays (positions, normals, UVs, colors)
- Multiple vertex formats (direct vs indexed)
- Matrix transformations

Parsing requires:
1. Understanding GX display list opcodes
2. Identifying vertex descriptor tables
3. Extracting position data from interleaved arrays
4. Reconstructing triangle indices

This is significantly more complex than texture containers.

## Next Steps

1. Parse TCRD chunk structure in ENV files
2. Identify vertex data within scene graph
3. Understand GX vertex format descriptors
4. Build glTF exporter (positions only, like 2K mod)
5. Build same-topology importer

## Recommendation

Model editing is a separate RE project comparable in scope to the texture work.
The texture pipeline (inventory → encode → replace) is ready pending format
verification. Model support should follow after textures are proven.
