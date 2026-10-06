# Stadium Model Format Research — NCAA College Football 2K3 (GameCube)

**Date:** October 6, 2026  
**Status:** Structure mapped. Vertex extraction NOT achieved. Import-larger assessed as infeasible.  
**ISO:** Read-only analysis. No modifications made.

---

## 1. ENV File Inventory

9 environment files in the DAT archive:

| File | Variant guess |
|------|---------------|
| ENV_A_D.IFF / ENV_A_R.IFF / ENV_A_S.IFF | Arena — Day / Rain? / Snow? |
| ENV_D_D.IFF / ENV_D_R.IFF / ENV_D_S.IFF | Dome — Day / Rain? / Snow? |
| ENV_N_D.IFF / ENV_N_R.IFF / ENV_N_S.IFF | Night — Day / Rain? / Snow? |

(A/D/N = likely Arena/Dome/Night stadium types; D/R/S = likely Day/Rain/Snow weather. Unverified.)

Sizes observed:
- `ENV_A_D.IFF`: 1,143,596 bytes (1.1 MB) — DAT record 999 of 1212
- `ENV_A_R.IFF`: 2,702,144 bytes (2.7 MB) — starts with `RTXT` magic (texture data, not geometry)

The `_R` / `_S` variants starting with `RTXT` suggests each ENV "set" splits geometry (`_D`) from texture/sky data (`_R`, `_S`). Only the `_D` files were analyzed for geometry.

---

## 2. ENV_A_D.IFF Structure

### File header
```
Offset 0x00: 00 07 55 58 00 00 00 01 00 00 00 00 ...
```
Not a standard IFF header. Magic bytes `\x00\x07UX` are proprietary.

### TCRD chunk
Single occurrence at file offset `0x18`:
```
0x18: 54 43 52 44          "TCRD"
0x1C: 00 00 00 11          chunk size = 17
0x20: 00 00 00 1d          count = 29 (?)
      00 00 00 00 00 00 00 00
      44 69 72 65 63 ...    "Direc..." (start of "DirectorDBDebug")
```

TCRD is a table-of-contents / section-list chunk, **not** geometry. It points into the section structure below.

### DirectorDBDebug sections
4 sections, each prefixed by the ASCII string `DirectorDBDebug`:

| Section | File offset | Size | Notes |
|---------|-------------|------|-------|
| 0 | 0x2C | 0x75568 (480 KB) | Largest geometry candidate |
| 1 | 0x75594 | 0x16294 (91 KB) | |
| 2 | 0x8B828 | 0x44F4 (17 KB) | Smallest — config? |
| 3 | 0x8FD1C | 0x87610 (554 KB) | Largest — geometry candidate |

Each section header follows the pattern:
```
00 00 00 11  00 00 00 1d  00 00 00 00 00 00 00 00  "DirectorDBDebug"
```

After the string, section-specific binary data follows (e.g. section 0: `00 09 20 19 42 00 00 00 01 00 07 55 28 ...`).

### Vertex data status
- **No `ENCS` magic found** (unlike Xbox SCNE format — this is a different engine branch).
- 2,036 occurrences of BE float `1.0` — float data is present.
- An automated scan found 1,291 "float runs" in section 0, but spot-checks revealed these are largely zero-filled arrays and incidental patterns, **not** confirmed vertex positions.
- **Vertex positions have NOT been located.** The scene graph references vertex arrays indirectly; the descriptor format is unknown.

### What remains for export
1. Parse the DirectorDBDebug section header fully (what do the fields after the string mean?)
2. Identify vertex descriptor tables (GameCube typically uses float32 BE positions, but stride/layout unknown)
3. Identify index/topology buffers
4. Resolve scene-graph node transforms to world space
5. Map texture/material references to the RTXT data in sibling files

**Estimate:** Weeks of dedicated reverse-engineering, comparable in scope to the texture inventory project. Feasible, but not close.

---

## 3. Cruuz's Approach — What's Applicable

### 3a. Stadium import (`stadium_model_import.py`)
Cruuz's APF 2K8 stadium pipeline:
- **77 "statically proved" targets** in a private catalog (not a general importer)
- Export is **POSITION + expanded-triangle glTF**
- Import requires **exact source vertex count** and **exact expanded topology**
- **Rejects:** transforms, materials, skins, UV/normal edits, topology changes, animation, collision
- Delegates to a "copied-1A writer" with an independent verifier
- All non-POSITION bytes remain **byte-identical**

### 3b. Player import (`model_import.py`)
- `POSITION_FORMAT = "snorm16x4"` — Xbox SCNE stores positions as 16-bit signed normalized, **not** float32
- Source-bound manifest required; expanded triangles must match byte-for-byte
- **Compressed spans must fit in the original size.** From the B661 report: *"compressed span cannot fit at the +1%/+5% witnesses; upper-arm import is not enabled"* — if recompressed data doesn't fit, the import is **refused**, not expanded.

### 3c. Applicability to NCAA 2K3 GameCube
**None of cruuz's parsers apply directly:**
- Xbox uses SCNE chunks (4,616 inventoried); GameCube 2K3 uses TCRD/DirectorDBDebug — different format family
- Xbox positions are snorm16; GameCube positions are typically float32 BE — different encoding
- Cruuz's `apf_inner` / `apf_outer` / `apf_scene` modules are Xbox-XBE-specific
- Years of RE went into the Xbox SCNE format; the GameCube TCRD format has had ~1 day

**What transfers is the methodology, not the code:**
1. Same-count, same-topology, POSITION-only paired writer
2. Source-bound manifest with hashes
3. Independent verifier
4. Refuse (don't corrupt) when the edit doesn't fit

---

## 4. Feasibility Assessment

### Export stadium → glTF
| Aspect | Assessment |
|--------|------------|
| Format identified | **Partial** — sections mapped, vertex descriptors unknown |
| Effort | Weeks of RE (section headers → descriptors → arrays → transforms) |
| Blocker | None fundamental — it's uncompressed float data in a scene graph |
| Verdict | **Feasible with dedicated effort** |

### Import same-size POSITION edits (cruuz-style)
| Aspect | Assessment |
|--------|------------|
| Prerequisite | Working exporter + manifest system |
| Effort | Moderate once export works (paired writer + verifier) |
| Verdict | **Feasible after export**, following cruuz's proven boundary |

### Import larger/different-topology models ("even if larger")
| Aspect | Assessment |
|--------|------------|
| DAT expansion | ENV_A_D.IFF is record 999/1212 → growing it requires **moving 931 MB** and updating **212 DAT records** |
| Scene rebuild | DirectorDBDebug sections have internal offsets; growing geometry means rebuilding the section table and all internal pointers |
| Topology change | New vertex counts break every index buffer, strip restart, and material batch |
| Compression | If any span is compressed (cf. PLAYERS.IFF), recompressed output must fit or the scene must be relocated |
| Cruuz precedent | Explicitly refused — *"import is not enabled"* when spans don't fit |
| Verdict | **Not feasible.** This is rewriting the game's asset pipeline, not patching it. |

### PLAYERS.IFF (player models)
- 2.4 MB, first bytes `f8 0e fc 87`, 234/256 unique byte values in first KB
- **Not zlib.** Likely custom compression or encryption.
- Player model export is **blocked** until this is decrypted/decompressed.
- Separate RE project from stadium work.

---

## 5. What "Import Even If Larger" Would Actually Require

For the record, since the user explicitly asked:

1. **Full TCRD/DirectorDBDebug format spec** — every section header field, every descriptor, every offset
2. **DAT archive expander** — move 931 MB, update 212 records, verify no absolute offsets elsewhere break (save files? DOL hardcoded offsets?)
3. **Scene graph rewriter** — parse all 4 sections, rebuild with new geometry, fix internal pointers
4. **Index buffer regeneration** — new topology needs new triangle lists
5. **Material/texture remapping** — new model needs UVs; UVs reference the RTXT texture data
6. **In-game verification** — Dolphin testing for crashes, rendering glitches, physics/collision mismatches (collision is separate data; a visual-only import would have invisible walls in wrong places)

This is a **multi-month project** requiring GameCube GX expertise, not an incremental feature. Cruuz — with years of head start on the Xbox format — deliberately chose the same-topology POSITION-only boundary because arbitrary import is not tractable.

---

## 6. Recommendation

1. **Do not promise larger-model import.** It contradicts the only proven-safe methodology (cruuz's) and requires rewriting the asset pipeline.
2. **Stadium export (POSITION-only, same topology)** is the correct long-term goal, following cruuz's methodology adapted to the TCRD format.
3. **Next concrete step:** parse the DirectorDBDebug section headers — identify what the 16 bytes after each `DirectorDBDebug` string mean, then hunt for vertex descriptor tables.
4. **PLAYERS.IFF** needs a separate decryption/decompression effort before player models are touchable.
5. **DOL analysis** (the user's next priority) is independent of this work and should proceed in parallel.

---

## 7. Files Referenced

- `~/workspace/ncaa2k3-fix/ncaa_model.py` — framework (NotImplementedError stubs)
- `~/workspace/ncaa2k3-fix/docs/MODEL_RESEARCH.md` — prior research (Oct 5)
- `~/workspace/recon/2k-football-mod-tools/mod_editor/apf_studio/stadium_model_import.py` — cruuz stadium pipeline
- `~/workspace/recon/2k-football-mod-tools/mod_editor/apf_studio/model_import.py` — cruuz player pipeline
- `~/workspace/recon/2k-football-mod-tools/mod_editor/apf_studio/model_export.py` — cruuz export boundary
- `~/workspace/recon/2k-football-mod-tools/ASTRA_B661_MODELS_REPORT.md` — cruuz B661 model research
- ISO: `~/workspace/discs/ncaa2k3/NCAA College Football 2K3 (USA).nkit.iso` (read-only)
