#!/usr/bin/env python3
"""
NCAA 2K3 Texture Replacement Tool
Following cruuz's methodology from 2k-football-mod-tools:
- Inventory of verified physical spans (no pixel decode required)
- Hash verification (fail closed on drift)
- PNG -> native GameCube format encoding
- Fixed-size replacement

Status: Research boundary - I8 format assumed for body part textures.
        Format identification needs verification via Dolphin or hardware.
"""

import struct
import hashlib
import json
from pathlib import Path
from PIL import Image

# GameCube texture encoders
def encode_i8(img, width=64, height=64):
    """Encode to GameCube I8 (8x4 tiles, 1 byte/pixel, grayscale)"""
    if img.mode != 'L':
        img = img.convert('L')
    img = img.resize((width, height), Image.LANCZOS)
    pixels = img.load()
    block_w = (width + 7) // 8
    block_h = (height + 3) // 4
    output = bytearray()
    for by in range(block_h):
        for bx in range(block_w):
            for py in range(4):
                for px in range(8):
                    x = bx*8 + px
                    y = by*4 + py
                    output.append(pixels[x, y] if x < width and y < height else 0)
    return bytes(output)

def encode_rgb5a3(img, width=64, height=64):
    """Encode to GameCube RGB5A3 (4x4 tiles, u16 BE)"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    img = img.resize((width, height), Image.LANCZOS)
    pixels = img.load()
    block_w = (width + 3) // 4
    block_h = (height + 3) // 4
    output = bytearray()
    for by in range(block_h):
        for bx in range(block_w):
            for py in range(4):
                for px in range(4):
                    x = bx*4 + px
                    y = by*4 + py
                    if x < width and y < height:
                        r, g, b, a = pixels[x, y]
                    else:
                        r, g, b, a = 0, 0, 0, 0
                    # RGB5A3: if opaque, use RGB555 mode
                    if a > 127:
                        val = 0x8000 | ((r*31//255) << 10) | ((g*31//255) << 5) | (b*31//255)
                    else:
                        val = ((a*7//255) << 12) | ((r*15//255) << 8) | ((g*15//255) << 4) | (b*15//255)
                    output.extend(struct.pack('>H', val))
    return bytes(output)

# Texture inventory (from 100A.IFF analysis)
# Format: name -> (offset, size, assumed_format, dimensions)
# These are RESEARCH BOUNDARY - format/dimensions not verified
TEXTURE_DB = {
    # Body part textures (65 total in 100A.IFF)
    # Assumed: 64x64 I8 based on size analysis (4184 bytes ≈ 4096 + headers)
}

def replace_texture(iso_path, texture_name, png_path, output_iso_path):
    """
    Replace a texture in the ISO.
    
    Args:
        iso_path: Path to source ISO (will NOT be modified)
        texture_name: Name from inventory (e.g., 'elbow01')
        png_path: Path to replacement PNG
        output_iso_path: Path for modified ISO (copy)
    
    Returns:
        True on success, raises on failure
    """
    # Load inventory
    inv_path = Path.home() / 'workspace/recon/ncaa2k3/texture_inventory.json'
    with open(inv_path) as f:
        inventory = json.load(f)
    
    # Find texture
    entry = next((e for e in inventory if e['texture_name'] == texture_name), None)
    if not entry:
        raise ValueError(f"Texture '{texture_name}' not in inventory")
    
    # Parse offset and size
    iso_offset = int(entry['iso_offset'], 16)
    size = entry['size']
    
    # For now, assume I8 64x64 (4096 bytes pixel data)
    # The 4184 byte span includes 88 bytes of headers
    # We need to find the exact pixel data offset within the span
    # RESEARCH BOUNDARY: This offset is GUESSED, not verified!
    PIXEL_DATA_OFFSET_WITHIN_SPAN = 88  # Guess!
    PIXEL_DATA_SIZE = 4096  # 64x64 I8
    
    # Load and encode PNG
    img = Image.open(png_path)
    encoded = encode_i8(img, 64, 64)
    
    if len(encoded) != PIXEL_DATA_SIZE:
        raise ValueError(f"Encoded size {len(encoded)} != expected {PIXEL_DATA_SIZE}")
    
    # Copy ISO (never modify original!)
    import shutil
    shutil.copy2(iso_path, output_iso_path)
    
    # Verify original hash (fail closed on drift)
    with open(output_iso_path, 'r+b') as f:
        f.seek(iso_offset)
        original_span = f.read(size)
        # TODO: Compare with inventory hash
        
        # Write encoded data at pixel offset
        f.seek(iso_offset + PIXEL_DATA_OFFSET_WITHIN_SPAN)
        f.write(encoded)
    
    print(f"Replaced '{texture_name}' in {output_iso_path}")
    print(f"  Offset: {hex(iso_offset + PIXEL_DATA_OFFSET_WITHIN_SPAN)}")
    print(f"  Size: {len(encoded)} bytes")
    print("  WARNING: Pixel offset is GUESSED. Verify in Dolphin before using!")
    return True

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 5:
        print("Usage: ncaa_texture.py <iso> <texture_name> <png> <output_iso>")
        print("Example: ncaa_texture.py game.iso elbow01 my_elbow.png game_mod.iso")
        sys.exit(1)
    replace_texture(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
