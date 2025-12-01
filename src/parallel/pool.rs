//! Thread pool utilities for parallel processing
//!
//! Provides a reusable thread pool for k-mer counting operations.

use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::sync::mpsc::{channel, Sender, Receiver};
use crate::error::{ProcessingError, ProcessingResult};

/// A task that can be executed by the thread pool
pub trait Task: Send + Sync + 'static {
    /// Execute the task
    fn execute(self: Box<Self>) -> ProcessingResult<()>;
}

/// Thread pool for parallel task execution
pub struct ThreadPool {
    /// Worker threads
    workers: Vec<Worker>,
    /// Sender for tasks
    sender: Sender<Box<dyn Task>>,
}

impl ThreadPool {
    /// Create a new thread pool
    ///
    /// # Arguments
    /// * `size` - Number of threads in the pool
    ///
    /// # Returns
    /// New ThreadPool instance
    pub fn new(size: usize) -> ProcessingResult<Self> {
        if size == 0 {
            return Err(ProcessingError::new("Thread pool size must be greater than 0"));
        }

        let (sender, receiver) = channel();
        let receiver = Arc::new(Mutex::new(receiver));

        let mut workers = Vec::with_capacity(size);
        for id in 0..size {
            let worker = Worker::new(id, Arc::clone(&receiver))?;
            workers.push(worker);
        }

        Ok(Self {
            workers,
            sender,
        })
    }

    /// Submit a task to the thread pool
    ///
    /// # Arguments
    /// * `task` - Task to execute
    ///
    /// # Returns
    /// Result indicating submission success
    pub fn submit<T>(&self, task: T) -> ProcessingResult<()>
    where
        T: Task + Send + 'static,
    {
        self.sender.send(Box::new(task))
            .map_err(|e| ProcessingError::with_context("Failed to submit task to thread pool", e))?;
        Ok(())
    }

    /// Get the number of threads in the pool
    pub fn size(&self) -> usize {
        self.workers.len()
    }

    /// Shutdown the thread pool
    pub fn shutdown(mut self) {
        // Drop sender, which will cause receivers to return None
        drop(self.sender);

        // Join all worker threads
        for worker in self.workers.iter_mut() {
            if let Some(handle) = worker.thread.take() {
                let _ = handle.join();
            }
        }
    }
}

/// Worker thread in the thread pool
struct Worker {
    /// Worker ID
    #[allow(dead_code)]
    id: usize,
    /// Thread handle
    thread: Option<JoinHandle<()>>,
}

impl Worker {
    /// Create a new worker thread
    ///
    /// # Arguments
    /// * `id` - Worker ID
    /// * `receiver` - Shared receiver for tasks
    ///
    /// # Returns
    /// New Worker instance
    fn new(id: usize, receiver: Arc<Mutex<Receiver<Box<dyn Task>>>>) -> ProcessingResult<Self> {
        let thread = thread::spawn(move || {
            loop {
                let task = {
                    let receiver = receiver.lock().unwrap();
                    receiver.recv()
                };

                match task {
                    Ok(task) => {
                        if let Err(e) = task.execute() {
                            eprintln!("Worker {} failed to execute task: {}", id, e);
                        }
                    }
                    Err(_) => {
                        // Channel closed, worker should exit
                        break;
                    }
                }
            }
        });

        Ok(Self {
            id,
            thread: Some(thread),
        })
    }
}

/// Simple task for counting k-mers in a sequence
pub struct SequenceCountTask {
    /// Sequence data
    pub sequence: String,
    /// K-mer length
    pub kmer_length: usize,
    /// Whether to use canonical mode
    pub canonical_mode: bool,
    /// Callback for each k-mer found
    pub callback: Box<dyn Fn(u64) + Send + Sync>,
}

impl Task for SequenceCountTask {
    fn execute(self: Box<Self>) -> ProcessingResult<()> {
        use crate::kmer::encoding::encode_kmer;
        use crate::kmer::canonical::canonical_kmer;

        // Extract fields from the boxed task
        let sequence = self.sequence;
        let kmer_length = self.kmer_length;
        let canonical_mode = self.canonical_mode;
        let callback = self.callback;

        // Skip sequences shorter than k
        if sequence.len() < kmer_length {
            return Ok(());
        }

        // Extract and process k-mers
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

                    (callback)(final_kmer);
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

/// Builder for thread pool
pub struct ThreadPoolBuilder {
    size: usize,
}

impl ThreadPoolBuilder {
    /// Create a new thread pool builder
    pub fn new() -> Self {
        Self {
            size: num_cpus::get(),
        }
    }

    /// Set the thread pool size
    pub fn size(mut self, size: usize) -> Self {
        self.size = size;
        self
    }

    /// Build the thread pool
    pub fn build(self) -> ProcessingResult<ThreadPool> {
        ThreadPool::new(self.size)
    }
}

impl Default for ThreadPoolBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    #[test]
    fn test_thread_pool_basic() {
        let pool = ThreadPool::new(2).unwrap();
        let counter = Arc::new(AtomicU64::new(0));

        for i in 0..10 {
            let counter_clone = Arc::clone(&counter);
            let task = SimpleTask {
                value: i,
                callback: Box::new(move |val| {
                    counter_clone.fetch_add(val, Ordering::Relaxed);
                }),
            };

            pool.submit(task).unwrap();
        }

        // Drop pool to wait for all tasks to complete
        pool.shutdown();

        assert_eq!(counter.load(Ordering::Relaxed), 45); // Sum of 0..9
    }

    #[test]
    fn test_sequence_count_task() {
        let counter = Arc::new(AtomicU64::new(0));
        let task = SequenceCountTask {
            sequence: "ATGCATGC".to_string(),
            kmer_length: 3,
            canonical_mode: false,
            callback: Box::new({
                let counter = Arc::clone(&counter);
                move |_| {
                    counter.fetch_add(1, Ordering::Relaxed);
                }
            }),
        };

        Box::new(task).execute().unwrap();
        assert_eq!(counter.load(Ordering::Relaxed), 6); // ATG, TGC, GCA, CAT, ATG, TGC
    }

    #[test]
    fn test_thread_pool_builder() {
        let pool = ThreadPoolBuilder::new()
            .size(4)
            .build()
            .unwrap();

        assert_eq!(pool.size(), 4);
        pool.shutdown();
    }

    /// Simple test task
    struct SimpleTask {
        value: u64,
        callback: Box<dyn Fn(u64) + Send + Sync>,
    }

    impl Task for SimpleTask {
        fn execute(self: Box<Self>) -> ProcessingResult<()> {
            let value = self.value;
            let callback = self.callback;
            (callback)(value);
            Ok(())
        }
    }
}