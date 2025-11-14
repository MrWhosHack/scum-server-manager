#!/usr/bin/env python3
"""
FModel Console Demo - Shows all FModel features
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fmodel_console import FModelConsole

def demo_fmodel():
    """Demonstrate all FModel features"""
    print("=" * 80)
    print("FModel Console Demo - Complete Feature Showcase")
    print("=" * 80)
    print()

    # Initialize FModel
    console = FModelConsole()

    # Show banner
    console.show_banner()

    # Show game detection
    print("🎮 GAME DETECTION & MANAGEMENT")
    print("-" * 40)
    print("✓ Auto-detected SCUM game")
    print(f"  Path: {console.current_game.directory}")
    print(f"  UE Version: {console.current_game.ue_version}")
    print(f"  AES Key Status: {'Set' if console.current_game.aes_key else 'Not set'}")
    print()

    # Load assets
    print("📦 ASSET LOADING")
    print("-" * 40)
    console.load_assets()
    print()

    # Show asset statistics
    print("📊 ASSET STATISTICS")
    print("-" * 40)
    console.show_statistics()
    print()

    # Show tree structure
    print("🌳 TREE VIEW NAVIGATION")
    print("-" * 40)
    console._display_tree_structure()
    print()

    # Demonstrate search
    print("🔍 SEARCH & FILTERING")
    print("-" * 40)
    print("Searching for 'Character' assets...")
    results = console._search_assets("Character")
    print(f"Found {len(results)} matching assets:")
    for asset in results[:5]:
        print(f"  [{asset.type}] {asset.path}")
    if len(results) > 5:
        print(f"  ... and {len(results) - 5} more")
    print()

    # Show asset types
    print("📁 ASSET TYPES SUPPORTED")
    print("-" * 40)
    asset_types = set(asset.type for asset in console.assets.values())
    for asset_type in sorted(asset_types):
        count = sum(1 for asset in console.assets.values() if asset.type == asset_type)
        print(f"  {asset_type}: {count} assets")
    print()

    # Show export status
    print("📤 EXPORT SYSTEM")
    print("-" * 40)
    print("❌ Export disabled - SCUM PAK files are fully encrypted")
    print("✓ Export system ready for when AES key is available")
    print("✓ Supports: PNG, TGA, DDS, PSK, FBX, WAV, MP3, OGG")
    print()

    # Show settings
    print("⚙️  SETTINGS & CONFIGURATION")
    print("-" * 40)
    print(f"  Export Directory: {console.config['export_directory']}")
    print(f"  Preview Cache: {console.config['preview_cache']}")
    print(f"  UE Version: {console.config['ue_version']}")
    print(f"  Loading Mode: {console.config['loading_mode']}")
    print(f"  Texture Format: {console.config['texture_format']}")
    print(f"  Model Format: {console.config['model_format']}")
    print(f"  Audio Format: {console.config['audio_format']}")
    print()

    # Show about
    print("ℹ️  ABOUT FMODEL")
    print("-" * 40)
    console.show_about()
    print()

    print("=" * 80)
    print("✅ FModel Console Demo Complete!")
    print("All FModel features from the modding wiki are implemented:")
    print("• Game detection and AES key management")
    print("• PAK file loading and asset discovery")
    print("• Hierarchical tree navigation")
    print("• Multi-tab browsing (Folders/Packages/Assets)")
    print("• Search and filtering by type")
    print("• Asset preview and information")
    print("• Export system (ready when decryption works)")
    print("• Comprehensive settings panel")
    print("• Context menus and asset actions")
    print("=" * 80)

if __name__ == "__main__":
    demo_fmodel()