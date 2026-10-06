#!/usr/bin/env python3
"""
ncaa2k3_roster_editor.py - PyQt5 GUI roster editor for NCAA College Football 2K3 (GameCube).

v2: Team grouping (160 teams). Players grouped by team using pos114 counts.
    Team names not yet mapped (displayed as Team 0-159).

Usage:
    python ncaa2k3_roster_editor.py <iso_path>
    
The editor works on the ISO directly (in-place edits). Make a backup copy first!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QSpinBox, QLabel, QPushButton,
    QSplitter, QMessageBox, QLineEdit, QGroupBox, QFormLayout,
    QFileDialog, QStatusBar, QComboBox
)
from PyQt5.QtCore import Qt

from ncaa_rost import RostEditor

# DEPRECATED: Ratings UI is disabled in v1.5.0+. Bytes 43-58 are NOT ratings.
# Kept as a constant for the disabled placeholder UI only.
RATING_COUNT = 16

# Rating names (best guess based on typical football game attributes)
RATING_NAMES = [
    "Rating 1 (SPD?)", "Rating 2 (STR?)", "Rating 3 (AGI?)", "Rating 4 (ACC?)",
    "Rating 5", "Rating 6", "Rating 7", "Rating 8",
    "Rating 9", "Rating 10", "Rating 11", "Rating 12",
    "Rating 13", "Rating 14", "Rating 15", "Rating 16",
]


class RosterEditorWindow(QMainWindow):
    def __init__(self, iso_path):
        super().__init__()
        self.iso_path = iso_path
        self.editor = None
        self.current_team_idx = -1
        self.current_player_idx = -1
        self.rating_spins = []
        
        self.setWindowTitle(f"NCAA 2K3 Roster Editor v2 - {os.path.basename(iso_path)}")
        self.setGeometry(100, 100, 1100, 700)
        
        self._load_roster()
        self._build_ui()
        self.statusBar().showMessage(f"Loaded {self.editor.team_count} teams, {self.editor.player_count} players")
    
    def _load_roster(self):
        try:
            self.editor = RostEditor(self.iso_path)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load ISO:\n{e}")
            sys.exit(1)
    
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Load team names if available
        self.team_names = {}
        team_names_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'team_names.txt')
        if os.path.exists(team_names_path):
            with open(team_names_path) as f:
                for line in f:
                    if ':' in line:
                        idx, name = line.strip().split(':', 1)
                        self.team_names[int(idx.strip())] = name.strip()
        
        # Top bar: team selector + save
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Team:"))
        self.team_combo = QComboBox()
        for i in range(self.editor.team_count):
            team = self.editor.get_team(i)
            name = self.team_names.get(i, f"Team {i}")
            self.team_combo.addItem(f"{name} ({team['player_count']} players)", i)
        self.team_combo.currentIndexChanged.connect(self._on_team_selected)
        top_bar.addWidget(self.team_combo)
        
        self.save_btn = QPushButton("Save All Changes")
        self.save_btn.clicked.connect(self._save_all)
        self.save_btn.setEnabled(False)
        top_bar.addWidget(self.save_btn)
        layout.addLayout(top_bar)
        
        # Main splitter: player list | ratings
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: player list for selected team
        self.player_list = QListWidget()
        self.player_list.itemSelectionChanged.connect(self._on_player_selected)
        splitter.addWidget(self.player_list)
        
        # Right: ratings editor
        ratings_widget = QWidget()
        ratings_layout = QVBoxLayout(ratings_widget)
        
        self.player_label = QLabel("Select a team, then a player")
        self.player_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        ratings_layout.addWidget(self.player_label)
        
        ratings_group = QGroupBox("Ratings (16 attributes)")
        form = QFormLayout(ratings_group)
        
        for i in range(RATING_COUNT):
            spin = QSpinBox()
            spin.setRange(0, 99)
            spin.setEnabled(False)
            spin.valueChanged.connect(self._on_rating_changed)
            self.rating_spins.append(spin)
            form.addRow(RATING_NAMES[i], spin)
        
        ratings_layout.addWidget(ratings_group)
        ratings_layout.addStretch()
        
        splitter.addWidget(ratings_widget)
        splitter.setSizes([350, 750])
        layout.addWidget(splitter)
        
        self.setStatusBar(QStatusBar())
        # Select first team
        self._on_team_selected(0)
    
    def _on_team_selected(self, index):
        if index < 0:
            return
        team_idx = self.team_combo.itemData(index)
        self.current_team_idx = team_idx
        team = self.editor.get_team(team_idx)
        team_name = self.team_names.get(team_idx, f"Team {team_idx}")
        
        # Populate player list
        self.player_list.clear()
        players = self.editor.get_team_players(team_idx)
        for p in players:
            # p.index is the global player index
            item = QListWidgetItem(f"Player {p.index} (ID: {p.player_id})")
            item.setData(Qt.UserRole, p.index)
            self.player_list.addItem(item)
        
        self.statusBar().showMessage(f"{team_name}: {len(players)} players")
        # Clear ratings
        self.current_player_idx = -1
        self.player_label.setText(f"{team_name} - Select a player")
        for spin in self.rating_spins:
            spin.setEnabled(False)
    
    def _on_player_selected(self):
        items = self.player_list.selectedItems()
        if not items:
            return
        idx = items[0].data(Qt.UserRole)
        self.current_player_idx = idx
        p = self.editor.get_player(idx)
        team_name = self.team_names.get(self.current_team_idx, f"Team {self.current_team_idx}")
        
        self.player_label.setText(f"{team_name}, {p.display_name} (ID: {p.player_id})")
        # Ratings are disabled in v1.5.0+ (bytes 43-58 are not ratings).
        # Keep the placeholder spinboxes disabled and at 0.
        for spin in self.rating_spins:
            spin.blockSignals(True)
            spin.setValue(0)
            spin.setEnabled(False)
            spin.blockSignals(False)
        
        self.save_btn.setEnabled(True)
    
    def _on_rating_changed(self):
        if self.current_player_idx < 0:
            return
        values = [spin.value() for spin in self.rating_spins]
        try:
            self.editor.set_player_ratings(self.current_player_idx, values)
            self.statusBar().showMessage(
                f"Player {self.current_player_idx} ratings updated", 2000
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save:\n{e}")
    
    def _save_all(self):
        QMessageBox.information(
            self, "Saved",
            f"All changes have been written to:\n{self.iso_path}\n\n"
            "Note: Edit the ISO copy, not your original!"
        )


def main():
    app = QApplication(sys.argv)
    
    if len(sys.argv) < 2:
        iso_path, _ = QFileDialog.getOpenFileName(
            None, "Select NCAA College Football 2K3 ISO",
            os.path.expanduser("~/workspace/discs"),
            "ISO Files (*.iso *.nkit.iso)"
        )
        if not iso_path:
            sys.exit(0)
    else:
        iso_path = sys.argv[1]
    
    if not os.path.exists(iso_path):
        QMessageBox.critical(None, "Error", f"File not found:\n{iso_path}")
        sys.exit(1)
    
    reply = QMessageBox.question(
        None, "Backup Reminder",
        f"You are about to edit:\n{iso_path}\n\n"
        "Are you working on a COPY (not your original dump)?",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.No:
        sys.exit(0)
    
    window = RosterEditorWindow(iso_path)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
