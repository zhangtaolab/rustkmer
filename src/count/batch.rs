//! Partition-tagged batch and acknowledgement messages for the parallel
//! counting engine (Phase 7, plan 07-02).
//!
//! The producer owns one routing buffer per partition and, when a buffer
//! reaches the configured batch size, moves it into a [`CountBatch`] and sends
//! it to the worker that owns that partition. `SyncSender::send` consumes the
//! batch, so the producer never retains a sent `Vec` — there is no clone and no
//! aliasing across the thread boundary.
//!
//! # Ordering guarantee
//!
//! Each worker receives its batches over exactly one `sync_channel`, which is
//! FIFO. A [`CountBatch::Flush`] sent after a batch is therefore processed
//! after that batch, and the matching [`WorkerStat::Flush`] acknowledgement is
//! emitted only once every previously sent batch has been counted. That
//! send/flush/ack sequence is the happens-before edge behind the per-file
//! cumulative statistics.
//!
//! Both enums are `Send` so they can cross the producer/worker boundary; the
//! receiver itself stays owned by one worker thread (never shared, never run on
//! a rayon task).

/// One unit of work for a counting worker.
#[derive(Debug)]
pub enum CountBatch {
    /// `k <= 32`: encoded keys routed to one partition, in observation order.
    Dense {
        /// Owning partition index (`0..partitions`).
        partition: u32,
        /// Encoded `u64` keys routed to that partition.
        keys: Vec<u64>,
    },
    /// `k 33..=64`: encoded keys routed to one partition, in observation order.
    Wide {
        /// Owning partition index (`0..partitions`).
        partition: u32,
        /// Encoded `u128` keys routed to that partition.
        keys: Vec<u128>,
    },
    /// File-boundary barrier: answer with a [`WorkerStat::Flush`] after every
    /// batch previously sent to this worker has been counted.
    Flush {
        /// Monotonic barrier token the acknowledgement must echo.
        token: u64,
    },
}

/// One message back from a counting worker.
#[derive(Debug)]
pub enum WorkerStat {
    /// Cumulative per-worker statistics at a file boundary.
    Flush {
        /// Token echoed from the corresponding [`CountBatch::Flush`].
        token: u64,
        /// Sum of counts over this worker's owned tables (checked).
        total: u64,
        /// Number of distinct keys over this worker's owned tables (checked).
        unique: u64,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_send<T: Send>() {}

    /// Both message types must cross the producer/worker boundary.
    #[test]
    fn batch_and_stat_are_send() {
        assert_send::<CountBatch>();
        assert_send::<WorkerStat>();
    }
}
