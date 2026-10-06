# ENCS Container Format — NCAA College Football 2K3 (GameCube)

**File:** FRONTEND.IFF (2.2MB at ISO+0xE30158)
**Date:** October 6, 2026
**Status:** Structure mapped. Material→pixel mapping NOT resolved. Textures NOT yet replaceable.
**ISO:** Read-only analysis. No modifications made.

---

## 1. Overview

FRONTEND.IFF uses the ENCS container format, distinct from the RTXT format used for player/uniform textures. It contains equipment materials (facemasks, mouthpieces, turf tape, socks, shoes, etc.) and UI elements.

ENCS is a multi-section container with a fundamentally different organization than RTXT:
- RTXT: Each texture is self-contained (name + format + dims + pixels in one chunk)
- ENCS: Names, metadata, and pixel data are separated into different sections

---

## 2. ENCS Chunk Structure

### 2.1 Chunk Header (16 bytes)

```
Offset  Size  Description
+0x00   4     Magic: "ENCS" (0x454E4353)
+0x04   4     Size1 (u32 BE) - total chunk data size
+0x08   4     Size2 (u32 BE) - duplicate of Size1
+0x0C   4     Unknown (always 0)
```

### 2.2 File Layout - 8 Chunks (4 Pairs)

FRONTEND.IFF contains 8 ENCS chunks forming 4 main+sub pairs:

| Offset   | Size      | Type | Description |
|----------|-----------|------|-------------|
| 0x000000 | 63,072    | Main | Headers, string table, metadata |
| 0x00001C | 1,732     | Sub  | Directory/index (13 = version?) |
| 0x00F670 | 1,863,584 | Main | 1.86MB - Float/matrix data + texture-like blocks |
| 0x00F68C | 34,748    | Sub  | Directory (only ~8 entries, not 68) |
| 0x1D6620 | 253,184   | Main | 253KB - Similar to section 2 |
| 0x1D663C | 6,552     | Sub  | Directory |
| 0x21E580 | 404,832   | Main | 404KB - Highest entropy, likely pixel data |
| 0x21E59C | 4,028     | Sub  | Directory |

### 2.3 Sub-chunk Pattern

All 4 sub-chunks share a consistent header pattern:

```
+0x00: 0
+0x04: (size - 16)  [1732→1716, 34748→34732, 6552→6536, 4028→4012]
+0x08: 0
+0x0C: 0
+0x10: 1 or 2       [type?]
+0x14: 113           [constant across all 4!]
+0x18: 0 or 2
+0x1C: 201 or 297    [201 in subs 1&4, 297 in subs 2&3]
```

The constant value 113 across all sub-chunks suggests a format version or shared reference, not per-texture data.

---

## 3. String Table (Section 1)

### 3.1 Location
File offsets 0x15000–0x16786 (within Section 1)

### 3.2 Contents
204 null-terminated ASCII strings, including:

**Source asset paths** (from artists' workstations):
```
W:/Artists/Eric/PS2Demo/sourceimages/10_socks_100_h.tga
W:/Artists/Eric/PS2Demo/sourceimages/helmet_reflect.tga
W:/Artists/Eric/PS2Demo/sourceimages/10_helmet.tga
...
```

**68 equipment material names:**
```
NUMBERS_R_stripe_DOUBLESIDED, NUMBERS_R_nostripe_DOUBLESIDED, ...
NUMBERS_M_stripe_DOUBLESIDED, ...
NUMBERS_L_stripe_DOUBLESIDED, ...
PLAYERNAME, SKIN_neck, LO_FACEMASK, HI_FACEMASK,
TURFTAPE, SOCKS, SHOE, MOUTHPIECE, HI_HELMET,
UNIF_sleeve_DOUBLESIDED, ...
```

**Bone/shape names** (skeleton?):
```
arm_doughy_L_armShape, arm_buff_L_armShape,
hand_push_L_armShape, hand_point_L_armShape, ...
```

### 3.3 Material Name Locations
- NUMBERS_R variants: 0x15111, 0x1512E, 0x1514D
- PLAYERNAME: 0x15207, 0x15223
- LO_FACEMASK: 0x15250
- TURFTAPE: 0x1534B
- SOCKS: 0x15396
- SHOE: 0x152C4, 0x153A8, 0x153C0
- MOUTHPIECE: 0x15416
- HI_HELMET: 0x15460, 0x15482
- SKIN_neck: 0x1523A

Materials appear 1-3 times each, all within the string table. They do NOT appear elsewhere in the file, indicating the mapping uses indices/offsets, not name strings.

---

## 4. Section Analysis

### 4.1 Section 2 (1.86MB @ 0xF670)
- First 1KB: Mostly zeros
- Contains 0x3F800000 (1.0f) float patterns - likely transform matrices
- At +0x10000: 33 unique bytes in 64B sample - mixed data
- At +0x100000: Pattern "98 98 aa ba aa aa" - suggests 4-bit or 8-bit grayscale texture data
- **Assessment:** Mixed metadata and texture data, not cleanly separated

### 4.2 Section 3 (253KB @ 0x1D6620)
- Similar characteristics to Section 2
- At +0x10000: "af af 00 b3 b3 b3" - texture-like patterns
- **Assessment:** Likely contains texture data

### 4.3 Section 4 (404KB @ 0x21E580)
- Highest entropy of all sections
- At +0x1000: 34 unique bytes, varied data
- At +0x10000: 35 unique bytes, high entropy
- **Assessment:** Most likely candidate for pixel data, but boundaries unclear

---

## 5. Comparison with RTXT

| Aspect | RTXT (Player Textures) | ENCS (Frontend) |
|--------|------------------------|-----------------|
| Organization | Self-contained chunks | Separated sections |
| Name location | In chunk header (+0x30 or +0x14) | Central string table |
| Format ID | At +0x40 or +0x3C (fmt_id) | Unknown |
| Dimensions | At +0x44/+0x48 or +0x2C/+0x30 | Unknown |
| Pixel data | Immediately follows header | In separate section |
| Mapping | Direct (name→data in one chunk) | Indirect (requires index table) |
| Replaceability | ✅ Yes (13,738 textures) | ❌ No (mapping unknown) |

---

## 6. Blockers for Texture Replacement

### 6.1 Unknown: Material Index → Pixel Data Mapping
The 68 materials are in the string table, but no clear directory maps them to pixel offsets. The sub-chunk "directories" contain only ~8 entries, not 68.

**Hypotheses:**
1. Materials are indexed implicitly by order (1st material = 1st texture in pixel section)
2. Mapping is in the float/matrix data (unlikely)
3. There's a separate index table not yet identified
4. Materials share textures (68 names → fewer actual textures)

### 6.2 Unknown: Pixel Format and Dimensions
Unlike RTXT which has explicit fmt_id and width/height fields, ENCS pixel data has no obvious headers. Format must be inferred from:
- Data size (if we can isolate a single texture)
- Visual inspection (decode as I8/IA8/RGB5A3 and see if it looks correct)
- Comparison with known sizes

### 6.3 Unknown: Section Boundaries
It's unclear which of the 3 pixel sections (2, 3, 4) contains the equipment textures, or if they're split across sections.

---

## 7. Next Steps for Full RE

1. **Identify texture boundaries:** Look for size patterns matching GameCube texture dimensions (4096=64×64 I8, 16384=128×128 I8, etc.)

2. **Correlate materials to data:** 
   - Count actual texture blocks in pixel sections
   - If count ≈ 68 (or fewer), try order-based mapping
   - Look for 68-entry tables elsewhere in the file

3. **Decode test:** Extract a candidate block, decode as I8, visually inspect for equipment-like patterns (numbers, facemask shapes)

4. **Cross-reference with RTXT:** The same materials (e.g., HI_HELMET) appear in both RTXT (HELMET.IFF, 226 textures) and ENCS. Compare to understand the relationship.

5. **Check DOL references:** The game code must reference these textures. Finding the loading code would reveal the expected format.

---

## 8. Recommendation

**Do NOT attempt replacement yet.** The mapping is unresolved, and writing to the wrong offset would corrupt the file.

The RTXT textures (13,863 inventoried) remain the safe target for replacement. ENCS requires the mapping work above before it's safe.

**Estimated effort:** 1-2 weeks of focused RE to resolve the mapping, assuming the format is logical. If it's obfuscated or compressed, longer.

---

## Appendix: Key Offsets

```
FRONTEND.IFF in ISO: 0xE30158
File size: ~2,300,000 bytes (2.2MB)

ENCS chunks:
  0x000000 (63,072)    - Headers + string table
  0x00001C (1,732)     - Sub: directory
  0x00F670 (1,863,584) - Main: mixed data
  0x00F68C (34,748)    - Sub: directory (~8 entries)
  0x1D6620 (253,184)   - Main: texture-like
  0x1D663C (6,552)     - Sub: directory
  0x21E580 (404,832)   - Main: high entropy (pixels?)
  0x21E59C (4,028)     - Sub: directory

String table: 0x15000-0x16786 (204 strings)
Material names: 0x15111-0x15500 (68 materials)
```
