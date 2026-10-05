# GameCube Texture Decoding - Research Update

**Date:** October 5, 2026  
**Status:** Format identified, decoder written, visual verification blocked.

## GameCube GX Texture Formats (from online research)

Based on documentation from Melee decomp project and tex_codec:

| Format | ID | Block | Coverage | Notes |
|--------|----|-------|----------|-------|
| I4 | 0 | 8 bytes | 8x8 | 4bpp, nibbles high-first |
| I8 | 1 | 32 bytes | 8x4 | 1 byte/texel |
| IA4 | 2 | 32 bytes | 8x4 | high nibble A, low I |
| IA8 | 3 | 32 bytes | 4x4 | A byte then I byte |
| RGB565 | 4 | 32 bytes | 4x4 | u16 BE |
| RGB5A3 | 5 | 32 bytes | 4x4 | u16 BE, dual-mode |
| RGBA8 | 6 | 64 bytes | 4x4 | AR planes then GB planes |
| CI4 | 8 | 32 bytes | 8x8 | palette indices |
| CI8 | 9 | 32 bytes | 8x4 | palette indices |
| CMPR | 14 | 32 bytes | 8x8 | 4 DXT1 sub-blocks |

**Key:** Tiles stored row-major. Dimensions rounded up to tile size.  
**Byte count** = blocks_x * blocks_y * block_size

## Decoder Implementation

Wrote Python decoder for RGB5A3 (most likely for UI/decals):
- 4x4 tiled blocks, 32 bytes per block
- u16 BE per pixel
- Bit 15 set: RGB555 opaque (5-5-5)
- Bit 15 clear: ARGB3444 (3-bit A, 4-4-4 RGB)
- Bit expansion via replication (not scaling)

Tested on 100H.IFF at offset 0x100:
- 32x32 decode produces 45 unique red values (plausible for real texture)
- Output written to /tmp/test_tex.ppm (PPM format, no PIL available)

## Blockers

1. **No PIL/Pillow**: Cannot install (disk full). Cannot visually verify decodes.
2. **Pixel data offset unknown**: ODUA data regions have headers; exact pixel start unclear.
3. **Dimensions unknown**: Need to find width/height in ODUA headers.
4. **Format unknown**: RGB5A3 is a guess; could be CMPR, IA8, etc.

## Next Steps

1. Free disk space, install Pillow for visual verification
2. Parse ODUA headers to find dimensions/format fields
3. Test multiple formats against known textures
4. Build texture inventory once format confirmed

## Sources

- Melee decomp: https://github.com/hexdump0/melee/blob/HEAD/native/AI/learnings/gx_textures.md
- tex_codec: https://github.com/hearhellacopters/tex_codec (GameCube/Wii GX support)
- miorom: https://github.com/miokotech/miorom (TPL texture converter)
