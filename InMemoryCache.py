import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict
from flask import Flask, request, jsonify
from datetime import datetime, timedelta


class InMemoryCache:
    """
    A thread-safe in-memory cache with TTL and LRU eviction support.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._lock = threading.RLock()

    def _is_expired(self, item: Dict) -> bool:
        """Check if a cache item has expired."""
        if item['ttl'] is None:
            return False
        return time.time() > item['expires_at']

    def _evict_expired(self):
        """Remove expired items from cache."""
        current_time = time.time()
        expired_keys = []

        for key, item in self._cache.items():
            if item['ttl'] is not None and current_time > item['expires_at']:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def _evict_lru(self):
        """Remove least recently used item if cache is at capacity."""
        if len(self._cache) >= self.max_size:
            # Remove the least recently used item (first item in OrderedDict)
            self._cache.popitem(last=False)

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a key-value pair in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None for no expiration)

        Returns:
            True if successfully stored
        """
        with self._lock:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Calculate expiration time
            expires_at = time.time() + ttl if ttl > 0 else None

            # Remove expired items
            self._evict_expired()

            # If key already exists, remove it (we'll add it back at the end)
            if key in self._cache:
                del self._cache[key]
            else:
                # Check if we need to evict LRU item
                self._evict_lru()

            # Add new item
            self._cache[key] = {
                'value': value,
                'ttl': ttl if ttl > 0 else None,
                'expires_at': expires_at,
                'created_at': time.time()
            }

            return True

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                return None

            item = self._cache[key]

            # Check if expired
            if self._is_expired(item):
                del self._cache[key]
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(key)

            return item['value']

    def delete(self, key: str) -> bool:
        """
        Remove a key from the cache.

        Args:
            key: Cache key

        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all items from the cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get the current number of items in cache."""
        with self._lock:
            self._evict_expired()
            return len(self._cache)

    def stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            self._evict_expired()
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'default_ttl': self.default_ttl
            }


# Initialize Flask app and cache
app = Flask(__name__)
cache = InMemoryCache(max_size=1000, default_ttl=3600)  # 1 hour default TTL


@app.route('/cache/<key>', methods=['GET'])
def get_cache_item(key):
    """
    GET endpoint to retrieve a value from cache.

    Returns:
        JSON response with value or error message
    """
    try:
        value = cache.get(key)

        if value is None:
            return jsonify({
                'error': 'Key not found or expired',
                'key': key
            }), 404

        return jsonify({
            'key': key,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/cache/<key>', methods=['PUT'])
def put_cache_item(key):
    """
    PUT endpoint to store a value in cache.

    Expected JSON body:
    {
        "value": "any_value",
        "ttl": 3600  // optional, time-to-live in seconds
    }

    Returns:
        JSON response with success message or error
    """
    try:
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json'
            }), 400

        data = request.get_json()

        if 'value' not in data:
            return jsonify({
                'error': 'Missing required field: value'
            }), 400

        value = data['value']
        ttl = data.get('ttl', None)  # Use cache default if not specified

        # Validate TTL if provided
        if ttl is not None:
            if not isinstance(ttl, int) or ttl < 0:
                return jsonify({
                    'error': 'TTL must be a non-negative integer'
                }), 400

        success = cache.put(key, value, ttl)

        if success:
            response_data = {
                'message': 'Value stored successfully',
                'key': key,
                'ttl': ttl or cache.default_ttl,
                'timestamp': datetime.now().isoformat()
            }
            return jsonify(response_data), 201
        else:
            return jsonify({
                'error': 'Failed to store value'
            }), 500

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/cache/<key>', methods=['DELETE'])
def delete_cache_item(key):
    """DELETE endpoint to remove a key from cache."""
    try:
        success = cache.delete(key)

        if success:
            return jsonify({
                'message': 'Key deleted successfully',
                'key': key,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'error': 'Key not found',
                'key': key
            }), 404

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """GET endpoint to retrieve cache statistics."""
    try:
        stats = cache.stats()
        stats['timestamp'] = datetime.now().isoformat()
        return jsonify(stats), 200

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/cache', methods=['DELETE'])
def clear_cache():
    """DELETE endpoint to clear all cache items."""
    try:
        cache.clear()
        return jsonify({
            'message': 'Cache cleared successfully',
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed'
    }), 405


if __name__ == '__main__':
    print("Starting In-Memory Cache API Server...")
    print("Available endpoints:")
    print("  GET    /cache/<key>     - Retrieve value")
    print("  PUT    /cache/<key>     - Store value")
    print("  DELETE /cache/<key>     - Delete key")
    print("  GET    /cache/stats     - Get cache statistics")
    print("  DELETE /cache           - Clear all cache")
    print("\nExample usage:")
    print(
        "  curl -X PUT http://localhost:8080/cache/mykey -H 'Content-Type: application/json' -d '{\"value\":\"hello\", \"ttl\":300}'")
    print("  curl -X GET http://localhost:8080/cache/mykey")

    app.run(debug=True, host='0.0.0.0', port=8080)