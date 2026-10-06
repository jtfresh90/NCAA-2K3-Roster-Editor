#!/usr/bin/env python3
"""
ncaa_playbook_gui.py - 2K5-style playbook organizer GUI for NCAA 2K3.

Provides NFL 2K5-inspired playbook browsing:
- By Package (personnel grouping)
- By Formation  
- By Play Type

Categories are initial GUESSES based on index ranges (not verified).
Users can recategorize plays. Categories are saved per-team.
"""

import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QComboBox, QSplitter,
    QMessageBox, QFileDialog, QTabWidget
)
from PyQt5.QtCore import Qt

from playbook_categories import (
    PlaybookOrganizer, PACKAGES, FORMATIONS, PLAY_TYPES
)
from ncaa_playbook import read_playbook

class PlaybookWindow(QMainWindow):
    def __init__(self, iso_path=None):
        super().__init__()
        self.iso_path = iso_path
        self.organizer = None
        self.current_team = None
        
        self.setWindowTitle("NCAA 2K3 Playbook Organizer (2K5-Style)")
        self.setGeometry(100, 100, 900, 600)
        
        self.init_ui()
        
        if iso_path:
            self.load_teams()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Warning banner
        warn = QLabel(
            "⚠️ RESEARCH PREVIEW: Play categories are initial guesses based on "
            "index ranges, NOT verified from game data. Recategorize as needed."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("background: #fff3cd; padding: 8px; border-radius: 4px;")
        layout.addWidget(warn)
        
        # Team selector
        team_layout = QHBoxLayout()
        team_layout.addWidget(QLabel("Team:"))
        self.team_combo = QComboBox()
        self.team_combo.currentTextChanged.connect(self.on_team_changed)
        team_layout.addWidget(self.team_combo)
        
        self.load_btn = QPushButton("Load ISO")
        self.load_btn.clicked.connect(self.load_iso)
        team_layout.addWidget(self.load_btn)
        layout.addLayout(team_layout)
        
        # View mode tabs (2K5-style: By Package / By Formation)
        self.tabs = QTabWidget()
        
        # By Package tab
        self.package_list = QListWidget()
        self.package_list.itemClicked.connect(self.on_category_clicked)
        self.tabs.addTab(self.package_list, "By Package")
        
        # By Formation tab  
        self.formation_list = QListWidget()
        self.formation_list.itemClicked.connect(self.on_category_clicked)
        self.tabs.addTab(self.formation_list, "By Formation")
        
        # By Play Type tab
        self.type_list = QListWidget()
        self.type_list.itemClicked.connect(self.on_category_clicked)
        self.tabs.addTab(self.type_list, "By Play Type")
        
        # All Plays tab
        self.all_list = QListWidget()
        self.tabs.addTab(self.all_list, "All Plays")
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tabs)
        
        # Right panel: play details and recategorization
        right = QWidget()
        right_layout = QVBoxLayout(right)
        
        right_layout.addWidget(QLabel("Selected Play:"))
        self.play_label = QLabel("None")
        self.play_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.play_label)
        
        right_layout.addWidget(QLabel("Package:"))
        self.pkg_combo = QComboBox()
        self.pkg_combo.addItems(PACKAGES)
        right_layout.addWidget(self.pkg_combo)
        
        right_layout.addWidget(QLabel("Formation:"))
        self.form_combo = QComboBox()
        self.form_combo.addItems(FORMATIONS)
        right_layout.addWidget(self.form_combo)
        
        right_layout.addWidget(QLabel("Play Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(PLAY_TYPES)
        right_layout.addWidget(self.type_combo)
        
        self.apply_btn = QPushButton("Apply Category")
        self.apply_btn.clicked.connect(self.apply_category)
        right_layout.addWidget(self.apply_btn)
        
        right_layout.addStretch()
        
        self.save_btn = QPushButton("Save Categories")
        self.save_btn.clicked.connect(self.save_categories)
        right_layout.addWidget(self.save_btn)
        
        splitter.addWidget(right)
        splitter.setSizes([600, 300])
        layout.addWidget(splitter)
        
        self.selected_idx = None
    
    def load_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select NCAA 2K3 ISO", "", "ISO Files (*.iso)"
        )
        if path:
            self.iso_path = path
            self.load_teams()
    
    def load_teams(self):
        # Get list of PB files (team abbreviations)
        import struct
        with open(self.iso_path, 'rb') as f:
            f.seek(0xC5D68 + 0x71D2)
            name_data = f.read(60000)
            names = []
            start = 0
            for i in range(2000):
                end = name_data.find(b'\x00', start)
                if end == -1:
                    break
                names.append(name_data[start:end].decode('ascii', errors='ignore'))
                start = end + 1
                if len(names) >= 1212:
                    break
        
        pb_files = [n for n in names if '-PB.IFF' in n]
        teams = sorted([pb.replace('-PB.IFF', '') for pb in pb_files])
        
        self.team_combo.clear()
        self.team_combo.addItems(teams)
    
    def on_team_changed(self, team_abbr):
        if not team_abbr or not self.iso_path:
            return
        
        try:
            plays = read_playbook(self.iso_path, team_abbr)
            self.organizer = PlaybookOrganizer(team_abbr, plays)
            self.current_team = team_abbr
            self.refresh_views()
            
            # Try to load saved categories
            cat_file = Path(self.iso_path).parent / f"{team_abbr}.playbook.json"
            if cat_file.exists():
                with open(cat_file) as f:
                    data = json.load(f)
                    self.organizer = PlaybookOrganizer.from_dict(data)
                self.refresh_views()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load playbook: {e}")
    
    def refresh_views(self):
        if not self.organizer:
            return
        
        # By Package
        self.package_list.clear()
        for pkg in PACKAGES:
            plays = self.organizer.get_by_package(pkg)
            if plays:
                self.package_list.addItem(f"══ {pkg} ({len(plays)}) ══")
                for idx, play in plays:
                    self.package_list.addItem(f"  [{idx}] {play}")
        
        # By Formation
        self.formation_list.clear()
        for form in FORMATIONS:
            plays = self.organizer.get_by_formation(form)
            if plays:
                self.formation_list.addItem(f"══ {form} ({len(plays)}) ══")
                for idx, play in plays:
                    self.formation_list.addItem(f"  [{idx}] {play}")
        
        # By Type
        self.type_list.clear()
        for ptype in PLAY_TYPES:
            plays = self.organizer.get_by_type(ptype)
            if plays:
                self.type_list.addItem(f"══ {ptype} ({len(plays)}) ══")
                for idx, play in plays:
                    self.type_list.addItem(f"  [{idx}] {play}")
        
        # All Plays
        self.all_list.clear()
        for i, play in enumerate(self.organizer.plays):
            pkg, form, ptype = self.organizer.categories[i]
            self.all_list.addItem(f"[{i}] {play} - {pkg} / {form} / {ptype}")
    
    def on_category_clicked(self, item):
        text = item.text()
        # Parse [idx] from text
        if text.startswith("  ["):
            try:
                idx = int(text[3:text.index("]")])
                self.selected_idx = idx
                play = self.organizer.plays[idx]
                pkg, form, ptype = self.organizer.categories[idx]
                
                self.play_label.setText(f"[{idx}] {play}")
                self.pkg_combo.setCurrentText(pkg)
                self.form_combo.setCurrentText(form)
                self.type_combo.setCurrentText(ptype)
            except:
                pass
    
    def apply_category(self):
        if self.selected_idx is None or not self.organizer:
            return
        
        self.organizer.set_category(
            self.selected_idx,
            package=self.pkg_combo.currentText(),
            formation=self.form_combo.currentText(),
            play_type=self.type_combo.currentText()
        )
        self.refresh_views()
    
    def save_categories(self):
        if not self.organizer or not self.iso_path:
            return
        
        cat_file = Path(self.iso_path).parent / f"{self.current_team}.playbook.json"
        with open(cat_file, 'w') as f:
            json.dump(self.organizer.to_dict(), f, indent=2)
        
        QMessageBox.information(
            self, "Saved", 
            f"Categories saved to {cat_file.name}\n\n"
            "Note: This saves your organization, not the ISO.\n"
            "Use ncaa_playbook.py to modify the actual playbook."
        )


def main():
    app = QApplication(sys.argv)
    iso_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = PlaybookWindow(iso_path)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
