# NCAA 2K3 Texture Format - ODUA Analysis Update

**Date:** October 5, 2026  
**Status:** Chunk structure mapped. Pixel format not yet identified.

## 100H.IFF Layout (12,288 bytes)

```
0x0000: ODUA header chunk (28 bytes)
  - Magic: ODUA
  - BE 6016 (data size?)
  - BE 192, BE 5824
  
0x001C: ODUA name chunk
  - Magic: ODUA
  - BE 17, BE 45
  - Name: "dclapaa1" (at +0x14)
  
0x003C: Data region (5,972 bytes)
  - Starts with "PADDING*" (16 bytes)
  - Headers: PADD, u32s, BE 5824, etc.
  - Pixel data offset unknown
  
0x1790: ODUA header chunk (second texture)
0x17AC: ODUA name chunk
  - Name: "oclapaa1"
  
0x17CC: Data region (second texture)
0x3000: End of file
```

## Texture Names Found

- `dclapaa1` - Likely "decal" texture
- `oclapaa1` - Unknown ("ocl" prefix)

The "dcl" prefix suggests these are decal textures (small logos, numbers), not full uniform textures.

## GameCube Texture Formats (to test)

Common GameCube formats:
- GX_TF_CMPR (0xE): S3TC compressed, 4x4 blocks, 8 bytes/block
- GX_TF_RGB5A3 (0x5): 16-bit, 2 bytes/pixel
- GX_TF_RGB565 (0x4): 16-bit, 2 bytes/pixel  
- GX_TF_IA8 (0x3): 16-bit, 2 bytes/pixel
- GX_TF_RGBA8 (0x6): 32-bit, 4 bytes/pixel (2x 16-bit)

For 5,972 byte data region:
- If CMPR: ~11,944 pixels → ~109x109 (not clean)
- If RGB5A3: 2,986 pixels → ~54x54 (not clean)
- Likely includes headers; actual pixel data smaller

## Next Steps

1. Find pixel data offset within data region (skip headers)
2. Try decoding as common GCN formats
3. Look for width/height in headers (BE u16)
4. Test with known texture (e.g., a simple logo)

## Model Formats

Not yet researched. Need to:
1. Find model files in DAT (likely .IFF or separate)
2. Identify format (GameCube display lists? Custom?)
3. 2K's Stadium Studio does glTF vertex edits; GCN equivalent unknown
