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

from ncaa_rost import RostEditor, RATING_COUNT, RATING_NAMES, RATING_UNVERIFIED

# Rating names are loaded from rating_names.json (statistically inferred, unverified)
# Display with asterisk to indicate unverified status
def _display_rating_name(i):
    base = RATING_NAMES[i] if i < len(RATING_NAMES) else f"Rating {i+1}"
    return f"{base}*" if RATING_UNVERIFIED else base


class RosterEditorWindow(QMainWindow):
    def __init__(self, iso_path):
        super().__init__()
        self.iso_path = iso_path
        self.editor = None
        self.current_team_idx = -1
        self.current_player_idx = -1
        self.rating_spins = []
        self.nicknames = {}  # player_idx -> custom nickname (editor-side only)
        self._load_nicknames()
        
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
    
    def _nickname_path(self):
        """Sidecar JSON file for custom nicknames (next to the ISO)."""
        base = os.path.splitext(self.iso_path)[0]
        return base + ".nicknames.json"
    
    def _load_nicknames(self):
        """Load custom nicknames from sidecar file."""
        import json
        try:
            with open(self._nickname_path(), 'r') as f:
                data = json.load(f)
                # Keys are player indices as strings
                self.nicknames = {int(k): v for k, v in data.items()}
        except (FileNotFoundError, ValueError, KeyError):
            self.nicknames = {}
    
    def _save_nicknames(self):
        """Save custom nicknames to sidecar file."""
        import json
        try:
            with open(self._nickname_path(), 'w') as f:
                json.dump({str(k): v for k, v in self.nicknames.items()}, f, indent=2)
        except Exception as e:
            self.statusBar().showMessage(f"Failed to save nicknames: {e}", 3000)
    
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
        
        self.texture_btn = QPushButton("🎨 Textures...")
        self.texture_btn.clicked.connect(self._open_texture_editor)
        top_bar.addWidget(self.texture_btn)
        
        self.balance_btn = QPushButton("⚖️ Balance Rosters...")
        self.balance_btn.clicked.connect(self._open_roster_balancer)
        top_bar.addWidget(self.balance_btn)
        
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
        
        # Player info editor (position, number, nickname)
        info_group = QGroupBox("Player Info")
        info_form = QFormLayout(info_group)
        
        from ncaa_rost import POSITION_NAMES
        self.position_combo = QComboBox()
        self.position_combo.addItems(POSITION_NAMES)
        self.position_combo.setEnabled(False)
        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        info_form.addRow("Position:", self.position_combo)
        
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 99)
        self.number_spin.setEnabled(False)
        self.number_spin.valueChanged.connect(self._on_number_changed)
        info_form.addRow("Jersey #:", self.number_spin)
        
        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("Custom nickname (editor only)")
        self.nickname_edit.setEnabled(False)
        self.nickname_edit.editingFinished.connect(self._on_nickname_changed)
        info_form.addRow("Nickname:", self.nickname_edit)
        
        ratings_layout.addWidget(info_group)
        
        # Appearance/Equipment group (statistically identified, unverified)
        from ncaa_rost import Player
        appear_group = QGroupBox("Appearance/Equipment* (*=unverified)")
        appear_form = QFormLayout(appear_group)
        self.appear_spins = {}  # offset -> QSpinBox
        for offset, (name, min_v, max_v) in Player.APPEARANCE_FIELDS.items():
            spin = QSpinBox()
            spin.setRange(min_v, max_v)
            spin.setEnabled(False)
            spin.valueChanged.connect(lambda v, off=offset: self._on_appearance_changed(off, v))
            appear_form.addRow(f"{name} (+{offset}):", spin)
            self.appear_spins[offset] = spin
        ratings_layout.addWidget(appear_group)
        
        ratings_group = QGroupBox("Ratings (16 attributes)")
        form = QFormLayout(ratings_group)
        
        for i in range(RATING_COUNT):
            spin = QSpinBox()
            spin.setRange(0, 99)
            spin.setEnabled(False)
            spin.valueChanged.connect(self._on_rating_changed)
            self.rating_spins.append(spin)
            form.addRow(_display_rating_name(i), spin)
        
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
            nickname = self.nicknames.get(p.index, "")
            disp = f'"{nickname}" ' if nickname else ""
            item = QListWidgetItem(f"{disp}{p.display_name} (ID: {p.player_id})")
            item.setData(Qt.UserRole, p.index)
            self.player_list.addItem(item)
        
        self.statusBar().showMessage(f"{team_name}: {len(players)} players")
        # Clear player info and ratings
        self.current_player_idx = -1
        self.player_label.setText(f"{team_name} - Select a player")
        self.position_combo.setEnabled(False)
        self.number_spin.setEnabled(False)
        self.nickname_edit.setEnabled(False)
        self.nickname_edit.clear()
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
        
        nickname = self.nicknames.get(idx, "")
        disp = f'"{nickname}" ' if nickname else ""
        self.player_label.setText(f"{team_name}, {disp}{p.display_name} (ID: {p.player_id})")
        
        # Populate position, number, nickname
        self.position_combo.blockSignals(True)
        self.position_combo.setCurrentIndex(p.position)
        self.position_combo.setEnabled(True)
        self.position_combo.blockSignals(False)
        
        self.number_spin.blockSignals(True)
        self.number_spin.setValue(p.jersey_number)
        self.number_spin.setEnabled(True)
        self.number_spin.blockSignals(False)
        
        self.nickname_edit.blockSignals(True)
        self.nickname_edit.setText(nickname)
        self.nickname_edit.setEnabled(True)
        self.nickname_edit.blockSignals(False)
        
        ratings = p.ratings
        for i, spin in enumerate(self.rating_spins):
            spin.blockSignals(True)
            spin.setValue(ratings[i])
            spin.setEnabled(True)
            spin.blockSignals(False)
        
        # Populate appearance fields
        for offset, spin in self.appear_spins.items():
            spin.blockSignals(True)
            spin.setValue(p.get_appearance(offset))
            spin.setEnabled(True)
            spin.blockSignals(False)
        
        self.save_btn.setEnabled(True)
    
    def _on_appearance_changed(self, offset, value):
        if self.current_player_idx < 0:
            return
        try:
            p = self.editor.get_player(self.current_player_idx)
            p.set_appearance(offset, value)
            self.editor.write_player(self.current_player_idx)
            self.statusBar().showMessage(f"Appearance +{offset} set to {value}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set appearance:\n{e}")
    
    def _on_position_changed(self, pos_idx):
        if self.current_player_idx < 0:
            return
        try:
            self.editor.set_player_position(self.current_player_idx, pos_idx)
            # Refresh the player label and list item
            p = self.editor.get_player(self.current_player_idx)
            team_name = self.team_names.get(self.current_team_idx, f"Team {self.current_team_idx}")
            nickname = self.nicknames.get(self.current_player_idx, "")
            disp = f'"{nickname}" ' if nickname else ""
            self.player_label.setText(f"{team_name}, {disp}{p.display_name} (ID: {p.player_id})")
            # Update list item text
            for i in range(self.player_list.count()):
                item = self.player_list.item(i)
                if item.data(Qt.UserRole) == self.current_player_idx:
                    item.setText(f"{disp}{p.display_name} (ID: {p.player_id})")
                    break
            self.statusBar().showMessage(f"Position updated to {p.position_name}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update position:\n{e}")
    
    def _on_number_changed(self, number):
        if self.current_player_idx < 0:
            return
        try:
            self.editor.set_player_number(self.current_player_idx, number)
            p = self.editor.get_player(self.current_player_idx)
            team_name = self.team_names.get(self.current_team_idx, f"Team {self.current_team_idx}")
            nickname = self.nicknames.get(self.current_player_idx, "")
            disp = f'"{nickname}" ' if nickname else ""
            self.player_label.setText(f"{team_name}, {disp}{p.display_name} (ID: {p.player_id})")
            for i in range(self.player_list.count()):
                item = self.player_list.item(i)
                if item.data(Qt.UserRole) == self.current_player_idx:
                    item.setText(f"{disp}{p.display_name} (ID: {p.player_id})")
                    break
            self.statusBar().showMessage(f"Jersey number updated to #{number}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update number:\n{e}")
    
    def _on_nickname_changed(self):
        if self.current_player_idx < 0:
            return
        nickname = self.nickname_edit.text().strip()
        if nickname:
            self.nicknames[self.current_player_idx] = nickname
        else:
            self.nicknames.pop(self.current_player_idx, None)
        self._save_nicknames()
        # Refresh label and list
        p = self.editor.get_player(self.current_player_idx)
        team_name = self.team_names.get(self.current_team_idx, f"Team {self.current_team_idx}")
        disp = f'"{nickname}" ' if nickname else ""
        self.player_label.setText(f"{team_name}, {disp}{p.display_name} (ID: {p.player_id})")
        for i in range(self.player_list.count()):
            item = self.player_list.item(i)
            if item.data(Qt.UserRole) == self.current_player_idx:
                item.setText(f"{disp}{p.display_name} (ID: {p.player_id})")
                break
    
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
    
    def _open_texture_editor(self):
        """Open the texture editor dialog."""
        try:
            from ncaa_texture_gui import TextureEditorDialog
            dialog = TextureEditorDialog(self.iso_path, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open texture editor:\n{e}")
    
    def _open_roster_balancer(self):
        """Balance roster sizes across teams."""
        from PyQt5.QtWidgets import QInputDialog
        
        # Get target range
        min_val, ok1 = QInputDialog.getInt(
            self, "Balance Rosters",
            "Minimum players per team (teams below this receive players):",
            60, 37, 100, 1
        )
        if not ok1:
            return
        
        max_val, ok2 = QInputDialog.getInt(
            self, "Balance Rosters",
            "Maximum players per team (teams above this donate players):",
            80, min_val, 113, 1
        )
        if not ok2:
            return
        
        # Confirm
        reply = QMessageBox.question(
            self, "Confirm Balance",
            f"Balance rosters?\n\n"
            f"Teams with < {min_val} players will receive players\n"
            f"Teams with > {max_val} players will donate players\n\n"
            f"This modifies team roster boundaries (safe, reversible).\n"
            f"Output will be written to a new ISO file.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        try:
            from ncaa_balance_rosters import balance_rosters
            import os
            base = os.path.splitext(self.iso_path)[0]
            output_path = base + "_balanced.iso"
            
            result = balance_rosters(self.iso_path, min_val, max_val, output_path)
            if result:
                QMessageBox.information(
                    self, "Success",
                    f"Rosters balanced!\n\nOutput: {result}\n\n"
                    f"Reload the ISO to see the changes."
                )
            else:
                QMessageBox.information(self, "No Changes", "No balancing needed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Balancing failed:\n{e}")


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
