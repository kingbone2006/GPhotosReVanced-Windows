"""Multi-core CPU Hash Pool for Google Photos ReVanced Windows Edition.
Offloads CPU-intensive SHA-1 hashing to a dedicated ProcessPoolExecutor across all CPU cores,
completely bypassing the Python GIL and preventing GUI/Upload thread starvation.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Union
from concurrent.futures import ProcessPoolExecutor, Future
import logging

logger = logging.getLogger(__name__)


def _compute_sha1_process_worker(path_str: str) -> str:
    """Standalone worker function executed inside dedicated OS process on separate CPU cores."""
    sha1 = hashlib.sha1()
    # 2MB buffered reading for blazing fast NVMe/SSD sequential throughput
    with open(path_str, "rb", buffering=2 * 1024 * 1024) as f:
        while chunk := f.read(2 * 1024 * 1024):
            sha1.update(chunk)
    return sha1.hexdigest()


class MultiCoreHashPool:
    """Manages a pool of worker processes to calculate cryptographic hashes across all CPU cores."""

    _instance: Optional["MultiCoreHashPool"] = None

    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            # Reserve 1-2 cores for OS/GUI, use remaining for heavy hashing
            cpu_total = os.cpu_count() or 4
            max_workers = max(2, min(cpu_total, 8))
        self.max_workers = max_workers
        self._executor: Optional[ProcessPoolExecutor] = None

    @classmethod
    def get_instance(cls) -> "MultiCoreHashPool":
        if cls._instance is None:
            cls._instance = MultiCoreHashPool()
        return cls._instance

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def compute_sha1(self, file_path: Union[str, Path]) -> str:
        """Compute SHA-1 hash of a file using multi-core process pool with graceful fallback."""
        path_str = str(file_path)
        try:
            executor = self._get_executor()
            future = executor.submit(_compute_sha1_process_worker, path_str)
            return future.result()
        except Exception as e:
            logger.debug("ProcessPool hashing error (%s), falling back to in-thread calculation", e)
            # Graceful in-thread fallback if process execution encounters an issue
            return _compute_sha1_process_worker(path_str)

    def compute_sha1_async(self, file_path: Union[str, Path]) -> Future:
        """Submit SHA-1 calculation to process pool asynchronously."""
        path_str = str(file_path)
        try:
            executor = self._get_executor()
            return executor.submit(_compute_sha1_process_worker, path_str)
        except Exception:
            # Fallback
            from concurrent.futures import Future
            fut: Future = Future()
            try:
                fut.set_result(_compute_sha1_process_worker(path_str))
            except Exception as ex:
                fut.set_exception(ex)
            return fut

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the process pool."""
        if self._executor:
            try:
                self._executor.shutdown(wait=wait, cancel_futures=True)
            except Exception:
                pass
            self._executor = None
