use std::io::{Write, Cursor};
use byteorder::{LittleEndian, WriteBytesExt, ReadBytesExt};

fn main() {
    let mut buffer = Vec::new();

    // Write count 1 using same method as count.rs
    buffer.write_u32::<LittleEndian>(1).unwrap();

    println!("Buffer bytes: {:02x?}", buffer);
    println!("Buffer hex: {}", hex::encode(&buffer));

    // Test reading it back
    let mut cursor = Cursor::new(&buffer);
    let count = cursor.read_u32::<LittleEndian>().unwrap();

    println!("Read count: {}", count);

    // Check if 1 in little-endian should be what we expect
    println!("1 as little-endian bytes: {:02x?}", 1u32.to_le_bytes());
    println!("1 as big-endian bytes: {:02x?}", 1u32.to_be_bytes());
}