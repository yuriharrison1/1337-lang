"""Tests for binary codec."""

import pytest
from leet import Cogon
from leet.codec import (
    encode_cogon, decode_cogon, 
    get_binary_size, compare_sizes,
    _float_to_uint8, _uint8_to_float
)


class TestQuantization:
    """Test float <-> uint8 quantization."""
    
    def test_float_to_uint8_zero(self):
        assert _float_to_uint8(0.0) == 0
    
    def test_float_to_uint8_one(self):
        assert _float_to_uint8(1.0) == 255
    
    def test_float_to_uint8_half(self):
        assert _float_to_uint8(0.5) == 127
    
    def test_float_to_uint8_clamp_high(self):
        assert _float_to_uint8(1.5) == 255
    
    def test_float_to_uint8_clamp_low(self):
        assert _float_to_uint8(-0.5) == 0
    
    def test_uint8_to_float_zero(self):
        assert _uint8_to_float(0) == 0.0
    
    def test_uint8_to_float_255(self):
        assert _uint8_to_float(255) == 1.0
    
    def test_roundtrip_approximate(self):
        """Quantização é aproximada devido à precisão limitada."""
        original = 0.734
        quantized = _float_to_uint8(original)
        recovered = _uint8_to_float(quantized)
        # Tolerância de 1/255 (~0.4%)
        assert abs(original - recovered) < 0.004


class TestBinaryCodec:
    """Test binary encoding/decoding."""
    
    def test_encode_size(self):
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        data = encode_cogon(cogon)
        assert len(data) == get_binary_size(cogon)
        assert len(data) == 96  # 4 header + 88 payload + 4 checksum
    
    def test_decode_roundtrip(self):
        original = Cogon.new(
            sem=[i / 31.0 for i in range(32)],  # 0.0 to 1.0
            unc=[0.1] * 32
        )
        data = encode_cogon(original)
        recovered = decode_cogon(data)
        
        assert recovered.id == original.id
        # Valores devem ser aproximados devido à quantização
        for i in range(32):
            assert abs(recovered.sem[i] - original.sem[i]) < 0.004
            assert abs(recovered.unc[i] - original.unc[i]) < 0.004
    
    def test_decode_invalid_magic(self):
        with pytest.raises(ValueError, match="Invalid magic"):
            decode_cogon(b'\x00\x00' + b'\x00' * 94)
    
    def test_decode_invalid_checksum(self):
        """Test that corrupted data is detected via checksum."""
        original = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        data = bytearray(encode_cogon(original))
        # Corrupt a byte in the payload
        data[10] ^= 0xFF
        
        with pytest.raises(ValueError, match="Checksum mismatch"):
            decode_cogon(bytes(data))
    
    def test_decode_invalid_size(self):
        with pytest.raises(ValueError, match="Invalid data size"):
            decode_cogon(b'\x13\x37' + b'\x00' * 10)
    
    def test_cogon_zero_roundtrip(self):
        zero = Cogon.zero()
        data = encode_cogon(zero)
        recovered = decode_cogon(data)
        
        assert recovered.is_zero()
        assert recovered.sem == [1.0] * 32
        assert recovered.unc == [0.0] * 32
        assert recovered.stamp == 0


class TestSizeComparison:
    """Test size comparison between JSON and binary."""
    
    def test_binary_smaller_than_json(self):
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        comparison = compare_sizes(cogon)
        
        assert comparison["binary_bytes"] < comparison["json_bytes"]
        assert comparison["compression_ratio"] > 4.0  # At least 4:1 compression
    
    def test_space_saved_positive(self):
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        comparison = compare_sizes(cogon)
        
        assert comparison["space_saved_percent"] > 70  # At least 70% savings


class TestCogonMethods:
    """Test Cogon.to_bytes() and Cogon.from_bytes()."""
    
    def test_to_bytes_method(self):
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        data = cogon.to_bytes()
        assert len(data) == 96  # 4 header + 88 payload + 4 checksum
    
    def test_from_bytes_method(self):
        original = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        data = original.to_bytes()
        recovered = Cogon.from_bytes(data)
        
        assert recovered.id == original.id
