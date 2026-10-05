"""
GameCube RGB5A3 texture encoder/decoder.

RGB5A3 format:
- 4x4 tiles, 2 bytes per pixel (u16 big-endian)
- Dual mode:
  - Bit 15 set: RGB555 opaque (5 bits per channel)
  - Bit 15 clear: ARGB3444 (3-bit alpha, 4 bits per channel)
- Tile layout: row-major, 4x4 blocks
"""

import struct
from PIL import Image


def encode(img, width=64, height=64):
    """
    Encode PIL Image to GameCube RGB5A3 tiled format.
    
    Args:
        img: PIL Image (will be converted to RGBA)
        width: Target width
        height: Target height
    
    Returns:
        bytes: Encoded RGB5A3 data
    """
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
                    x = bx * 4 + px
                    y = by * 4 + py
                    if x < width and y < height:
                        r, g, b, a = pixels[x, y]
                    else:
                        r, g, b, a = 0, 0, 0, 0
                    
                    if a > 127:
                        # Opaque: RGB555
                        val = 0x8000 | ((r * 31 // 255) << 10) | ((g * 31 // 255) << 5) | (b * 31 // 255)
                    else:
                        # Transparent: ARGB3444
                        val = ((a * 7 // 255) << 12) | ((r * 15 // 255) << 8) | ((g * 15 // 255) << 4) | (b * 15 // 255)
                    output.extend(struct.pack('>H', val))
    return bytes(output)


def decode(data, width, height):
    """
    Decode GameCube RGB5A3 tiled format to PIL Image.
    
    Args:
        data: Encoded RGB5A3 bytes
        width: Image width
        height: Image height
    
    Returns:
        PIL Image in 'RGBA' mode
    """
    img = Image.new('RGBA', (width, height))
    pixels = img.load()
    
    block_w = (width + 3) // 4
    block_h = (height + 3) // 4
    offset = 0
    
    for by in range(block_h):
        for bx in range(block_w):
            for py in range(4):
                for px in range(4):
                    if offset + 2 > len(data):
                        return img
                    val = struct.unpack('>H', data[offset:offset+2])[0]
                    offset += 2
                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= width or y >= height:
                        continue
                    
                    if val & 0x8000:
                        # Opaque RGB555
                        r = ((val >> 10) & 0x1F) * 255 // 31
                        g = ((val >> 5) & 0x1F) * 255 // 31
                        b = (val & 0x1F) * 255 // 31
                        a = 255
                    else:
                        # Transparent ARGB3444
                        a = ((val >> 12) & 0x7) * 255 // 7
                        r = ((val >> 8) & 0xF) * 255 // 15
                        g = ((val >> 4) & 0xF) * 255 // 15
                        b = (val & 0xF) * 255 // 15
                    pixels[x, y] = (r, g, b, a)
    return img
