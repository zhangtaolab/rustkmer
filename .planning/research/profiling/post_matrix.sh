#!/bin/sh
# Post-matrix sequential driver (no concurrent CPU loads).
set -x
cd /tmp/rkmer-v2-prof
python3 -I scripts/collect_parity.py
python3 -I scripts/run_profiles.py all
cd /tmp/rkmer-v2-prof/microbench
cargo build --release 2>&1 | tail -2
./target/release/rk-microbench 21 200000 ABCDE
./target/release/rk-microbench 31 200000 ABCDE
./target/release/rk-microbench 21 1000000 BC
cd /tmp/rkmer-v2-prof
python3 -I scripts/verify_threads.py
/usr/bin/time -l /opt/homebrew/bin/jellyfish count -m 21 -s 2G -t 1 -C -o out/jf21-fq-t1.jf data/slice4M.fq 2> logs/jf21-fq-t1.log
echo "POST-MATRIX DONE"