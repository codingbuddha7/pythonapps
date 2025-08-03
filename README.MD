## Ex 1: Custom Load Balancer

### Created by ChatGPT
 
- cd server1
- run `python3 -m http.server 8001`

- cd server2
- run `python3 -m http.server 8002`

- cd server3
- run `python3 -m http.server 8003`

- run `python3 LoadBalancer.py`

## Ex 2: Custom In Memory Cache

### Created by Claude Sonnet 4:

### Key Features:

**Cache Implementation:**
- **Thread-safe**: Uses RLock for concurrent access
- **TTL Support**: Configurable time-to-live for cache entries
- **LRU Eviction**: Automatically removes least recently used items when at capacity
- **Automatic Cleanup**: Removes expired items during operations

**REST API Endpoints:**
- `PUT /cache/<key>` - Store values with optional TTL
- `GET /cache/<key>` - Retrieve values
- `DELETE /cache/<key>` - Remove specific keys
- `GET /cache/stats` - Get cache statistics
- `DELETE /cache` - Clear entire cache

### Usage Examples:

**1. Store a value:**
```bash
curl -X PUT http://localhost:5000/cache/user123 \
  -H 'Content-Type: application/json' \
  -d '{"value": {"name": "John", "age": 30}, "ttl": 600}'
```

**2. Retrieve a value:**
```bash
curl -X GET http://localhost:5000/cache/user123
```

**3. Get cache statistics:**
```bash
curl -X GET http://localhost:5000/cache/stats
```

### Installation Requirements:
```bash
pip install flask
```

### Configuration Options:
- `max_size`: Maximum cache capacity (default: 1000)
- `default_ttl`: Default expiration time in seconds (default: 3600)

The cache handles various data types (strings, numbers, objects) and includes proper error handling, JSON responses, 
and HTTP status codes. The implementation is production-ready with comprehensive logging and statistics tracking.