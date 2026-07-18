import pytest, time
from datacore.store.cache import MemoryCache

class TestMemoryCache:
    def test_set_get(self):
        c = MemoryCache()
        c.set('k', 'v')
        assert c.get('k') == 'v'
        
    def test_expiry(self):
        c = MemoryCache(default_ttl=0.1)
        c.set('k', 'v')
        time.sleep(0.15)
        assert c.get('k') is None
        
    def test_invalidate(self):
        c = MemoryCache()
        c.set('k', 'v')
        c.invalidate('k')
        assert c.get('k') is None
        
    def test_clear(self):
        c = MemoryCache()
        c.set('a', 1)
        c.set('b', 2)
        c.clear()
        assert c.get('a') is None
        
    def test_purge(self):
        c = MemoryCache(default_ttl=-1)
        c.set('x', 1)
        c.set('y', 2)
        assert c.purge() == 2
