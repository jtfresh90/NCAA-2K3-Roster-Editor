#!/usr/bin/env python3
"""
DOL Analyzer for NCAA College Football 2K3 (GameCube)
PowerPC disassembly and bug-hunting tools.

Usage:
    python dol_analyzer.py disasm <address> <count>
    python dol_analyzer.py search <bytes_hex>
    python dol_analyzer.py strings
"""

import sys
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

DOL_PATH = Path(__file__).parent / "dol" / "main.dol"

# DOL section info (from header)
# Text sections: 0-6, Data sections: 7-17
# We'll parse the header to get load addresses

def load_dol():
    """Load DOL and return (data, sections)."""
    with open(DOL_PATH, 'rb') as f:
        data = f.read()
    
    sections = []
    # Text sections (0-6): file offset at 0x00, load addr at 0x48, size at 0x90
    # Data sections (7-17): file offset at 0x1C, load addr at 0x64, size at 0xAC
    for i in range(7):
        file_off = struct.unpack('>I', data[i*4:i*4+4])[0]
        load_addr = struct.unpack('>I', data[0x48 + i*4:0x48 + i*4+4])[0]
        size = struct.unpack('>I', data[0x90 + i*4:0x90 + i*4+4])[0]
        if size > 0:
            sections.append(('text', i, file_off, load_addr, size))
    
    for i in range(11):
        file_off = struct.unpack('>I', data[0x1C + i*4:0x1C + i*4+4])[0]
        load_addr = struct.unpack('>I', data[0x64 + i*4:0x64 + i*4+4])[0]
        size = struct.unpack('>I', data[0xAC + i*4:0xAC + i*4+4])[0]
        if size > 0:
            sections.append(('data', i+7, file_off, load_addr, size))
    
    return data, sections

def addr_to_file_offset(addr, sections):
    """Convert memory address to file offset."""
    for typ, idx, file_off, load_addr, size in sections:
        if load_addr <= addr < load_addr + size:
            return file_off + (addr - load_addr)
    return None

def disasm_at(addr, count=20):
    """Disassemble at memory address."""
    data, sections = load_dol()
    file_off = addr_to_file_offset(addr, sections)
    if file_off is None:
        print(f"Address 0x{addr:X} not in any section")
        return
    
    md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    md.detail = False
    
    code = data[file_off:file_off + count*4]
    print(f"Disassembly at 0x{addr:X} (file offset 0x{file_off:X}):")
    for insn in md.disasm(code, addr):
        print(f"  0x{insn.address:08X}: {insn.mnemonic:10s} {insn.op_str}")

def search_bytes(hex_str):
    """Search for byte pattern in DOL."""
    data, sections = load_dol()
    pattern = bytes.fromhex(hex_str.replace(' ', ''))
    
    print(f"Searching for {pattern.hex()}...")
    found = []
    for typ, idx, file_off, load_addr, size in sections:
        section_data = data[file_off:file_off+size]
        pos = 0
        while True:
            pos = section_data.find(pattern, pos)
            if pos == -1:
                break
            addr = load_addr + pos
            found.append((addr, typ, idx))
            pos += 1
            if len(found) >= 20:
                break
        if len(found) >= 20:
            break
    
    for addr, typ, idx in found:
        print(f"  0x{addr:08X} ({typ} section {idx})")

def list_strings(min_len=6):
    """List ASCII strings in DOL (may contain debug info, bug messages)."""
    data, sections = load_dol()
    print("Searching for strings...")
    for typ, idx, file_off, load_addr, size in sections:
        if typ != 'data':
            continue
        section_data = data[file_off:file_off+size]
        i = 0
        while i < len(section_data):
            if 32 <= section_data[i] < 127:
                start = i
                while i < len(section_data) and 32 <= section_data[i] < 127:
                    i += 1
                s = section_data[start:i].decode('ascii', errors='ignore')
                if len(s) >= min_len and any(kw in s.lower() for kw in 
                    ['safety', 'block', 'kick', 'punt', 'error', 'bug', 'assert']):
                    addr = load_addr + start
                    print(f"  0x{addr:08X}: {s}")
            else:
                i += 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == 'disasm' and len(sys.argv) >= 4:
        addr = int(sys.argv[2], 16)
        count = int(sys.argv[3])
        disasm_at(addr, count)
    elif cmd == 'search' and len(sys.argv) >= 3:
        search_bytes(sys.argv[2])
    elif cmd == 'strings':
        list_strings()
    elif cmd == 'sections':
        data, sections = load_dol()
        print("DOL Sections:")
        for typ, idx, file_off, load_addr, size in sections:
            print(f"  {typ:4s} {idx:2d}: file 0x{file_off:06X}, mem 0x{load_addr:08X}, size 0x{size:X} ({size} bytes)")
    else:
        print(__doc__)
