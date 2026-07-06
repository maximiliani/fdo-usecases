# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""HTTP response caching for external API calls.

This module provides a simple file-based cache for HTTP responses to avoid
hitting rate limits on external APIs like Zenodo.

Cache Structure:
    .cache/
        ├── https%3A%2F%2Fzenodo.org%2Fapi%2Frecords%2F12345
        └── ...

Files are named by URL-encoded URL path to ensure uniqueness and filesystem safety.
"""

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)


class HTTPCache:
    """File-based HTTP response cache.

    Caches HTTP responses to disk using URL as filename (URL-encoded).
    Supports TTL-based expiration.
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = 3600):
        """Initialize HTTP cache.

        Args:
            cache_dir: Directory to store cached responses. Defaults to .cache/ in project root.
            ttl_seconds: Time-to-live for cached entries in seconds. Default: 1 hour.

        """
        if cache_dir is None:
            # Find project root (directory containing .git)
            current = Path(__file__).parent
            while current != current.parent and not (current / ".git").exists():
                current = current.parent

            cache_dir = current / ".cache"

        self._cache_dir = cache_dir
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

        # Ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"HTTPCache initialized at {self._cache_dir} (TTL: {ttl_seconds}s)")

    def _url_to_filename(self, url: str) -> Path:
        """Convert URL to safe filename using URL encoding.

        Args:
            url: The URL to convert

        Returns:
            Path to cache file

        """
        # URL-encode the entire URL to make it filesystem-safe
        encoded = quote(url, safe="")
        return self._cache_dir / encoded

    def _filename_to_url(self, filename: Path) -> str:
        """Convert cache filename back to URL.

        Args:
            filename: Cache file path

        Returns:
            Original URL

        """
        return unquote(filename.name)

    def get(self, url: str) -> Optional[str]:
        """Get cached response for URL.

        Args:
            url: The URL to lookup

        Returns:
            Cached content as string, or None if not found/expired

        """
        cache_file = self._url_to_filename(url)

        if not cache_file.exists():
            self._misses += 1
            logger.debug(f"Cache miss: {url}")
            return None

        # Check TTL
        try:
            mtime = cache_file.stat().st_mtime
            import time

            age = time.time() - mtime

            if age > self._ttl_seconds:
                logger.debug(
                    f"Cache expired ({age:.0f}s > {self._ttl_seconds}s): {url}"
                )
                cache_file.unlink(missing_ok=True)
                self._misses += 1
                return None
        except Exception as e:
            logger.warning(f"Error checking cache file age: {e}")
            self._misses += 1
            return None

        # Read cached content
        try:
            content = cache_file.read_text(encoding="utf-8")
            self._hits += 1
            logger.debug(f"Cache hit: {url}")
            return content
        except Exception as e:
            logger.warning(f"Error reading cache file {cache_file}: {e}")
            cache_file.unlink(missing_ok=True)
            self._misses += 1
            return None

    def set(self, url: str, content: str) -> None:
        """Cache HTTP response.

        Args:
            url: The URL being cached
            content: Response content to cache

        """
        cache_file = self._url_to_filename(url)

        try:
            # Write atomically (write to temp, then rename)
            temp_file = cache_file.with_suffix(".tmp")
            temp_file.write_text(content, encoding="utf-8")
            temp_file.rename(cache_file)
            logger.debug(f"Cached: {url} -> {cache_file.name[:50]}...")
        except Exception as e:
            logger.error(f"Error writing cache file {cache_file}: {e}")

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of files deleted

        """
        count = 0
        for cache_file in self._cache_dir.glob("*"):
            if cache_file.is_file():
                cache_file.unlink()
                count += 1

        logger.info(f"Cleared {count} cached entries")
        return count

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, and size_bytes

        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        # Calculate cache size
        size_bytes = sum(
            f.stat().st_size for f in self._cache_dir.glob("*") if f.is_file()
        )

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size_bytes": size_bytes,
            "size_mb": f"{size_bytes / (1024 * 1024):.2f} MB",
        }

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of files deleted

        """
        import time

        count = 0
        current_time = time.time()

        for cache_file in self._cache_dir.glob("*"):
            if cache_file.is_file():
                try:
                    age = current_time - cache_file.stat().st_mtime
                    if age > self._ttl_seconds:
                        cache_file.unlink()
                        count += 1
                except Exception as e:
                    logger.debug(f"Error cleaning up {cache_file}: {e}")

        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")

        return count


# Global cache instance for reuse
_cache_instance: Optional[HTTPCache] = None


def get_cache(ttl_seconds: int = 3600) -> HTTPCache:
    """Get or create global HTTP cache instance.

    Args:
        ttl_seconds: TTL for cache entries

    Returns:
        HTTPCache instance

    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = HTTPCache(ttl_seconds=ttl_seconds)
    return _cache_instance
