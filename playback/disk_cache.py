"""Bounded local media cache for high-latency network sources."""

from __future__ import absolute_import

import hashlib
import glob
import os
import re
import shutil
import time

from PySide6 import QtCore

from playback.reader import MovieReader


class CacheWorker(QtCore.QThread):
    progress = QtCore.Signal(str, int)
    cached = QtCore.Signal(str, str)
    failed = QtCore.Signal(str, str)

    def __init__(self, source, destination, bytes_per_second, parent=None):
        super().__init__(parent)
        self.source = source
        self.destination = destination
        self.partial = f"{destination}.part"
        self.bytes_per_second = max(1, int(bytes_per_second))
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            total = os.path.getsize(self.source)
            copied = os.path.getsize(self.partial) if os.path.isfile(self.partial) else 0
            if copied > total:
                os.remove(self.partial)
                copied = 0

            mode = "ab" if copied else "wb"
            last_percent = -1
            started = time.perf_counter()
            initial_bytes = copied

            with open(self.source, "rb", buffering=4 * 1024 * 1024) as source_file:
                source_file.seek(copied)
                with open(self.partial, mode, buffering=4 * 1024 * 1024) as target_file:
                    while not self.cancelled:
                        chunk = source_file.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        target_file.write(chunk)
                        copied += len(chunk)

                        percent = min(100, int(copied * 100 / max(total, 1)))
                        if percent >= last_percent + 2 or percent == 100:
                            last_percent = percent
                            self.progress.emit(self.source, percent)

                        expected = (copied - initial_bytes) / self.bytes_per_second
                        delay = expected - (time.perf_counter() - started)
                        if delay > 0:
                            time.sleep(min(delay, 0.2))

            if self.cancelled:
                return

            if copied != total:
                raise IOError(f"Incomplete cache copy ({copied}/{total} bytes)")

            os.replace(self.partial, self.destination)
            self.progress.emit(self.source, 100)
            self.cached.emit(self.source, self.destination)
        except Exception as error:
            self.failed.emit(self.source, str(error))


class SequenceCacheWorker(QtCore.QThread):
    """Copy a complete image sequence into one atomic cache entry."""

    progress = QtCore.Signal(str, int)
    cached = QtCore.Signal(str, str)
    failed = QtCore.Signal(str, str)

    def __init__(self, source, files, destination, local_pattern, bytes_per_second, parent=None):
        super().__init__(parent)
        self.source = source
        self.files = files
        self.destination = destination
        self.local_pattern = local_pattern
        self.partial = f"{destination}.partial"
        self.bytes_per_second = max(1, int(bytes_per_second))
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            if os.path.isdir(self.partial):
                shutil.rmtree(self.partial, ignore_errors=True)
            os.makedirs(self.partial, exist_ok=True)
            total = sum(os.path.getsize(path) for path in self.files)
            copied = 0
            started = time.perf_counter()
            for source_file in self.files:
                if self.cancelled:
                    return
                target = os.path.join(self.partial, os.path.basename(source_file))
                with open(source_file, "rb", buffering=4 * 1024 * 1024) as src, open(
                    target, "wb", buffering=4 * 1024 * 1024
                ) as dst:
                    while not self.cancelled:
                        chunk = src.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                        copied += len(chunk)
                        self.progress.emit(
                            self.source, min(99, int(copied * 100 / max(1, total)))
                        )
                        expected = copied / self.bytes_per_second
                        delay = expected - (time.perf_counter() - started)
                        if delay > 0:
                            time.sleep(min(delay, 0.2))
            if self.cancelled:
                return
            with open(os.path.join(self.partial, ".complete"), "w", encoding="utf-8") as marker:
                marker.write(str(len(self.files)))
            if os.path.isdir(self.destination):
                shutil.rmtree(self.destination, ignore_errors=True)
            os.replace(self.partial, self.destination)
            self.progress.emit(self.source, 100)
            self.cached.emit(self.source, self.local_pattern)
        except Exception as error:
            self.failed.emit(self.source, str(error))


class MediaCache(QtCore.QObject):
    progress = QtCore.Signal(str, int)
    ready = QtCore.Signal(str, str)
    failed = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        local_app_data = os.getenv("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        self.root = os.getenv("FRAMEDECK_MEDIA_CACHE") or os.path.join(
            local_app_data, "FrameDeck", "media-cache"
        )
        os.makedirs(self.root, exist_ok=True)

        saved_cache_gb = QtCore.QSettings("FrameDeck", "FrameDeck").value(
            "cache/max_gb", 20.0, type=float
        )
        cache_gb = float(os.getenv("FRAMEDECK_CACHE_GB", saved_cache_gb))
        cache_mbps = float(os.getenv("FRAMEDECK_CACHE_MBPS", "32"))
        self.max_bytes = max(1, int(cache_gb * 1024**3))
        self.bytes_per_second = max(1, int(cache_mbps * 1024**2))
        self.workers = dict()
        self.active_path = None

    def set_active(self, playback_path):
        path = os.path.abspath(playback_path) if playback_path else ""
        root = os.path.abspath(self.root) + os.sep
        self.active_path = path if path.startswith(root) else None

    def _cache_path(self, source):
        stat = os.stat(source)
        fingerprint = (
            f"{os.path.normcase(os.path.abspath(source))}|"
            f"{stat.st_size}|{stat.st_mtime_ns}"
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        extension = os.path.splitext(source)[1].lower() or ".media"
        return os.path.join(self.root, f"{digest}{extension}"), stat.st_size

    @staticmethod
    def _sequence_files(pattern):
        wildcard = re.sub(r"#+", "*", pattern)
        return sorted(path for path in glob.glob(wildcard) if os.path.isfile(path))

    def _sequence_cache_info(self, pattern):
        files = self._sequence_files(pattern)
        if not files:
            raise OSError(f"No frames found for sequence: {pattern}")
        stats = [os.stat(path) for path in files]
        fingerprint = (
            f"{os.path.normcase(os.path.abspath(pattern))}|{len(files)}|"
            f"{sum(stat.st_size for stat in stats)}|{stats[0].st_mtime_ns}|"
            f"{stats[-1].st_mtime_ns}"
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        destination = os.path.join(self.root, "sequences", digest)
        local_pattern = os.path.join(destination, os.path.basename(pattern))
        total = sum(stat.st_size for stat in stats)
        return files, destination, local_pattern, total

    def resolve(self, source):
        """Return a valid local cache file, otherwise the original source."""
        if not source:
            return source

        if "#" in source:
            try:
                files, destination, local_pattern, _total = self._sequence_cache_info(source)
            except OSError:
                return source
            marker = os.path.join(destination, ".complete")
            local_files = self._sequence_files(local_pattern)
            if os.path.isfile(marker) and len(local_files) == len(files):
                try:
                    os.utime(marker, None)
                except OSError:
                    pass
                return local_pattern
            return source

        if not MovieReader._is_network_path(source):
            return source

        try:
            cache_path, source_size = self._cache_path(source)
        except OSError:
            return source

        if os.path.isfile(cache_path) and os.path.getsize(cache_path) == source_size:
            try:
                os.utime(cache_path, None)
            except OSError:
                pass
            return cache_path
        return source

    def cache(self, source):
        """Start a rate-limited background cache copy when needed."""
        if not source:
            return

        source = os.path.abspath(source)
        if source in self.workers:
            return

        is_sequence = "#" in source
        if not is_sequence and not MovieReader._is_network_path(source):
            self.failed.emit(source, "Local video does not need disk cache")
            return

        resolved = self.resolve(source)
        if resolved != source:
            self.progress.emit(source, 100)
            self.ready.emit(source, resolved)
            return

        try:
            if is_sequence:
                files, destination, local_pattern, source_size = self._sequence_cache_info(source)
            else:
                destination, source_size = self._cache_path(source)
        except OSError as error:
            self.failed.emit(source, str(error))
            return

        if source_size > self.max_bytes:
            self.failed.emit(source, "File is larger than the configured cache limit")
            return

        self.prune(required_bytes=source_size)
        free_bytes = shutil.disk_usage(self.root).free
        if free_bytes < source_size + 512 * 1024**2:
            self.failed.emit(source, "Not enough free disk space for media cache")
            return

        if is_sequence:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            worker = SequenceCacheWorker(
                source,
                files,
                destination,
                local_pattern,
                self.bytes_per_second,
                self,
            )
        else:
            worker = CacheWorker(source, destination, self.bytes_per_second, self)
        self.workers[source] = worker
        worker.progress.connect(self.progress)
        worker.cached.connect(self.ready)
        worker.failed.connect(self.failed)
        worker.finished.connect(lambda source=source: self.workers.pop(source, None))
        worker.start(QtCore.QThread.Priority.LowPriority)

    def prune(self, required_bytes=0):
        """Evict least-recently-used complete/partial files within the limit."""
        protected = {
            worker.destination for worker in self.workers.values()
        } | {worker.partial for worker in self.workers.values()}
        entries = list()
        total = 0
        for directory, _folders, names in os.walk(self.root):
            for name in names:
                path = os.path.join(directory, name)
                if not os.path.isfile(path):
                    continue
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                total += stat.st_size
                if not any(path.startswith(value) for value in protected):
                    entries.append((stat.st_atime, stat.st_mtime, stat.st_size, path))

        target = max(0, self.max_bytes - max(0, int(required_bytes)))
        for _, _, size, path in sorted(entries):
            if total <= target:
                break
            try:
                os.remove(path)
                total -= size
            except OSError:
                pass

    def size_bytes(self):
        total = 0
        for directory, _folders, names in os.walk(self.root):
            for name in names:
                path = os.path.join(directory, name)
                try:
                    total += os.path.getsize(path)
                except OSError:
                    pass
        return total

    def file_count(self):
        return sum(len(files) for _root, _folders, files in os.walk(self.root))

    def clear(self):
        """Delete all inactive cache entries."""
        if self.workers or self.active_path:
            return False
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError:
                pass
        return True

    def shutdown(self):
        for worker in list(self.workers.values()):
            worker.cancel()
        for worker in list(self.workers.values()):
            worker.wait(2000)
