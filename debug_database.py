#!/usr/bin/env python3
import struct

# Read the database file and examine all entries
with open('test_fresh_sorted.rkdb', 'rb') as f:
    # Read header
    magic = f.read(4)
    version = struct.unpack('<H', f.read(2))[0]
    kmer_size = struct.unpack('B', f.read(1))[0]
    padding1 = f.read(1)  # padding
    padding2 = struct.unpack('<H', f.read(2))[0]  # padding
    total_kmers = struct.unpack('<Q', f.read(8))[0]
    flags = struct.unpack('B', f.read(1))[0]
    padding3 = f.read(7)  # padding
    data_offset = struct.unpack('<Q', f.read(8))[0]
    index_offset = struct.unpack('<Q', f.read(8))[0]

    print(f"Header info:")
    print(f"  Magic: {magic}")
    print(f"  Version: {version}")
    print(f"  K-mer size: {kmer_size}")
    print(f"  Total k-mers: {total_kmers}")
    print(f"  Flags: {flags:08b} (sorted: {bool(flags & 1)}, canonical: {bool(flags & 2)})")
    print(f"  Data offset: {data_offset}")
    print(f"  Index offset: {index_offset}")
    print(f"  Header size should be: 40, actual data_offset: {data_offset}")
    print()

    # Seek to data offset
    f.seek(data_offset)

    # Also check what's at offset 40 (what we expected)
    print("Data at expected offset 40:")
    f.seek(40)
    data_at_40 = f.read(12)
    print(f"  Bytes: {data_at_40.hex()}")
    if len(data_at_40) >= 12:
        kmer_40 = struct.unpack('<Q', data_at_40[:8])[0]
        count_40 = struct.unpack('<I', data_at_40[8:12])[0]
        print(f"  K-mer: 0x{kmer_40:016x}")
        print(f"  Count: {count_40}")
    print()

    # Seek back to data offset
    f.seek(data_offset)

    # Read all entries
    for i in range(total_kmers):
        pos = f.tell()
        data = f.read(12)
        if len(data) < 12:
            break

        kmer_bytes = data[:8]
        count_bytes = data[8:12]

        kmer = struct.unpack('<Q', kmer_bytes)[0]
        count = struct.unpack('<I', count_bytes)[0]

        print(f"Entry {i+1} at offset {pos}:")
        print(f"  K-mer bytes: {kmer_bytes.hex()}")
        print(f"  K-mer value: 0x{kmer:016x}")
        print(f"  Count bytes: {count_bytes.hex()}")
        print(f"  Count value: {count}")
        print(f"  Count value as big-endian: {struct.unpack('>I', count_bytes)[0]}")
        print()