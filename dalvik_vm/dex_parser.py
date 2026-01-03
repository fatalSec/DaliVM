import struct
import zipfile
import re
from typing import List, Dict, Optional, Tuple, Any


class SingleDexData:
    """Holds parsed data for a single DEX file."""
    def __init__(self, dex_name: str, dex_data: bytes):
        self.dex_name = dex_name
        self.dex_data = dex_data
        self.strings: List[str] = []
        self.types: List[str] = []
        self.protos: List[Dict] = []
        self.methods: List[Dict] = []
        
        # Header offsets
        self.string_ids_size = 0
        self.string_ids_off = 0
        self.type_ids_size = 0
        self.type_ids_off = 0
        self.proto_ids_size = 0
        self.proto_ids_off = 0
        self.field_ids_size = 0
        self.field_ids_off = 0
        self.method_ids_size = 0
        self.method_ids_off = 0
        self.class_defs_size = 0
        self.class_defs_off = 0
        
    def _read_uleb128(self, offset: int) -> Tuple[int, int]:
        result = 0
        shift = 0
        count = 0
        while True:
            byte = self.dex_data[offset + count]
            result |= (byte & 0x7f) << shift
            count += 1
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, count


class DexParser:
    """Parser for DEX files in an APK with multidex support."""
    
    def __init__(self, apk_path: str):
        self.apk_path = apk_path
        
        # List of SingleDexData objects - one per DEX file
        self.dex_files: List[SingleDexData] = []
        
        # Unified lookup: global_method_idx -> (dex_index, local_method_idx)
        self._method_index_map: Dict[int, Tuple[int, int]] = {}
        
        # Global method offset for each DEX (cumulative sum of previous method counts)
        self._dex_method_offsets: List[int] = []
        
        # Legacy compatibility - aggregate strings/methods for simple lookups
        self.strings: List[str] = []
        self.types: List[str] = []
        self.protos: List[Dict] = []
        self.methods: List[Dict] = []
        
        self._read_all_dex_from_apk()
        self._parse_all()
        self._build_unified_index()
    
    def _read_all_dex_from_apk(self):
        """Read all classes*.dex files from the APK."""
        with zipfile.ZipFile(self.apk_path, 'r') as z:
            # Find all dex files matching classes*.dex pattern
            dex_files = sorted([
                name for name in z.namelist() 
                if re.match(r'^classes\d*\.dex$', name)
            ])
            
            if not dex_files:
                raise ValueError("No classes*.dex files found in APK")
            
            for dex_name in dex_files:
                dex_data = z.read(dex_name)
                self.dex_files.append(SingleDexData(dex_name, dex_data))
    
    def _parse_all(self):
        """Parse all DEX files."""
        for dex in self.dex_files:
            self._parse_single_dex(dex)
    
    def _parse_single_dex(self, dex: SingleDexData):
        """Parse a single DEX file."""
        data = dex.dex_data
        
        # Header validation
        magic = data[0:8]
        # TODO: Full validation
        
        # Parse header offsets
        dex.string_ids_size = struct.unpack('<I', data[0x38:0x3C])[0]
        dex.string_ids_off = struct.unpack('<I', data[0x3C:0x40])[0]
        dex.type_ids_size = struct.unpack('<I', data[0x40:0x44])[0]
        dex.type_ids_off = struct.unpack('<I', data[0x44:0x48])[0]
        dex.proto_ids_size = struct.unpack('<I', data[0x48:0x4C])[0]
        dex.proto_ids_off = struct.unpack('<I', data[0x4C:0x50])[0]
        dex.field_ids_size = struct.unpack('<I', data[0x50:0x54])[0]
        dex.field_ids_off = struct.unpack('<I', data[0x54:0x58])[0]
        dex.method_ids_size = struct.unpack('<I', data[0x58:0x5C])[0]
        dex.method_ids_off = struct.unpack('<I', data[0x5C:0x60])[0]
        dex.class_defs_size = struct.unpack('<I', data[0x60:0x64])[0]
        dex.class_defs_off = struct.unpack('<I', data[0x64:0x68])[0]
        
        self._parse_strings(dex)
        self._parse_types(dex)
        self._parse_protos(dex)
        self._parse_methods(dex)
    
    def _parse_strings(self, dex: SingleDexData):
        """Parse string table for a DEX.
        
        DEX strings use MUTF-8 encoding:
        - ULEB128 prefix gives char count (NOT byte count)
        - Strings are null-terminated (0x00 byte)
        - Null char (U+0000) is encoded as 0xC0 0x80
        - Supplementary chars use surrogate pairs
        """
        dex.strings = []
        for i in range(dex.string_ids_size):
            off = dex.string_ids_off + (i * 4)
            str_off = struct.unpack('<I', dex.dex_data[off:off+4])[0]
            
            # Read char count (for reference, not used for byte slicing)
            char_count, len_bytes = dex._read_uleb128(str_off)
            data_start = str_off + len_bytes
            
            # Read until null terminator (MUTF-8 strings are null-terminated)
            end = data_start
            while end < len(dex.dex_data) and dex.dex_data[end] != 0:
                end += 1
            s_data = dex.dex_data[data_start:end]
            
            # Decode MUTF-8 to Python string
            try:
                decoded = self._decode_mutf8(s_data)
                dex.strings.append(decoded)
            except Exception:
                # Fallback to latin-1 if MUTF-8 decoding fails
                dex.strings.append(s_data.decode('latin-1', errors='replace'))
    
    def _decode_mutf8(self, data: bytes) -> str:
        """Decode MUTF-8 (Modified UTF-8) to Python string.
        
        MUTF-8 differences from standard UTF-8:
        - Null (U+0000) is encoded as 0xC0 0x80
        - Supplementary chars (U+10000+) use surrogate pairs
        """
        result = []
        i = 0
        while i < len(data):
            b1 = data[i]
            if b1 == 0:
                # Should not happen (null terminator handled above)
                break
            elif b1 < 0x80:
                # Single byte (ASCII)
                result.append(chr(b1))
                i += 1
            elif b1 < 0xC0:
                # Invalid start byte, treat as raw
                result.append(chr(b1))
                i += 1
            elif b1 < 0xE0:
                # 2-byte sequence
                if i + 1 >= len(data):
                    result.append(chr(b1))
                    i += 1
                    continue
                b2 = data[i + 1]
                # Check for MUTF-8 null encoding (0xC0 0x80 = U+0000)
                if b1 == 0xC0 and b2 == 0x80:
                    result.append('\x00')
                else:
                    code = ((b1 & 0x1F) << 6) | (b2 & 0x3F)
                    result.append(chr(code))
                i += 2
            elif b1 < 0xF0:
                # 3-byte sequence
                if i + 2 >= len(data):
                    result.append(chr(b1))
                    i += 1
                    continue
                b2 = data[i + 1]
                b3 = data[i + 2]
                code = ((b1 & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
                result.append(chr(code))
                i += 3
            else:
                # 4-byte sequence (rare in MUTF-8, usually surrogates instead)
                if i + 3 >= len(data):
                    result.append(chr(b1))
                    i += 1
                    continue
                b2 = data[i + 1]
                b3 = data[i + 2]
                b4 = data[i + 3]
                code = ((b1 & 0x07) << 18) | ((b2 & 0x3F) << 12) | ((b3 & 0x3F) << 6) | (b4 & 0x3F)
                result.append(chr(code))
                i += 4
        return ''.join(result)
    
    def _parse_types(self, dex: SingleDexData):
        """Parse type table for a DEX."""
        dex.types = []
        for i in range(dex.type_ids_size):
            off = dex.type_ids_off + (i * 4)
            desc_idx = struct.unpack('<I', dex.dex_data[off:off+4])[0]
            dex.types.append(dex.strings[desc_idx])
    
    def _parse_protos(self, dex: SingleDexData):
        """Parse prototype table for a DEX."""
        dex.protos = []
        for i in range(dex.proto_ids_size):
            off = dex.proto_ids_off + (i * 12)
            shorty_idx = struct.unpack('<I', dex.dex_data[off:off+4])[0]
            return_type_idx = struct.unpack('<I', dex.dex_data[off+4:off+8])[0]
            params_off = struct.unpack('<I', dex.dex_data[off+8:off+12])[0]
            
            dex.protos.append({
                'shorty': dex.strings[shorty_idx],
                'return_type': dex.types[return_type_idx],
                'params_off': params_off
            })
    
    def _parse_methods(self, dex: SingleDexData):
        """Parse method table for a DEX."""
        dex.methods = []
        for i in range(dex.method_ids_size):
            off = dex.method_ids_off + (i * 8)
            class_idx = struct.unpack('<H', dex.dex_data[off:off+2])[0]
            proto_idx = struct.unpack('<H', dex.dex_data[off+2:off+4])[0]
            name_idx = struct.unpack('<I', dex.dex_data[off+4:off+8])[0]
            
            dex.methods.append({
                'class': dex.types[class_idx],
                'name': dex.strings[name_idx],
                'proto': dex.protos[proto_idx]
            })
    
    def _build_unified_index(self):
        """Build unified lookup tables across all DEX files."""
        global_offset = 0
        
        for dex_idx, dex in enumerate(self.dex_files):
            self._dex_method_offsets.append(global_offset)
            
            # Map each method to global index
            for local_idx in range(len(dex.methods)):
                global_idx = global_offset + local_idx
                self._method_index_map[global_idx] = (dex_idx, local_idx)
            
            # Aggregate for legacy compatibility
            self.strings.extend(dex.strings)
            self.types.extend(dex.types)
            self.protos.extend(dex.protos)
            self.methods.extend(dex.methods)
            
            global_offset += len(dex.methods)
    
    def _resolve_method_idx(self, method_idx: int) -> Tuple[SingleDexData, int]:
        """Resolve a global method index to (DEX, local_index)."""
        if method_idx in self._method_index_map:
            dex_idx, local_idx = self._method_index_map[method_idx]
            return self.dex_files[dex_idx], local_idx
        
        # Fallback: find which DEX contains this index
        for i, offset in enumerate(self._dex_method_offsets):
            dex = self.dex_files[i]
            if method_idx < offset + len(dex.methods):
                return dex, method_idx - offset
        
        raise ValueError(f"Method index {method_idx} out of range")
    
    # =========================================================================
    # Legacy API compatibility (single-DEX style)
    # =========================================================================
    
    @property
    def dex_data(self) -> bytes:
        """Legacy: return first DEX data."""
        return self.dex_files[0].dex_data if self.dex_files else b''
    
    @property 
    def string_ids_size(self) -> int:
        return self.dex_files[0].string_ids_size if self.dex_files else 0
    
    @property
    def string_ids_off(self) -> int:
        return self.dex_files[0].string_ids_off if self.dex_files else 0
    
    @property
    def class_defs_size(self) -> int:
        return sum(dex.class_defs_size for dex in self.dex_files)
    
    @property
    def class_defs_off(self) -> int:
        return self.dex_files[0].class_defs_off if self.dex_files else 0
    
    def _read_uleb128(self, offset: int) -> Tuple[int, int]:
        """Legacy: read from first DEX."""
        return self.dex_files[0]._read_uleb128(offset)
    
    # =========================================================================
    # Core API methods
    # =========================================================================
    
    def get_method_bytecode(self, target_method_str: str) -> Tuple[bytes, int]:
        """Get bytecode for a method by its full name.
        
        Args:
            target_method_str: Format "LClass;->method(Sig)Ret"
        
        Returns:
            Tuple of (bytecode, registers_size)
        """
        if '->' not in target_method_str:
            raise ValueError("Format: LClass;->method(Sig)Ret")
        
        target_class, target_name_sig = target_method_str.split('->')
        target_name = target_name_sig.split('(')[0]
        
        # Search across all DEX files
        for dex_idx, dex in enumerate(self.dex_files):
            method_idx = -1
            for i, m in enumerate(dex.methods):
                if m['class'] == target_class and m['name'] == target_name:
                    method_idx = i
                    break
            
            if method_idx == -1:
                continue  # Try next DEX
            
            # Find code in this DEX's class definitions
            for i in range(dex.class_defs_size):
                off = dex.class_defs_off + (i * 32)
                class_idx = struct.unpack('<I', dex.dex_data[off:off+4])[0]
                
                if dex.types[class_idx] != target_class:
                    continue
                
                class_data_off = struct.unpack('<I', dex.dex_data[off+24:off+28])[0]
                if class_data_off == 0:
                    continue
                
                return self._find_code_in_class_data(dex, class_data_off, method_idx)
        
        raise ValueError(f"Method {target_method_str} not found in any DEX file")
    
    def _find_code_in_class_data(self, dex: SingleDexData, offset: int, target_method_idx: int) -> Tuple[bytes, int]:
        """Find method bytecode in class data."""
        pos = offset
        static_fields_size, count = dex._read_uleb128(pos); pos += count
        instance_fields_size, count = dex._read_uleb128(pos); pos += count
        direct_methods_size, count = dex._read_uleb128(pos); pos += count
        virtual_methods_size, count = dex._read_uleb128(pos); pos += count
        
        # Skip fields
        for _ in range(static_fields_size):
            _, c = dex._read_uleb128(pos); pos += c
            _, c = dex._read_uleb128(pos); pos += c
        for _ in range(instance_fields_size):
            _, c = dex._read_uleb128(pos); pos += c
            _, c = dex._read_uleb128(pos); pos += c
        
        # Check direct methods
        prev_idx = 0
        for _ in range(direct_methods_size):
            idx_diff, c = dex._read_uleb128(pos); pos += c
            method_idx = prev_idx + idx_diff
            prev_idx = method_idx
            
            access_flags, c = dex._read_uleb128(pos); pos += c
            code_off, c = dex._read_uleb128(pos); pos += c
            
            if method_idx == target_method_idx:
                return self._read_code_item(dex, code_off)
        
        # Check virtual methods
        prev_idx = 0
        for _ in range(virtual_methods_size):
            idx_diff, c = dex._read_uleb128(pos); pos += c
            method_idx = prev_idx + idx_diff
            prev_idx = method_idx
            
            access_flags, c = dex._read_uleb128(pos); pos += c
            code_off, c = dex._read_uleb128(pos); pos += c
            
            if method_idx == target_method_idx:
                return self._read_code_item(dex, code_off)
        
        raise ValueError("Method body not found in class data")
    
    def _read_code_item(self, dex: SingleDexData, offset: int) -> Tuple[bytes, int]:
        """Read bytecode from code_item structure."""
        if offset == 0:
            return b'', 0
        
        regs_size = struct.unpack('<H', dex.dex_data[offset:offset+2])[0]
        insns_size = struct.unpack('<I', dex.dex_data[offset+12:offset+16])[0]
        
        insns_start = offset + 16
        insns_bytes_len = insns_size * 2
        
        bytecode = dex.dex_data[insns_start:insns_start + insns_bytes_len]
        return bytecode, regs_size
    
    def get_method_name(self, method_idx: int) -> str:
        """Get full method name by global method index."""
        if method_idx >= len(self.methods):
            return f"method_{method_idx}"
        m = self.methods[method_idx]
        return f"{m['class']}->{m['name']}"
    
    def iter_all_methods(self):
        """Yields (method_name, bytecode, regs_size) for all defined methods."""
        for dex in self.dex_files:
            for i in range(dex.class_defs_size):
                off = dex.class_defs_off + (i * 32)
                class_idx = struct.unpack('<I', dex.dex_data[off:off+4])[0]
                class_name = dex.types[class_idx]
                
                class_data_off = struct.unpack('<I', dex.dex_data[off+24:off+28])[0]
                if class_data_off == 0:
                    continue
                
                pos = class_data_off
                static_fields_size, count = dex._read_uleb128(pos); pos += count
                instance_fields_size, count = dex._read_uleb128(pos); pos += count
                direct_methods_size, count = dex._read_uleb128(pos); pos += count
                virtual_methods_size, count = dex._read_uleb128(pos); pos += count
                
                # Skip fields
                for _ in range(static_fields_size):
                    _, c = dex._read_uleb128(pos); pos += c
                    _, c = dex._read_uleb128(pos); pos += c
                for _ in range(instance_fields_size):
                    _, c = dex._read_uleb128(pos); pos += c
                    _, c = dex._read_uleb128(pos); pos += c
                
                prev_idx = 0
                for _ in range(direct_methods_size):
                    idx_diff, c = dex._read_uleb128(pos); pos += c
                    method_idx = prev_idx + idx_diff
                    prev_idx = method_idx
                    access_flags, c = dex._read_uleb128(pos); pos += c
                    code_off, c = dex._read_uleb128(pos); pos += c
                    
                    if code_off > 0:
                        name = f"{class_name}->{dex.methods[method_idx]['name']}"
                        code, regs = self._read_code_item(dex, code_off)
                        yield name, code, regs
                
                prev_idx = 0
                for _ in range(virtual_methods_size):
                    idx_diff, c = dex._read_uleb128(pos); pos += c
                    method_idx = prev_idx + idx_diff
                    prev_idx = method_idx
                    access_flags, c = dex._read_uleb128(pos); pos += c
                    code_off, c = dex._read_uleb128(pos); pos += c
                    
                    if code_off > 0:
                        name = f"{class_name}->{dex.methods[method_idx]['name']}"
                        code, regs = self._read_code_item(dex, code_off)
                        yield name, code, regs
    
    def get_dex_count(self) -> int:
        """Return number of DEX files loaded."""
        return len(self.dex_files)
    
    def get_dex_names(self) -> List[str]:
        """Return list of DEX file names."""
        return [dex.dex_name for dex in self.dex_files]
