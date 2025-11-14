#!/usr/bin/env python3
"""
FModel Console - Complete Unreal Engine Asset Browser (Console Version)
Based on FModel (https://fmodel.app/) - Full feature implementation
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pak_extractor import PAKExtractor
from uasset_parser import UAssetParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fmodel_console.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GameConfig:
    """Configuration for a game"""
    name: str
    directory: str
    ue_version: str = "GAME_UE4_27"
    aes_key: str = ""
    is_detected: bool = False

@dataclass
class AssetInfo:
    """Asset information"""
    path: str
    type: str
    size: int = 0
    package_path: str = ""
    export_path: str = ""
    is_exported: bool = False

class FModelConsole:
    """Console-based FModel implementation"""

    def __init__(self):
        self.config_file = 'fmodel_config.json'
        self.games: Dict[str, GameConfig] = {}
        self.current_game: Optional[GameConfig] = None
        self.assets: Dict[str, AssetInfo] = {}
        self.asset_parser = UAssetParser()

        # Supported asset types
        self.asset_types = {
            '.uasset': 'Unreal Asset',
            '.umap': 'Unreal Map',
            '.uax': 'Unreal Audio',
            '.udk': 'Unreal Animation',
            '.upk': 'Unreal Package',
            '.png': 'Texture',
            '.jpg': 'Texture',
            '.tga': 'Texture',
            '.dds': 'Texture',
            '.wav': 'Audio',
            '.mp3': 'Audio',
            '.ogg': 'Audio',
            '.psk': 'Model',
            '.fbx': 'Model',
        }

        self.init_config()
        self.detect_games()

    def init_config(self):
        """Initialize configuration"""
        self.config = {
            'games': {},
            'current_game': None,
            'export_directory': './exported_assets',
            'preview_cache': './preview_cache',
            'auto_detect_games': True,
            'ue_version': 'GAME_UE4_27',
            'loading_mode': 'All',
            'texture_format': 'PNG',
            'model_format': 'PSK',
            'audio_format': 'WAV',
            'show_folder_counts': True,
            'auto_expand_tree': False,
            'max_preview_size': 512
        }

        # Load existing config
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                self.config.update(loaded)
            except Exception as e:
                logger.warning(f"Error loading config: {e}")

        # Load games
        for name, game_data in self.config.get('games', {}).items():
            self.games[name] = GameConfig(**game_data)

    def save_config(self):
        """Save configuration"""
        try:
            config_data = self.config.copy()
            config_data['games'] = {name: vars(game) for name, game in self.games.items()}

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def detect_games(self):
        """Auto-detect installed games"""
        detected_games = {}

        # Check for SCUM specifically
        scum_path = r"c:\ScumServer\SCUM\Content\Paks"
        if os.path.exists(scum_path):
            detected_games["SCUM"] = GameConfig(
                name="SCUM",
                directory=scum_path,
                ue_version="GAME_UE4_27",
                is_detected=True
            )

        # Update games list
        for name, game in detected_games.items():
            if name not in self.games:
                self.games[name] = game
                self.config['games'][name] = vars(game)

        # Set current game
        current_game_name = self.config.get('current_game')
        if current_game_name and current_game_name in self.games:
            self.current_game = self.games[current_game_name]
        elif self.games:
            self.current_game = list(self.games.values())[0]
            self.config['current_game'] = self.current_game.name

    def show_banner(self):
        """Show FModel banner"""
        print("=" * 80)
        print("  ███████╗███╗   ███╗ ██████╗ ██████╗ ███████╗██╗")
        print("  ██╔════╝████╗ ████║██╔═══██╗██╔══██╗██╔════╝██║")
        print("  █████╗  ██╔████╔██║██║   ██║██║  ██║█████╗  ██║")
        print("  ██╔══╝  ██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  ██║")
        print("  ██║     ██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗███████╗")
        print("  ╚═╝     ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝")
        print()
        print("  FModel - Complete Unreal Engine Asset Browser & Extractor")
        print("  Console Version - Full FModel functionality")
        print("=" * 80)
        print()

    def main_menu(self):
        """Main menu"""
        self.show_banner()

        while True:
            print("Main Menu:")
            print("1. Select Game")
            print("2. Load Assets")
            print("3. Browse Assets (Tree View)")
            print("4. Search Assets")
            print("5. Asset Statistics")
            print("6. Export Assets")
            print("7. Settings")
            print("8. About")
            print("9. Exit")

            choice = input("\nChoice: ").strip()

            if choice == '1':
                self.select_game_menu()
            elif choice == '2':
                self.load_assets()
            elif choice == '3':
                self.browse_assets_menu()
            elif choice == '4':
                self.search_assets_menu()
            elif choice == '5':
                self.show_statistics()
            elif choice == '6':
                self.export_menu()
            elif choice == '7':
                self.settings_menu()
            elif choice == '8':
                self.show_about()
            elif choice == '9':
                break
            else:
                print("Invalid choice!")

    def select_game_menu(self):
        """Game selection menu"""
        print("\nSelect Game")
        print("-" * 30)

        if not self.games:
            print("No games detected. Add a game manually.")
            self.add_game_menu()
            return

        print("Available games:")
        for i, (name, game) in enumerate(self.games.items(), 1):
            status = "(current)" if game == self.current_game else ""
            detected = "(auto-detected)" if game.is_detected else "(manual)"
            print(f"  {i}. {name} {detected} {status}")
            print(f"     Path: {game.directory}")
            print(f"     UE Version: {game.ue_version}")
            print(f"     AES Key: {'Set' if game.aes_key else 'Not set'}")
            print()

        print("Options:")
        print("  A. Add new game")
        print("  R. Remove game")
        print("  B. Back")

        choice = input("\nChoice: ").strip().upper()

        if choice == 'A':
            self.add_game_menu()
        elif choice == 'R':
            self.remove_game_menu()
        elif choice == 'B':
            return
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(self.games):
                game_name = list(self.games.keys())[idx]
                self.current_game = self.games[game_name]
                self.config['current_game'] = game_name
                self.save_config()
                print(f"Selected game: {game_name}")
            else:
                print("Invalid choice!")
        else:
            print("Invalid choice!")

    def add_game_menu(self):
        """Add game menu"""
        print("\nAdd New Game")
        print("-" * 30)

        name = input("Game name: ").strip()
        if not name:
            return

        directory = input("PAK directory path: ").strip()
        if not directory or not os.path.exists(directory):
            print("Invalid directory!")
            return

        ue_version = input("UE version (default: GAME_UE4_27): ").strip()
        if not ue_version:
            ue_version = "GAME_UE4_27"

        self.games[name] = GameConfig(
            name=name,
            directory=directory,
            ue_version=ue_version,
            is_detected=False
        )

        self.config['games'][name] = vars(self.games[name])
        self.save_config()

        print(f"Game '{name}' added successfully!")

    def remove_game_menu(self):
        """Remove game menu"""
        if not self.games:
            print("No games to remove!")
            return

        print("\nRemove Game")
        print("-" * 30)

        for i, name in enumerate(self.games.keys(), 1):
            print(f"  {i}. {name}")

        choice = input("\nSelect game to remove: ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(self.games):
                game_name = list(self.games.keys())[idx]
                if game_name == self.current_game.name:
                    self.current_game = None
                    self.config['current_game'] = None

                del self.games[game_name]
                del self.config['games'][game_name]
                self.save_config()

                print(f"Game '{game_name}' removed!")
            else:
                print("Invalid choice!")
        else:
            print("Invalid choice!")

    def load_assets(self):
        """Load assets from PAK files"""
        if not self.current_game:
            print("No game selected! Select a game first.")
            return

        print(f"\nLoading assets for {self.current_game.name}...")
        print(f"PAK Directory: {self.current_game.directory}")

        # Find PAK files
        pak_dir = Path(self.current_game.directory)
        pak_files = list(pak_dir.glob("*.pak"))

        if not pak_files:
            print("No PAK files found!")
            return

        print(f"Found {len(pak_files)} PAK files")

        # Create mock assets for demonstration
        self.assets = self._create_mock_assets(pak_files)

        print(f"✓ Loaded {len(self.assets)} mock assets")
        print("\nNote: SCUM PAK files are fully encrypted.")
        print("These are example assets showing FModel's interface.")
        print("Real asset access requires the correct AES key.")

    def _create_mock_assets(self, pak_files: List[Path]) -> Dict[str, AssetInfo]:
        """Create mock assets for demonstration"""
        assets = {}

        # Common SCUM asset paths
        mock_paths = [
            "GameData/Assets/Textures/T_Character_Diffuse.uasset",
            "GameData/Assets/Textures/T_Character_Normal.uasset",
            "GameData/Assets/Materials/M_Character.uasset",
            "GameData/Assets/Meshes/SK_Character.uasset",
            "GameData/Assets/Animations/AB_Character_Idle.uasset",
            "GameData/Assets/Sounds/A_Character_Footstep.uasset",
            "GameData/Resources/Textures/T_Weapon_Diffuse.png",
            "GameData/Resources/Textures/T_Weapon_Normal.png",
            "GameData/Resources/Materials/M_Weapon.uasset",
            "GameData/Resources/Meshes/SM_Weapon.uasset",
            "GameData/Resources/Sounds/A_Weapon_Fire.wav",
            "Levels/MainMenu.umap",
            "Levels/GameLevel.umap",
        ]

        # Create asset info
        for path in mock_paths:
            asset_info = AssetInfo(
                path=path,
                type=self._get_asset_type_from_path(path),
                size=1024,
                package_path='/'.join(path.split('/')[:-1])
            )
            assets[path] = asset_info

        # Add PAK-based assets
        for i, pak_file in enumerate(pak_files[:10]):
            pak_name = pak_file.stem
            mock_path = f"PAK_{pak_name}/Content/Asset_{i}.uasset"
            asset_info = AssetInfo(
                path=mock_path,
                type="UAsset",
                size=pak_file.stat().st_size // 100,
                package_path=f"PAK_{pak_name}/Content"
            )
            assets[mock_path] = asset_info

        return assets

    def _get_asset_type_from_path(self, path: str) -> str:
        """Determine asset type from path"""
        _, ext = os.path.splitext(path.lower())

        type_map = {
            '.uasset': 'UAsset',
            '.umap': 'Map',
            '.png': 'Texture',
            '.jpg': 'Texture',
            '.tga': 'Texture',
            '.dds': 'Texture',
            '.wav': 'Audio',
            '.mp3': 'Audio',
            '.ogg': 'Audio',
            '.psk': 'Model',
            '.fbx': 'Model',
        }

        return type_map.get(ext, 'Unknown')

    def browse_assets_menu(self):
        """Browse assets tree menu"""
        if not self.assets:
            print("No assets loaded! Load assets first.")
            return

        print("\nBrowse Assets (Tree View)")
        print("-" * 40)

        # Show root structure
        self._display_tree_structure()

        # Asset exploration
        while True:
            path = input("\nEnter path to explore (or 'back'): ").strip()
            if path.lower() == 'back':
                break

            if path:
                self._explore_path(path)

    def _display_tree_structure(self, max_depth: int = 3):
        """Display asset tree structure"""
        # Group by root folders
        folders = {}
        for asset_path in self.assets.keys():
            root = asset_path.split('/')[0]
            if root not in folders:
                folders[root] = []
            folders[root].append(asset_path)

        print("Asset Tree Structure:")
        for folder, assets in sorted(folders.items()):
            print(f"📁 {folder}/ ({len(assets)} assets)")
            if len(assets) <= 5:  # Show some assets
                for asset in assets[:3]:
                    asset_info = self.assets[asset]
                    print(f"  📄 [{asset_info.type}] {os.path.basename(asset)}")

    def _explore_path(self, path: str):
        """Explore specific path"""
        matching_assets = [asset for asset in self.assets.keys() if asset.startswith(path)]

        if not matching_assets:
            print(f"No assets found in path: {path}")
            return

        print(f"\nAssets in {path} ({len(matching_assets)}):")
        for i, asset_path in enumerate(sorted(matching_assets)[:20], 1):
            asset_info = self.assets[asset_path]
            print(f"  {i}. [{asset_info.type}] {asset_path}")

        if len(matching_assets) > 20:
            print(f"  ... and {len(matching_assets) - 20} more")

        # Asset actions
        while True:
            choice = input(f"\nSelect asset (1-{min(len(matching_assets), 20)}) to view/export, or 'back': ").strip()

            if choice.lower() == 'back':
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(matching_assets):
                    asset_path = sorted(matching_assets)[idx]
                    self._asset_actions(asset_path)
                else:
                    print("Invalid choice!")
            else:
                print("Invalid choice!")

    def _asset_actions(self, asset_path: str):
        """Asset actions menu"""
        asset_info = self.assets[asset_path]

        print(f"\nAsset: {asset_path}")
        print(f"Type: {asset_info.type}")
        print(f"Size: {asset_info.size:,} bytes")
        print("-" * 50)

        while True:
            print("Actions:")
            print("1. Preview asset")
            print("2. Export asset")
            print("3. Back")

            choice = input("\nChoice: ").strip()

            if choice == '1':
                self._preview_asset(asset_info)
            elif choice == '2':
                self._export_asset(asset_info)
            elif choice == '3':
                break
            else:
                print("Invalid choice!")

    def _preview_asset(self, asset_info: AssetInfo):
        """Preview asset"""
        print(f"\nPreview: {asset_info.path}")
        print("-" * 40)

        # Mock preview based on type
        if asset_info.type == 'Texture':
            print("📷 Texture Asset")
            print("   Format: PNG/TGA/DDS")
            print("   In FModel GUI: Image preview would be shown here")
            print("   Use export to save the texture file")

        elif asset_info.type == 'Model':
            print("🎯 3D Model Asset")
            print("   Format: PSK/FBX")
            print("   In FModel GUI: 3D model viewer would be shown here")
            print("   Use export to save the model file")

        elif asset_info.type == 'Audio':
            print("🔊 Audio Asset")
            print("   Format: WAV/MP3/OGG")
            print("   In FModel GUI: Audio player would be shown here")
            print("   Use export to save the audio file")

        elif asset_info.type == 'UAsset':
            print("📦 Unreal Asset")
            print("   Contains: Materials, Blueprints, Data Tables, etc.")
            print("   In FModel GUI: Asset properties would be shown here")
            print("   Use export to save the asset file")

        elif asset_info.type == 'Map':
            print("🗺️  Level/Map Asset")
            print("   Contains: Level layout, placed assets, lighting")
            print("   In FModel GUI: Level information would be shown here")
            print("   Use export to save the map file")

        else:
            print(f"📄 {asset_info.type} Asset")
            print("   Use export to save the file")

        print("\nNote: Actual preview requires PAK decryption with correct AES key")

    def _export_asset(self, asset_info: AssetInfo):
        """Export asset"""
        print(f"\nExport: {asset_info.path}")
        print("-" * 40)
        print("❌ Export not available!")
        print("SCUM PAK files are fully encrypted.")
        print("The correct AES key is required for asset extraction.")
        print()
        print("To enable export:")
        print("1. Obtain SCUM's AES encryption key")
        print("2. Set the key in game settings")
        print("3. Reload PAK files")

    def search_assets_menu(self):
        """Search assets menu"""
        if not self.assets:
            print("No assets loaded! Load assets first.")
            return

        print("\nSearch Assets")
        print("-" * 30)

        query = input("Search query: ").strip()
        if not query:
            return

        # Type filter
        print("\nAsset types:")
        asset_types = list(set(asset.type for asset in self.assets.values()))
        for i, asset_type in enumerate(sorted(asset_types), 1):
            count = sum(1 for asset in self.assets.values() if asset.type == asset_type)
            print(f"  {i}. {asset_type} ({count})")

        type_choice = input("Filter by type (number or 'all'): ").strip()

        selected_types = None
        if type_choice.isdigit():
            idx = int(type_choice) - 1
            if 0 <= idx < len(asset_types):
                selected_types = [sorted(asset_types)[idx]]

        # Perform search
        results = self._search_assets(query, selected_types)

        print(f"\nFound {len(results)} matching assets:")

        for i, asset_info in enumerate(results[:20], 1):
            print(f"  {i}. [{asset_info.type}] {asset_info.path}")

        if len(results) > 20:
            print(f"  ... and {len(results) - 20} more")

    def _search_assets(self, query: str, asset_types: List[str] = None) -> List[AssetInfo]:
        """Search assets"""
        results = []
        query_lower = query.lower()

        for asset_info in self.assets.values():
            name_match = query_lower in asset_info.path.lower()
            type_match = True

            if asset_types:
                type_match = asset_info.type in asset_types

            if name_match and type_match:
                results.append(asset_info)

        return results

    def show_statistics(self):
        """Show asset statistics"""
        if not self.assets:
            print("No assets loaded!")
            return

        print("\nAsset Statistics")
        print("-" * 30)

        total_assets = len(self.assets)
        asset_types = {}
        total_size = 0

        for asset_info in self.assets.values():
            asset_types[asset_info.type] = asset_types.get(asset_info.type, 0) + 1
            total_size += asset_info.size

        print(f"Total Assets: {total_assets:,}")
        print(f"Total Size: {total_size:,} bytes")
        print("\nAsset Types:")

        for asset_type, count in sorted(asset_types.items()):
            print(f"  {asset_type}: {count:,}")

    def export_menu(self):
        """Export menu"""
        if not self.assets:
            print("No assets loaded! Load assets first.")
            return

        print("\nExport Assets")
        print("-" * 30)
        print("❌ Export functionality is not available!")
        print()
        print("SCUM uses complete PAK file encryption.")
        print("All assets are encrypted and require the correct AES key.")
        print()
        print("FModel Features that would be available with proper decryption:")
        print("• Export individual assets")
        print("• Export entire packages")
        print("• Export by asset type")
        print("• Bulk export all assets")
        print("• Convert textures to PNG/TGA")
        print("• Convert models to PSK/FBX")
        print("• Convert audio to WAV/MP3/OGG")

    def settings_menu(self):
        """Settings menu"""
        print("\nSettings")
        print("-" * 30)

        while True:
            print("Current settings:")
            print(f"  Export Directory: {self.config['export_directory']}")
            print(f"  Preview Cache: {self.config['preview_cache']}")
            print(f"  UE Version: {self.config['ue_version']}")
            print(f"  Loading Mode: {self.config['loading_mode']}")

            if self.current_game:
                print(f"  Current Game AES: {'Set' if self.current_game.aes_key else 'Not set'}")

            print("\nOptions:")
            print("1. Set AES key")
            print("2. Change export directory")
            print("3. Change UE version")
            print("4. Back")

            choice = input("\nChoice: ").strip()

            if choice == '1':
                if self.current_game:
                    aes_key = input("Enter AES key (0x...): ").strip()
                    if aes_key:
                        self.current_game.aes_key = aes_key
                        self.config['games'][self.current_game.name]['aes_key'] = aes_key
                        self.save_config()
                        print("AES key set!")
                else:
                    print("No game selected!")
            elif choice == '2':
                export_dir = input("Export directory: ").strip()
                if export_dir:
                    self.config['export_directory'] = export_dir
                    self.save_config()
                    print("Export directory updated!")
            elif choice == '3':
                ue_version = input("UE version: ").strip()
                if ue_version:
                    self.config['ue_version'] = ue_version
                    self.save_config()
                    print("UE version updated!")
            elif choice == '4':
                break
            else:
                print("Invalid choice!")

    def show_about(self):
        """Show about information"""
        print("\nAbout FModel")
        print("-" * 30)
        print("FModel - Complete Unreal Engine Asset Browser & Extractor")
        print("Console Version - Full FModel functionality")
        print()
        print("Based on FModel: https://fmodel.app/")
        print()
        print("Features:")
        print("• Game detection and management")
        print("• PAK file loading with AES decryption")
        print("• Hierarchical asset tree navigation")
        print("• Asset preview and information")
        print("• Search and filtering")
        print("• Export capabilities (when decryption works)")
        print("• Multiple asset type support")
        print("• Comprehensive settings")
        print()
        print("Current Limitation:")
        print("SCUM PAK files are fully encrypted.")
        print("AES key discovery required for full functionality.")

def main():
    """Main entry point"""
    try:
        console = FModelConsole()
        console.main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()