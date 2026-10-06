#!/usr/bin/env python3
"""
Texture editor dialog for NCAA 2K3 Roster Editor.

Lists textures from texture_inventory.json and allows replacement
with user-provided PNG files (encoded to GameCube format).

Status: Research preview - formats are inferred, not verified in-game.
"""

import os
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt


class TextureEditorDialog(QDialog):
    def __init__(self, iso_path, parent=None):
        super().__init__(parent)
        self.iso_path = iso_path
        self.setWindowTitle("NCAA 2K3 Texture Editor (Research Preview)")
        self.setGeometry(200, 200, 800, 500)
        
        self.inventory = self._load_inventory()
        self._build_ui()
        self._populate_table()
    
    def _load_inventory(self):
        """Load texture inventory from JSON."""
        # Try alongside this file, then in recon dir
        paths = [
            Path(__file__).parent / 'texture_inventory.json',
            Path.home() / 'workspace/ncaa2k3-fix/texture_inventory.json',
        ]
        for p in paths:
            if p.exists():
                with open(p) as f:
                    return json.load(f)
        return []
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Warning label
        warn = QLabel(
            "⚠️ RESEARCH PREVIEW: Texture formats are inferred, not verified in-game. "
            "Replacement may not display correctly. Work on a COPY!"
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #a00; font-weight: bold; padding: 5px;")
        layout.addWidget(warn)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Source File', 'Size', 'Format', 'Status'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.replace_btn = QPushButton("🔄 Replace Selected Texture...")
        self.replace_btn.clicked.connect(self._on_replace)
        btn_layout.addWidget(self.replace_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._populate_table)
        btn_layout.addWidget(self.refresh_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # Status
        self.status = QLabel(f"{len(self.inventory)} textures inventoried")
        layout.addWidget(self.status)
    
    def _populate_table(self):
        self.inventory = self._load_inventory()
        self.table.setRowCount(len(self.inventory))
        for i, tex in enumerate(self.inventory):
            self.table.setItem(i, 0, QTableWidgetItem(tex.get('texture_name', '?')))
            self.table.setItem(i, 1, QTableWidgetItem(tex.get('source_file', '?')))
            self.table.setItem(i, 2, QTableWidgetItem(str(tex.get('size', '?'))))
            self.table.setItem(i, 3, QTableWidgetItem(tex.get('format', 'unknown')))
            self.table.setItem(i, 4, QTableWidgetItem(tex.get('status', '?')))
        self.status.setText(f"{len(self.inventory)} textures inventoried")
    
    def _on_replace(self):
        """Replace selected texture with user PNG."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a texture first.")
            return
        
        tex = self.inventory[row]
        tex_name = tex.get('texture_name', '?')
        
        # Ask for PNG file
        png_path, _ = QFileDialog.getOpenFileName(
            self, f"Select PNG to replace '{tex_name}'",
            "", "PNG Images (*.png)"
        )
        if not png_path:
            return
        
        # Confirm (research preview warning)
        reply = QMessageBox.question(
            self, "Confirm Replacement",
            f"Replace '{tex_name}' ({tex.get('size')} bytes) with:\n{png_path}\n\n"
            f"Format: {tex.get('format', 'unknown')} (inferred, not verified)\n\n"
            "This is EXPERIMENTAL. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Import here to avoid circular imports
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from ncaa_texture import replace_texture
            
            # Output to new file (don't overwrite input)
            base = os.path.splitext(self.iso_path)[0]
            output_path = base + "_texmod.iso"
            
            replace_texture(self.iso_path, tex_name, png_path, output_path)
            
            QMessageBox.information(
                self, "Success",
                f"Texture replaced!\n\nOutput: {output_path}\n\n"
                "Test in Dolphin to verify the format was correct."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Replacement failed:\n{e}")
