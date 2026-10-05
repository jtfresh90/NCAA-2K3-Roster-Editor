"""
GameCube I8 texture encoder/decoder.

I8 format:
- 8x4 tiles, 1 byte per pixel
- Grayscale intensity
- Tile layout: row-major, 8 wide x 4 tall blocks
"""

import struct
from PIL import Image


def encode(img, width=64, height=64):
    """
    Encode PIL Image to GameCube I8 tiled format.
    
    Args:
        img: PIL Image (will be converted to grayscale)
        width: Target width (default 64)
        height: Target height (default 64)
    
    Returns:
        bytes: Encoded I8 data (width * height bytes)
    """
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
                    x = bx * 8 + px
                    y = by * 4 + py
                    if x < width and y < height:
                        output.append(pixels[x, y])
                    else:
                        output.append(0)
    return bytes(output)


def decode(data, width, height):
    """
    Decode GameCube I8 tiled format to PIL Image.
    
    Args:
        data: Encoded I8 bytes
        width: Image width
        height: Image height
    
    Returns:
        PIL Image in 'L' mode
    """
    img = Image.new('L', (width, height))
    pixels = img.load()
    
    block_w = (width + 7) // 8
    block_h = (height + 3) // 4
    offset = 0
    
    for by in range(block_h):
        for bx in range(block_w):
            for py in range(4):
                for px in range(8):
                    if offset >= len(data):
                        return img
                    val = data[offset]
                    offset += 1
                    x = bx * 8 + px
                    y = by * 4 + py
                    if x < width and y < height:
                        pixels[x, y] = val
    return img
