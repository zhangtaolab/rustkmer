//! Parallel processing utilities for k-mer counting
//!
//! Provides multi-threaded processing of sequence files.

use std::sync::{Arc, Mutex};
use std::thread;
use std::sync::mpsc::channel;
use rayon::prelude::*;
use crate::error::{ProcessingError, ProcessingResult};
use crate::hash::table::KmerCounter;
use crate::kmer::encoding::encode_kmer;
use crate::kmer::canonical::canonical_kmer;

/// Parallel sequence processor
pub struct ParallelProcessor {
    /// Number of worker threads
    #[allow(dead_code)]
    num_threads: usize,
    /// Shared k-mer counter
    counter: Arc<KmerCounter>,
    /// K-mer length
    kmer_length: usize,
    /// Whether to use canonical mode
    canonical_mode: bool,
}

impl ParallelProcessor {
    /// Create a new parallel processor
    ///
    /// # Arguments
    /// * `counter` - Shared k-mer counter
    /// * `kmer_length` - Length of k-mers
    /// * `canonical_mode` - Whether to use canonical mode
    /// * `num_threads` - Number of threads to use
    ///
    /// # Returns
    /// New ParallelProcessor instance
    pub fn new(
        counter: Arc<KmerCounter>,
        kmer_length: usize,
        canonical_mode: bool,
        num_threads: usize,
    ) -> Self {
        Self {
            num_threads,
            counter,
            kmer_length,
            canonical_mode,
        }
    }

    /// Process sequences in parallel
    ///
    /// # Arguments
    /// * `sequences` - Iterator of sequence strings
    ///
    /// # Returns
    /// Processing result
    pub fn process_sequences<I>(&self, sequences: I) -> ProcessingResult<()>
    where
        I: IntoIterator<Item = String> + Send + 'static,
        I::IntoIter: Send,
    {
        let sequences: Vec<String> = sequences.into_iter().collect();

        // Process sequences in parallel using Rayon
        sequences.into_par_iter().try_for_each(|sequence| {
            self.process_single_sequence(&sequence)
        })
    }

    /// Process a single sequence
    ///
    /// # Arguments
    /// * `sequence` - DNA sequence
    ///
    /// # Returns
    /// Processing result
    fn process_single_sequence(&self, sequence: &str) -> ProcessingResult<()> {
        // Skip sequences shorter than k
        if sequence.len() < self.kmer_length {
            return Ok(());
        }

        // Extract and count k-mers
        for i in 0..=(sequence.len() - self.kmer_length) {
            let kmer_seq = &sequence[i..i + self.kmer_length];

            match encode_kmer(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if self.canonical_mode {
                        match canonical_kmer(encoded_kmer, self.kmer_length) {
                            Ok(canonical) => canonical,
                            Err(_) => continue, // Skip invalid k-mers
                        }
                    } else {
                        encoded_kmer
                    };

                    self.counter.increment(final_kmer).map_err(|e| {
                        ProcessingError::with_context("Failed to increment k-mer count", e)
                    })?;
                },
                Err(_) => {
                    // Skip k-mers with invalid characters (N, etc.)
                    continue;
                }
            }
        }

        Ok(())
    }

    /// Get processing statistics
    pub fn get_stats(&self) -> crate::hash::table::CounterStats {
        self.counter.get_stats()
    }
}

/// Work item for parallel processing
pub struct WorkItem {
    /// Sequence identifier
    pub id: String,
    /// Sequence data
    pub sequence: String,
}

/// Parallel processor using work queue
pub struct QueueProcessor {
    /// Number of worker threads
    #[allow(dead_code)]
    num_threads: usize,
    /// Shared k-mer counter
    counter: Arc<KmerCounter>,
    /// K-mer length
    kmer_length: usize,
    /// Whether to use canonical mode
    canonical_mode: bool,
}

impl QueueProcessor {
    /// Create a new queue-based processor
    pub fn new(
        counter: Arc<KmerCounter>,
        kmer_length: usize,
        canonical_mode: bool,
        num_threads: usize,
    ) -> Self {
        Self {
            num_threads,
            counter,
            kmer_length,
            canonical_mode,
        }
    }

    /// Process work items using a queue
    ///
    /// # Arguments
    /// * `work_items` - Iterator of work items
    ///
    /// # Returns
    /// Processing result
    pub fn process_work_items<I>(&self, work_items: I) -> ProcessingResult<()>
    where
        I: IntoIterator<Item = WorkItem> + Send + 'static,
        I::IntoIter: Send,
    {
        let (sender, receiver) = channel::<WorkItem>();
        let receiver = Arc::new(Mutex::new(receiver));
        let counter = Arc::clone(&self.counter);
        let kmer_length = self.kmer_length;
        let canonical_mode = self.canonical_mode;

        // Spawn worker threads
        let mut handles = Vec::new();
        for _ in 0..self.num_threads {
            let receiver_clone = Arc::clone(&receiver);
            let counter_clone = Arc::clone(&counter);

            let handle = thread::spawn(move || {
                loop {
                    let work_item = {
                        let receiver = receiver_clone.lock().unwrap();
                        receiver.recv()
                    };

                    match work_item {
                        Ok(item) => {
                            if let Err(e) = Self::process_work_item(
                                &counter_clone,
                                &item.sequence,
                                kmer_length,
                                canonical_mode,
                            ) {
                                eprintln!("Error processing work item {}: {}", item.id, e);
                            }
                        },
                        Err(_) => break, // Channel closed
                    }
                }
            });

            handles.push(handle);
        }

        // Drop the main receiver reference
        drop(receiver);

        // Send work items
        for work_item in work_items {
            sender.send(work_item)
                .map_err(|e| ProcessingError::with_context("Failed to send work item", e))?;
        }

        // Drop sender to signal completion
        drop(sender);

        // Wait for all workers to complete
        for handle in handles {
            handle.join()
                .map_err(|e| ProcessingError::new(format!("Worker thread panicked: {:?}", e)))?;
        }

        Ok(())
    }

    /// Process a single work item
    fn process_work_item(
        counter: &KmerCounter,
        sequence: &str,
        kmer_length: usize,
        canonical_mode: bool,
    ) -> ProcessingResult<()> {
        // Skip sequences shorter than k
        if sequence.len() < kmer_length {
            return Ok(());
        }

        // Extract and count k-mers
        for i in 0..=(sequence.len() - kmer_length) {
            let kmer_seq = &sequence[i..i + kmer_length];

            match encode_kmer(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if canonical_mode {
                        match canonical_kmer(encoded_kmer, kmer_length) {
                            Ok(canonical) => canonical,
                            Err(_) => continue, // Skip invalid k-mers
                        }
                    } else {
                        encoded_kmer
                    };

                    counter.increment(final_kmer).map_err(|e| {
                        ProcessingError::with_context("Failed to increment k-mer count", e)
                    })?;
                },
                Err(_) => {
                    // Skip k-mers with invalid characters (N, etc.)
                    continue;
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hash::table::KmerCounter;

    #[test]
    fn test_parallel_processor() {
        let counter = Arc::new(KmerCounter::new(3, false, 1000, 4).unwrap());
        let processor = ParallelProcessor::new(counter.clone(), 3, false, 2);

        let sequences = vec![
            "ATGC".to_string(),
            "GCAT".to_string(),
            "ATAT".to_string(),
        ];

        processor.process_sequences(sequences).unwrap();

        let stats = processor.get_stats();
        assert_eq!(stats.total_kmers, 6); // Each sequence has 2 k-mers of length 3
        assert_eq!(stats.unique_kmers, 4); // ATG, TGC, GCA, CAT, ATA, TAT
    }

    #[test]
    fn test_queue_processor() {
        let counter = Arc::new(KmerCounter::new(3, false, 1000, 2).unwrap());
        let processor = QueueProcessor::new(counter.clone(), 3, false, 2);

        let work_items = vec![
            WorkItem {
                id: "seq1".to_string(),
                sequence: "ATGC".to_string(),
            },
            WorkItem {
                id: "seq2".to_string(),
                sequence: "GCAT".to_string(),
            },
        ];

        processor.process_work_items(work_items).unwrap();

        let stats = counter.get_stats();
        assert_eq!(stats.total_kmers, 4);
        assert!(stats.unique_kmers >= 3);
    }
}