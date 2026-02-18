import json
import hashlib
from pathlib import Path

cache_file = Path("cache.json")

def get_cached_response(query):
    if cache_file.exists():
        with open(cache_file, "r") as f:
            cache = json.load(f)
            key = hashlib.md5(query.lower().encode()).hexdigest()
            return cache.get(key)
    return None

def set_cached_response(query, response):
    key = hashlib.md5(query.lower().encode()).hexdigest()
    cache = {}
    if cache_file.exists():
        with open(cache_file, "r") as f:
            cache = json.load(f)
    cache[key] = response
    with open(cache_file, "w") as f:
        json.dump(cache, f)
