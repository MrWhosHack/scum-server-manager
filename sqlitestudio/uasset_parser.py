#!/usr/bin/env python3
"""
UAsset Parser for Unreal Engine assets
Compatible with FModel - provides asset information and preview
"""

import struct
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class UAssetParser:
    """UAsset file parser for FModel compatibility"""

    def __init__(self):
        self.asset_info = {}
        self.names = []
        self.imports = []
        self.exports = []

    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse UAsset data and return information"""
        try:
            if len(data) < 100:
                return {"error": "Data too small for UAsset"}

            info = {
                "type": "UAsset",
                "size": len(data),
                "parsed": False,
                "sections": {}
            }

            # Try to parse header
            header_info = self._parse_header(data)
            if header_info:
                info.update(header_info)
                info["parsed"] = True

            # Try to extract names
            if self.names:
                info["names"] = self.names[:10]  # First 10 names

            # Try to extract imports/exports
            if self.imports:
                info["imports"] = len(self.imports)

            if self.exports:
                info["exports"] = len(self.exports)

            return info

        except Exception as e:
            logger.error(f"Error parsing UAsset: {e}")
            return {"error": str(e)}

    def _parse_header(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse UAsset header"""
        try:
            pos = 0

            # Magic number (should be 0x9E2A83C1 for UE4)
            magic = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            if magic != 0x9E2A83C1:
                return None

            # Version info
            legacy_version = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            ue_version = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            file_version = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            # Engine version
            engine_major = data[pos]
            engine_minor = data[pos+1]
            engine_patch = data[pos+2]
            pos += 4

            # Various counts
            total_header_size = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            folder_name = self._read_string(data, pos)
            pos = folder_name[1]

            package_flags = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            name_count = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            name_offset = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4

            # Read names
            self.names = self._read_names(data, name_offset, name_count)

            return {
                "magic": f"0x{magic:08X}",
                "legacy_version": legacy_version,
                "ue_version": ue_version,
                "file_version": file_version,
                "engine_version": f"{engine_major}.{engine_minor}.{engine_patch}",
                "total_header_size": total_header_size,
                "folder_name": folder_name[0],
                "package_flags": f"0x{package_flags:08X}",
                "name_count": name_count,
                "name_offset": name_offset
            }

        except Exception as e:
            logger.error(f"Error parsing header: {e}")
            return None

    def _read_string(self, data: bytes, pos: int) -> Tuple[str, int]:
        """Read null-terminated string"""
        try:
            start = pos
            while pos < len(data) and data[pos] != 0:
                pos += 1
            length = pos - start
            string = data[start:start+length].decode('utf-8', errors='ignore')
            return string, pos + 1
        except:
            return "", pos

    def _read_names(self, data: bytes, offset: int, count: int) -> List[str]:
        """Read name table"""
        names = []
        pos = offset

        try:
            for i in range(min(count, 100)):  # Limit to first 100 names
                if pos >= len(data):
                    break

                # Read string
                string, new_pos = self._read_string(data, pos)
                pos = new_pos

                # Skip additional data
                if pos + 8 <= len(data):
                    pos += 8  # Skip some metadata

                if string:
                    names.append(string)

        except Exception as e:
            logger.error(f"Error reading names: {e}")

        return names

    def get_asset_type(self, data: bytes) -> str:
        """Determine asset type from data"""
        try:
            if len(data) < 4:
                return "Unknown"

            # Check for common patterns
            if data[:4] == b'\x9E\x2A\x83\xC1':  # UAsset magic
                return "UAsset"

            # Check file extension patterns in data
            data_str = data[:1000].decode('utf-8', errors='ignore').lower()

            if 'texture' in data_str:
                return "Texture"
            elif 'material' in data_str:
                return "Material"
            elif 'skeletalmesh' in data_str:
                return "Skeletal Mesh"
            elif 'staticmesh' in data_str:
                return "Static Mesh"
            elif 'sound' in data_str or 'audio' in data_str:
                return "Audio"
            elif 'animation' in data_str:
                return "Animation"
            elif 'blueprint' in data_str:
                return "Blueprint"
            elif 'particle' in data_str:
                return "Particle System"
            else:
                return "UAsset"

        except:
            return "Unknown"

class UMapParser:
    """UMAP parser for Unreal Engine maps"""

    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse UMAP data"""
        try:
            info = {
                "type": "UMap",
                "size": len(data),
                "parsed": False
            }

            # Basic map info
            if len(data) > 100:
                info["parsed"] = True
                info["description"] = "Unreal Engine Map File"

            return info

        except Exception as e:
            return {"error": str(e)}

class TextureParser:
    """Texture parser for various formats"""

    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse texture data"""
        try:
            info = {
                "type": "Texture",
                "size": len(data),
                "parsed": True,
                "format": "Unknown"
            }

            # Check for common texture headers
            if len(data) >= 4:
                header = data[:4]

                if header == b'\x89PNG':
                    info["format"] = "PNG"
                elif header[:2] == b'\xFF\xD8':
                    info["format"] = "JPEG"
                elif header[:4] == b'DDS ':
                    info["format"] = "DDS"
                elif len(data) >= 18 and data[16:18] == b'TG':
                    info["format"] = "TGA"

            return info

        except Exception as e:
            return {"error": str(e)}

class AudioParser:
    """Audio parser for various formats"""

    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse audio data"""
        try:
            info = {
                "type": "Audio",
                "size": len(data),
                "parsed": True,
                "format": "Unknown"
            }

            # Check for common audio headers
            if len(data) >= 12:
                header = data[:12]

                if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                    info["format"] = "WAV"
                elif header[:3] == b'ID3' or (header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
                    info["format"] = "MP3"
                elif header[:4] == b'OggS':
                    info["format"] = "OGG"

            return info

        except Exception as e:
            return {"error": str(e)}

# Asset parser factory
class AssetParserFactory:
    """Factory for creating appropriate asset parsers"""

    @staticmethod
    def get_parser(asset_path: str) -> Any:
        """Get appropriate parser for asset type"""
        ext = Path(asset_path).suffix.lower()

        if ext == '.uasset':
            return UAssetParser()
        elif ext == '.umap':
            return UMapParser()
        elif ext in ['.png', '.jpg', '.tga', '.dds']:
            return TextureParser()
        elif ext in ['.wav', '.mp3', '.ogg']:
            return AudioParser()
        else:
            return UAssetParser()  # Default parser

# Test function
def test_parsers():
    """Test asset parsers"""
    print("Testing asset parsers...")

    # Test UAsset parser
    uasset_parser = UAssetParser()
    test_data = b'\x9E\x2A\x83\xC1' + b'\x00' * 100  # Mock UAsset data
    result = uasset_parser.parse(test_data)
    print(f"UAsset parse result: {result}")

    # Test texture parser
    texture_parser = TextureParser()
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    result = texture_parser.parse(png_data)
    print(f"Texture parse result: {result}")

if __name__ == "__main__":
    test_parsers()