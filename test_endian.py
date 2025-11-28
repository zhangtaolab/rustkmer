#!/usr/bin/env python3
import struct

# Test little-endian vs big-endian
count = 1

# What little-endian should look like
little_endian_bytes = count.to_bytes(4, 'little')
big_endian_bytes = count.to_bytes(4, 'big')

print(f"Count: {count}")
print(f"Little-endian bytes: {little_endian_bytes.hex()}")  # Should be 01000000
print(f"Big-endian bytes: {big_endian_bytes.hex()}")      # Should be 00000001

# Test reading
print(f"\nReading little-endian bytes as little-endian: {struct.unpack('<I', little_endian_bytes)[0]}")
print(f"Reading big-endian bytes as little-endian: {struct.unpack('<I', big_endian_bytes)[0]}")

# The actual problem
actual_bytes = bytes.fromhex('00000001')  # What's in our database
print(f"\nActual bytes in database: {actual_bytes.hex()}")
print(f"Reading as little-endian: {struct.unpack('<I', actual_bytes)[0]}")  # This gives 16777216
print(f"Reading as big-endian: {struct.unpack('>I', actual_bytes)[0]}")    # This gives 1