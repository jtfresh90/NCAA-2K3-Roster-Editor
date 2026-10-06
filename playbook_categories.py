#!/usr/bin/env python3
"""
playbook_categories.py - 2K5-style playbook organization for NCAA 2K3.

NFL 2K5 organizes plays by:
- Package (personnel grouping): Pro, Twins, Spread, Ace, Jumbo, etc.
- Formation: I-Form, Shotgun, Singleback, etc.
- Play Type: Run, Pass, Play Action, Special Teams

Since 2K3's S###.IFF play files don't have descriptive names yet
(ENCS format not fully decoded), this module provides:
1. Index-based initial categorization (RESEARCH - unverified)
2. User-customizable categories
3. 2K5-style browsing interface

The categories are stored per-team and can be edited.
"""

# 2K5-style packages (personnel groupings)
PACKAGES = [
    "Pro",      # HB, FB, TE, 2 WR
    "Twins",    # HB, FB, TE, 2WR (both on same side)
    "Spread",   # HB, FB, 3 WR
    "Ace",      # HB, 2 TE, 2 WR
    "Jumbo",    # 3 backs, 2 TE
    "Kings",    # HB, TE, 3 WR
    "5 Wide",   # 5 WR
    "Empty",    # HB split wide
    "Goal Line",
    "Special Teams",
]

# 2K5-style formations
FORMATIONS = [
    "I-Form",
    "Strong I",
    "Weak I", 
    "Split Backs",
    "Singleback",
    "Shotgun",
    "Pistol",
    "Wildcat",
    "Goal Line",
    "Punt",
    "Field Goal",
    "Kickoff",
]

# Play types
PLAY_TYPES = [
    "Inside Run",
    "Outside Run", 
    "Option",
    "Short Pass",
    "Medium Pass",
    "Deep Pass",
    "Play Action",
    "Screen",
    "Draw",
    "Special Teams",
]

# Initial index-based categorization (RESEARCH - NOT VERIFIED)
# Based on typical football playbook structure:
# - Early indices: likely base offensive plays
# - Middle indices: likely passing plays  
# - Late indices: special teams, etc.
# 
# WARNING: These are GUESSES. The actual play types are in the ENCS
# files which haven't been fully decoded. Users should verify and
# recategorize as needed.

def get_initial_category(play_index, total_plays=132):
    """
    Get initial category guess for a play by index.
    Returns (package, formation, play_type) tuple.
    
    THIS IS A RESEARCH GUESS - NOT VERIFIED.
    """
    # Last ~10 plays are often special teams / non-play files
    if play_index >= total_plays - 10:
        return ("Special Teams", "Special Teams", "Special Teams")
    
    # First third: likely run-heavy base formations
    if play_index < 44:
        pkg = PACKAGES[play_index % 5]  # Cycle through base packages
        form = FORMATIONS[play_index % 6]  # I-Form, Strong I, etc.
        ptype = PLAY_TYPES[play_index % 3]  # Inside/Outside/Option
        return (pkg, form, ptype)
    
    # Middle third: likely passing plays
    elif play_index < 88:
        pkg = PACKAGES[(play_index % 5) + 2]  # Spread-oriented
        form = FORMATIONS[(play_index % 4) + 4]  # Shotgun, Singleback, etc.
        ptype = PLAY_TYPES[(play_index % 5) + 3]  # Short/Medium/Deep/PA/Screen
        return (pkg, form, ptype)
    
    # Last third (before special teams): mixed
    else:
        pkg = PACKAGES[play_index % len(PACKAGES)]
        form = FORMATIONS[play_index % len(FORMATIONS)]
        ptype = PLAY_TYPES[play_index % len(PLAY_TYPES)]
        return (pkg, form, ptype)


class PlaybookOrganizer:
    """Manages 2K5-style organization of a team's playbook."""
    
    def __init__(self, team_abbr, plays):
        """
        Args:
            team_abbr: Team abbreviation (e.g., "AFA")
            plays: List of 132 play filenames (e.g., ["S138.IFF", ...])
        """
        self.team_abbr = team_abbr
        self.plays = plays
        # categories[play_idx] = (package, formation, play_type)
        self.categories = {}
        for i in range(len(plays)):
            self.categories[i] = get_initial_category(i, len(plays))
    
    def set_category(self, play_idx, package=None, formation=None, play_type=None):
        """Update category for a play."""
        pkg, form, ptype = self.categories[play_idx]
        if package is not None:
            pkg = package
        if formation is not None:
            form = formation
        if play_type is not None:
            ptype = play_type
        self.categories[play_idx] = (pkg, form, ptype)
    
    def get_by_package(self, package):
        """Get all plays in a package."""
        return [(i, self.plays[i]) for i in range(len(self.plays))
                if self.categories[i][0] == package]
    
    def get_by_formation(self, formation):
        """Get all plays in a formation."""
        return [(i, self.plays[i]) for i in range(len(self.plays))
                if self.categories[i][1] == formation]
    
    def get_by_type(self, play_type):
        """Get all plays of a type."""
        return [(i, self.plays[i]) for i in range(len(self.plays))
                if self.categories[i][2] == play_type]
    
    def to_dict(self):
        """Serialize to dict for JSON storage."""
        return {
            'team': self.team_abbr,
            'plays': self.plays,
            'categories': {str(k): list(v) for k, v in self.categories.items()}
        }
    
    @classmethod
    def from_dict(cls, data):
        """Deserialize from dict."""
        org = cls(data['team'], data['plays'])
        org.categories = {int(k): tuple(v) for k, v in data['categories'].items()}
        return org
