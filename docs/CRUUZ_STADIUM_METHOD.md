# How Cruuz Does Stadium Export/Import — Methodology Reference

**Date:** October 6, 2026
**Source:** `~/workspace/recon/2k-football-mod-tools/` (cruuz's 2k-football-mod-tools, beta-75+)
**Purpose:** Understand cruuz's stadium pipeline so we can apply the same approach to NCAA 2K3 (GameCube).
**Status:** Research only. None of this is implemented for 2K3 yet.

---

## 1. The Big Picture

Cruuz's stadium pipeline has **two separate, independent tracks**:

| Track | What it edits | Format | Status |
|-------|--------------|--------|--------|
| **Texture import** | Stadium surface artwork (paint/colors) | PNG → native P8 palettized | Shipped, 477/477 scenes proven |
| **POSITION-only mesh import** | Vertex positions (move geometry) | glTF → native FLOAT3 lane | Shipped, 75–77 catalogued targets |

What he explicitly does **NOT** do:
- No UV editing (UVs are export-only, read for preview)
- No transform/node-matrix editing (ownership not proved)
- No topology changes (vertex count and faces must be identical)
- No material/shader editing
- No normal/tangent editing
- No collision editing
- No new-stadium authoring
- No archive expansion (ever)

The governing principle is: **refuse, don't corrupt**. If an edit can't fit the original fixed allocation, the import is rejected — the tool never grows an archive or alters container structure.

---

## 2. Export Process (step by step)

### 2a. Texture export

1. **Select a scene** in Mod Studio's Stadiums page (477 SCNE scenes catalogued for NFL 2K5; each has a canonical ID like `nfl2k5.stadium.o3280.c0005.scene2648.texture0002`).
2. **Export textured model** → produces a `.gltf` + `.bin` pair in a folder. The buffer contains:
   - Geometry (positions, indices) — unchanged source bytes
   - Decoded PNG images (one per texture occurrence)
   - **Source-derived UVs** — computed with the proved equation:
     ```
     u = normshort(register6.x) * shape[+0x30] + shape[+0x38]
     v = normshort(register6.y) * shape[+0x34] + shape[+0x3C]
     ```
     (Signed normalization: negative shorts ÷ 32768, non-negative ÷ 32767. No V flip.)
   - Canonical texture IDs on materials and images
   - A 0.01 unit root (centimetres → metres)
3. **Keep `.gltf` and `.bin` together** — they are a pair.

Key detail: the exporter **re-reads the source SCNE** and matches each cached shape ID, position count, and every position byte against the fresh source before binding UVs. This is a trust-but-verify step — the export refuses to proceed if the cache disagrees with the source.

### 2b. Mesh (POSITION) export

1. **Select one of the 75–77 catalogued targets** (e.g. `outer14.inner8.node0`). The catalog (`apf2k8_stadium_static_position_target_catalog.v1.json`, 456 KB, pinned by SHA-256) records for each target:
   - Exact vertex count
   - Vertex stream layout (stride, lane offsets, declarations: POSITION0 float32x3 BE at byte offset 0, TEXCOORD0 float16x4, NORMAL0 snorm10_10_10, TANGENT0 snorm16x4)
   - Index topology (component bits, triangle count, degenerate/restart info, topology SHA-256)
   - Draw records, hierarchy records, matrix slots — all hashed
2. **Export hand-off** → a `.gltf` + `.bin` containing **POSITION only** (FLOAT VEC3, non-normalized) plus the expanded triangle indices. No UVs, no normals, no materials, no skins, no animations.
3. The hand-off carries `extras` metadata: `apf2k8_target_id`, `apf_scene_node_index`, `source_position_sha256`, catalog SHA-256, and the schema version.
4. Export **never overwrites** an existing `.gltf`/`.bin`.

### 2c. Blender helper addon

`tools/blender/nfl2k5_stadium.py` (standard-library Python until bpy is injected):
- Registers **File → Import → NFL 2K5 Stadium** and **File → Export → NFL 2K5 Stadium textures**.
- Import uses Blender's **stock glTF importer**, packs images, retains source texture IDs and original dimensions on materials/images.
- Export saves **selected objects' texture materials** to a self-contained, **texture-only** `.gltf`. It **never passes re-exported meshes, transforms, or UVs** to a game writer.
- Critical: it copies **live painted pixels** into a temp image (`Image.copy()` alone can lose unsaved edits), preserves colour space/alpha, and cleans up temp files on failure.
- Materials must have exactly one Principled shader with the image connected directly to Base Color.
- Refusals: missing IDs, resized images, procedural materials, multi-scene selections, conflicting IDs, existing output filenames.

**Important lesson from the community add-on review** (`ASTRA_STADIUM_BLENDER_ADDONS_REPORT.md`): third-party Blender add-ons were **rejected** because an untouched round-trip changed 148,712 BIN bytes (wrong coordinate axes — Blender converts glTF `(x,y,z)` to `(x,-z,y)` and the add-on wrote Blender-local components directly). The stock importer path + cruuz's own helper is the only trusted route. Lesson: **never trust a round-trip you haven't byte-verified**.

---

## 3. Import Process (step by step)

### 3a. Texture import

1. In Blender, **paint at original dimensions**. Save the `.blend`.
2. Select objects → **File → Export → NFL 2K5 Stadium textures** → produces `stadium-textures.gltf` (textures + IDs only, no meshes).
3. In Mod Studio, select the **same scene** → **Import Blender textures** → open the helper file.
4. The Studio reader validates:
   - Document/buffer/image data bounded to 64 MiB
   - Material/texture/image ID carriers agree (explicit foreign ID never falls back to name matching)
   - All PNGs validated **before any mutation**
   - Identical pixels → `changed=False`, no writer call, no undo entry (no-op preservation)
5. **Compilation** (the core):
   - Generate complete mip chain (deterministic box filtering)
   - Quantize all mips together to one 256-entry palette
   - Regenerate P8 indices + platform swizzle
   - Write only the selected index-chain and palette allocations in decoded SCNE memory
   - **Losslessly recompress the whole SCNE into its original fixed stored span**
   - Preserve wrapper allocation and final opaque bytes exactly
6. **Fixed-span fit check**: the recompressed scene must fit its original compressed span **and** a loader-scratch bound (observed 3,120-byte cap). If it doesn't fit:
   - First, try **token filling**: replace early VC-LZ match tokens with equivalent literals to shrink the stream (accounts exactly for token/flag-byte costs)
   - If still too large → **clean refusal**. Previous edit set is restored intact.
7. One grouped undo action. Session manifest published only on success.

**No-op preservation** (added after the retail run exposed it): if the decoded scene is unchanged, the writer returns the **original compressed span, wrapper, padding, and opaque tail byte-for-byte** — it does not regenerate mips or reorder palettes.

### 3b. POSITION-only mesh import

1. Edit vertex positions in Blender **Edit Mode** (move vertices; do not add/delete).
2. Export the edited mesh as glTF (POSITION + indices only).
3. Run the import: `stadium_model_import.py import --game-dir … --reference-gltf … --target <id> --edited-gltf … --output-dir …`
4. The importer validates the glTF **strictly**:
   - Exactly one external buffer; URI must be a bare local filename
   - No duplicate JSON keys; no `NaN`/`Infinity` constants
   - POSITION must be non-normalized FLOAT VEC3; indices must be unsigned SCALAR
   - Mesh must have **exactly one** triangle primitive with **only** a POSITION attribute
   - All node transforms must be identity (translation `[0,0,0]`, rotation `[0,0,0,1]`, scale `[1,1,1]`) — "apply every object transform before stadium import"
   - No materials, textures, images, samplers, skins, animations in the document
   - Mesh identified by `extras.apf2k8_target_id` or `extras.apf_scene_node_index`
   - **Vertex count must exactly equal the catalogued count** (e.g. "requires exactly 1,234 vertices")
   - **Triangle indices must be byte-identical to the source reference** (`indices != source_indices` → refusal). This is the "expanded triangle topology must match exactly" rule.
   - Every POSITION component must be finite
5. The writer (`apf_stadium_catalog_position_patch.py`) then:
   - Loads the pinned catalog (size + SHA-256 checked)
   - Copies the source pack's `1A` physical allocation ("copied-1A writer")
   - Replaces **only** the FLOAT32x3_BE POSITION0 lane, in retail stream order
   - May not change count, topology, interleaves, attachment data, any sibling part, the fixed outer allocation, or any byte outside outer14
6. The **independent verifier** (`apf_stadium_catalog_position_verify.py`) then runs — see §4.

### What "POSITION-only" means technically

- The vertex record is interleaved: `[POSITION0 float32x3 BE (12B)][TEXCOORD0 float16x4 (8B)][NORMAL0 snorm10_10_10 (4B)][TANGENT0 snorm16x4 (8B)]` = 32-byte stride (example from catalog; actual strides vary).
- Import writes **only bytes 0–11 of each vertex record** (the POSITION0 lane). Bytes 12+ (UVs, normals, tangents) are preserved byte-identical.
- Index buffer, draw records, hierarchy, materials, node transforms, collision — all untouched.
- Net effect: you can **reshape** a surface (move the field's crown, raise a wall) but you cannot add detail, change texturing, or alter how the surface is rendered.

---

## 4. The Verifier

The verifier is a **separate program** that imports no writer code. It independently:

1. Parses the output pack with the pre-existing independent outer/IFF/H7A byte parser.
2. Loads the pinned hashes-only target catalog.
3. Re-derives the selected SCNE node/stream/lane from the catalog (not from the writer's internal state).
4. Checks **every changed decoded byte** — only the POSITION0 lane bytes may differ.
5. Reconstructs **every manifest field** from source bytes + recipe + output bytes.
6. Compares its independently derived manifest against the writer's manifest — **they must be identical** ("independent stadium verification returned a different manifest" → hard failure).

The manifest records: `changed_decoded_block0_byte_count`, source hashes, recipe hash, catalog hash, target ID, and a full claim-flags block that honestly states what is **not** proved (topology changes, rigid attachment, material/UV authoring, skin authoring, emulator/hardware runtime visibility, production mesh importer).

**Why two programs?** The writer could have a bug that the verifier would then share. Independent re-derivation from the catalog means a writer bug shows up as a manifest mismatch. This is the "paired writer + independent verifier" methodology.

**Scale of proof:** the texture track was proven across **477/477 scenes, 23,838 P8 texture occurrences, 43,639 meshes, 8,392,217 UV vertices**, with a 550 KB metadata-only proof JSON (hashes only, no game bytes). Retail acceptance ran as eight bounded batch processes.

---

## 5. Why Refuse Instead of Expand?

Three reasons, all load-bearing:

1. **Fixed allocation contract.** The game's loader allocates a fixed-size buffer for each compressed span and decompresses in place. A larger span would overflow the allocation → crash or memory corruption. The observed loader-scratch cap (3,120 bytes) is an empirical bound, not a tunable.
2. **Container integrity.** Growing one file means shifting every subsequent file in the archive and updating every record — for APF 2K8's packs this is hundreds of megabytes and thousands of records, each a new corruption risk. Cruuz's tools never copy or grow a pack; they write replacement spans into a project overlay and the build system assembles a new disc.
3. **Scope discipline.** "This is a fixed-allocation limit, not an authorization to grow archives or alter topology." Expansion would require rebuilding scene graphs, regenerating index buffers, remapping UVs/materials, and fixing collision — a multi-month asset-pipeline rewrite. The refuse boundary keeps the tool shippable and safe.

The practical consequence: photographic-detail texture replacements sometimes **cannot fit** (P8 palette + compression limits). The tool refuses cleanly and suggests simplifying the artwork. This is a feature, not a bug.

---

## 6. Tools Used

| Tool | Role |
|------|------|
| **Mod Studio (Qt/Python)** | Main app: scene browser, export/import UI, session/undo/project management |
| **Stock Blender glTF importer** | Import the exported hand-off into Blender (trusted; community add-ons rejected) |
| **`tools/blender/nfl2k5_stadium.py`** | Cruuz's own Blender helper: registers import/export menu entries, texture-only export |
| **glTF 2.0** | Interchange format for both texture and mesh hand-offs (.gltf + .bin) |
| **VC-LZ token parser/serializer** | Lossless recompression + token-filling to fit fixed spans |
| **Pinned SHA-256 catalogs** | `apf2k8_stadium_static_position_target_catalog.v1.json` (456 KB); every target's vertex count, stream layout, topology hash |
| **Paired writer + independent verifier** | `apf_stadium_catalog_position_patch.py` + `apf_stadium_catalog_position_verify.py` |
| **Metadata-only proof JSONs** | `nfl2k5_stadium_editor_retail_proof.json` (550 KB) — hashes, no game bytes, shareable |
| **Offscreen Qt tests** | 163 tests across 15 files, `QT_QPA_PLATFORM=offscreen`, bpy mocked |

---

## 7. What We'd Need to Replicate for NCAA 2K3 (GameCube)

### What transfers (methodology)
- **Paired writer + independent verifier** — the single most important pattern. Never ship a writer without a second program that re-derives everything from pinned hashes.
- **Refuse-don't-corrupt** — fixed-allocation boundary; clean refusal with the previous state intact.
- **No-op preservation** — unchanged data must round-trip byte-identical.
- **Catalog-driven targets** — pin every editable target's vertex count, stream layout, and topology hash in a versioned JSON before writing any importer.
- **glTF hand-off** — use stock Blender glTF import; write our own minimal exporter/helper; byte-verify every round-trip (the community add-on failure is the cautionary tale).
- **Metadata-only proofs** — share hashes and receipts, never game bytes.

### What changes (GameCube vs Xbox 360/PS3)
| Aspect | Cruuz (APF 2K8, Xbox 360 / NFL 2K5, Xbox) | NCAA 2K3 (GameCube) |
|--------|-------------------------------------------|---------------------|
| Container | SCNE chunks in archive packs 8/9; VC-LZ compression | DAT archive (24-byte records); ENV_*.IFF files; TCRD/DirectorDBDebug chunks; compression unknown |
| Vertex format | FLOAT32x3 **big-endian** POSITION0 in 32B interleaved records | Unknown — TCRD is a table-of-contents, not geometry; vertex lanes not yet located |
| Texture format | Xbox P8 (palettized, swizzled, mip-chained) | GameCube I4/I8/CMPR (RTXT chunks, fmt_id 12/4/14); tile-based (4×4, 8×4) |
| Texture compression | VC-LZ with token-fill trick | Unknown container compression for ENV/texture spans |
| Endianness | Big-endian throughout | Big-endian (GameCube is BE) — same |
| Scene graph | SCNE node/shape relocators, pinned function ranges | DirectorDBDebug sections (4 per ENV_D file); node ownership unproved |
| Toolchain | Mod Studio Qt app + Blender helper | Our PyQt5 editor + PWA; no Blender helper yet |

### Prerequisites for 2K3 (in order)
1. **Locate vertex data in ENV_D files.** TCRD points to DirectorDBDebug sections; float runs found so far are mostly zero-fill false positives. Next step per the existing research doc: parse the 16 bytes after each `DirectorDBDebug` string, then hunt vertex descriptors. Nothing else is possible until this is done.
2. **Decode the texture span compression** for ENV files (needed for texture import fit-checks).
3. **Build the pinned target catalog**: for each editable surface, record vertex count, stride, lane offsets, topology hash. Start with 1–3 surfaces, not 75.
4. **Write the POSITION-only writer + independent verifier** following cruuz's paired structure.
5. **glTF hand-off + Blender helper** for 2K3's coordinate conventions (GameCube vs Xbox axis handling must be byte-verified; do not assume).
6. **Fixed-span fit logic** for 2K3's compression (unknown until step 2).

### Honest feasibility note
Cruuz had years of head start, pinned retail function ranges (8 native code ranges replayed as evidence), and a hardware/Xemu witness pipeline. For 2K3 we have: the ENV structure mapped, vertex lanes **not** located, compression unknown, and no runtime witness setup. The texture track (RTXT I4/I8/CMPR replacement within fixed spans) is the nearer-term win — it mirrors what our `ncaa_texture.py` already attempts. The POSITION-only mesh track needs weeks of TCRD RE first. "Import even if larger" remains infeasible for the same three reasons in §5, compounded by 2K3's DAT archive (growing ENV_A_D.IFF means moving ~931 MB and updating 212 records, per the prior research).

---

## 8. Key Files in cruuz's Repo (for reference)

- `ASTRA_STADIUM_EDITOR_REPORT.md` — the r62 stadium editor build report (F1/F2/F3/F4, 477-scene proof)
- `ASTRA_STADIUM_BLENDER_ADDONS_REPORT.md` — why community add-ons were rejected (coordinate-axis bug)
- `docs/mod_editor/nfl2k5_stadium_blender_workflow.md` — the user-facing Blender workflow
- `docs/mod_editor/nfl2k5_stadium_texture_writer.md` — P8 texture writer admission contract + fixed-compression boundary
- `mod_editor/apf_studio/stadium_model_import.py` — the strict glTF import gate (all refusal conditions)
- `tools/apf_stadium_catalog_position_patch.py` — the fail-closed POSITION0 writer
- `tools/apf_stadium_catalog_position_verify.py` — the independent verifier
- `mod_editor/data/apf2k8_stadium_static_position_target_catalog.v1.json` — the 77-target pinned catalog
- `tools/blender/nfl2k5_stadium.py` — the Blender helper addon
