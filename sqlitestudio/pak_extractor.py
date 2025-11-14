#!/usr/bin/env python3
"""
PAK Extractor for Unreal Engine games
Compatible with FModel - supports AES decryption and asset extraction
"""

import os
import struct
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from Cryptodome.Cipher import AES
from Cryptodome.Util import Counter

logger = logging.getLogger(__name__)

class PAKExtractor:
    """PAK file extractor with AES decryption support"""

    # PAK file magic number
    PAK_MAGIC = 0x5A6F12E1

    # Compression methods
    COMPRESSION_NONE = 0x00
    COMPRESSION_ZLIB = 0x01
    COMPRESSION_GZIP = 0x02
    COMPRESSION_LZ4 = 0x03

    def __init__(self, aes_key: str = ""):
        self.aes_key = aes_key
        self.pak_path = ""
        self.pak_file = None
        self.version = 0
        self.mount_point = ""
        self.entries: Dict[str, dict] = {}
        self.index_offset = 0
        self.index_size = 0

    def open_pak(self, pak_path: str) -> bool:
        """Open and parse PAK file"""
        try:
            if not os.path.exists(pak_path):
                logger.error(f"PAK file not found: {pak_path}")
                return False

            self.pak_path = pak_path
            self.pak_file = open(pak_path, 'rb')

            # Read header
            if not self._read_header():
                return False

            # Read index
            if not self._read_index():
                return False

            logger.info(f"Successfully opened PAK: {pak_path}")
            logger.info(f"Version: {self.version}, Mount point: {self.mount_point}")
            logger.info(f"Total entries: {len(self.entries)}")

            return True

        except Exception as e:
            logger.error(f"Error opening PAK file: {e}")
            if self.pak_file:
                self.pak_file.close()
            return False

    def _read_header(self) -> bool:
        """Read PAK file header"""
        try:
            # Read magic number
            magic = struct.unpack('<I', self.pak_file.read(4))[0]
            if magic != self.PAK_MAGIC:
                logger.error(f"Invalid PAK magic: {magic:08X}")
                return False

            # Read version
            self.version = struct.unpack('<I', self.pak_file.read(4))[0]
            logger.info(f"PAK version: {self.version}")

            # Read mount point
            mount_point_len = struct.unpack('<I', self.pak_file.read(4))[0]
            if mount_point_len > 0:
                self.mount_point = self.pak_file.read(mount_point_len).decode('utf-8').rstrip('\0')
            else:
                self.mount_point = ""

            # Skip padding
            self.pak_file.read(4)  # Padding

            return True

        except Exception as e:
            logger.error(f"Error reading PAK header: {e}")
            return False

    def _read_index(self) -> bool:
        """Read PAK index"""
        try:
            # Seek to index
            self.pak_file.seek(-8, 2)  # 8 bytes from end
            self.index_offset, self.index_size = struct.unpack('<QQ', self.pak_file.read(8))

            # Seek to index start
            self.pak_file.seek(self.index_offset)

            # Read index
            index_data = self.pak_file.read(self.index_size)

            # Decrypt index if needed
            if self.aes_key:
                index_data = self._decrypt_aes(index_data, self.index_offset)

            # Parse index
            return self._parse_index(index_data)

        except Exception as e:
            logger.error(f"Error reading PAK index: {e}")
            return False

    def _parse_index(self, index_data: bytes) -> bool:
        """Parse PAK index data"""
        try:
            pos = 0

            # Read mount point again
            mount_point_len = struct.unpack('<I', index_data[pos:pos+4])[0]
            pos += 4
            if mount_point_len > 0:
                mount_point = index_data[pos:pos+mount_point_len].decode('utf-8').rstrip('\0')
                pos += mount_point_len

            # Read number of entries
            num_entries = struct.unpack('<I', index_data[pos:pos+4])[0]
            pos += 4

            logger.info(f"Parsing {num_entries} entries")

            # Read entries
            for i in range(num_entries):
                if pos >= len(index_data):
                    break

                # Read filename
                filename_len = struct.unpack('<I', index_data[pos:pos+4])[0]
                pos += 4

                if filename_len == 0:
                    continue

                filename = index_data[pos:pos+filename_len].decode('utf-8').rstrip('\0')
                pos += filename_len

                # Read entry data
                offset, size, uncompressed_size, compression_method = struct.unpack('<QQQI', index_data[pos:pos+20])
                pos += 20

                # Skip hash and flags for now
                pos += 20  # Skip hash (20 bytes)
                pos += 4   # Skip flags

                # Skip compression blocks if any
                if compression_method != self.COMPRESSION_NONE:
                    num_blocks = struct.unpack('<I', index_data[pos:pos+4])[0]
                    pos += 4
                    pos += num_blocks * 16  # Skip compression blocks

                # Store entry
                self.entries[filename] = {
                    'offset': offset,
                    'size': size,
                    'uncompressed_size': uncompressed_size,
                    'compression_method': compression_method,
                    'encrypted': self.aes_key != ""  # Assume encrypted if key provided
                }

            return True

        except Exception as e:
            logger.error(f"Error parsing PAK index: {e}")
            return False

    def list_files(self) -> List[str]:
        """List all files in PAK"""
        return list(self.entries.keys())

    def extract_file(self, filename: str, output_path: Optional[str] = None) -> Optional[bytes]:
        """Extract file from PAK"""
        if filename not in self.entries:
            logger.error(f"File not found: {filename}")
            return None

        try:
            entry = self.entries[filename]

            # Seek to file data
            self.pak_file.seek(entry['offset'])

            # Read compressed/encrypted data
            data = self.pak_file.read(entry['size'])

            # Decrypt if needed
            if entry.get('encrypted', False) and self.aes_key:
                data = self._decrypt_aes(data, entry['offset'])

            # Decompress if needed
            if entry['compression_method'] != self.COMPRESSION_NONE:
                data = self._decompress_data(data, entry['compression_method'])

            # Write to file if output path provided
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(data)
                logger.info(f"Extracted {filename} to {output_path}")

            return data

        except Exception as e:
            logger.error(f"Error extracting {filename}: {e}")
            return None

    def _decrypt_aes(self, data: bytes, offset: int) -> bytes:
        """Decrypt data using AES"""
        if not self.aes_key:
            return data

        try:
            # Parse AES key
            if self.aes_key.startswith('0x'):
                key = bytes.fromhex(self.aes_key[2:])
            else:
                key = bytes.fromhex(self.aes_key)

            # Create AES cipher
            # Use offset as IV/nonce for CTR mode
            iv = struct.pack('<Q', offset // 16)  # Block-aligned offset
            cipher = AES.new(key, AES.MODE_CTR, counter=Counter.new(128, initial_value=int.from_bytes(iv, 'little')))

            # Decrypt
            return cipher.decrypt(data)

        except Exception as e:
            logger.error(f"AES decryption error: {e}")
            return data

    def _decompress_data(self, data: bytes, method: int) -> bytes:
        """Decompress data"""
        try:
            if method == self.COMPRESSION_ZLIB:
                import zlib
                return zlib.decompress(data)
            elif method == self.COMPRESSION_GZIP:
                import gzip
                return gzip.decompress(data)
            elif method == self.COMPRESSION_LZ4:
                import lz4.frame
                return lz4.frame.decompress(data)
            else:
                logger.warning(f"Unknown compression method: {method}")
                return data
        except ImportError as e:
            logger.warning(f"Decompression library not available: {e}")
            return data
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            return data

    def get_file_info(self, filename: str) -> Optional[dict]:
        """Get file information"""
        return self.entries.get(filename)

    def close(self):
        """Close PAK file"""
        if self.pak_file:
            self.pak_file.close()
            self.pak_file = None

    def __del__(self):
        """Destructor"""
        self.close()

class UAssetParser:
    """Basic UAsset parser for FModel compatibility"""

    def __init__(self):
        self.asset_info = {}

    def parse(self, data: bytes) -> dict:
        """Parse UAsset data"""
        try:
            if len(data) < 16:
                return {"error": "Data too small"}

            # Basic UAsset header parsing
            pos = 0

            # Skip some header fields
            pos += 16  # Magic, version, etc.

            # Try to extract basic info
            info = {
                "size": len(data),
                "type": "UAsset",
                "parsed": False
            }

            # Look for common UAsset patterns
            if b"Engine" in data[:100]:
                info["engine_detected"] = True

            return info

        except Exception as e:
            return {"error": str(e)}

# Test function
def test_pak_extractor():
    """Test PAK extractor"""
    # Test with SCUM PAK
    pak_path = r"c:\ScumServer\SCUM\Content\Paks\pakchunk0-WindowsServer.pak"
    aes_key = "0x0B1F4E543FB798EFC5BD861BB405BE7081CD03698EA9BA06469462A3B113CA81"  # Default SCUM key

    extractor = PAKExtractor(aes_key)

    if extractor.open_pak(pak_path):
        files = extractor.list_files()
        print(f"Found {len(files)} files")

        # Try to extract first few files
        for i, filename in enumerate(files[:5]):
            print(f"Extracting {filename}...")
            data = extractor.extract_file(filename)
            if data:
                print(f"  Extracted {len(data)} bytes")
            else:
                print("  Failed to extract")

        extractor.close()
    else:
        print("Failed to open PAK file")

if __name__ == "__main__":
    test_pak_extractor()
