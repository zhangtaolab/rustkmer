use rustkmer::kmer::encoding::encode_kmer;

fn main() {
    let test_seq = "ATGCGATGCTAGC";
    match encode_kmer(test_seq) {
        Ok(encoded) => println!("Encoded {}: {:#b}", test_seq, encoded),
        Err(e) => println!("Error encoding {}: {}", test_seq, e),
    }
}