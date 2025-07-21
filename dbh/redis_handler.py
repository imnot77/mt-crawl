import redis
import json
import config

class RedisHandler:
    def __init__(self):
        self.client = redis.from_url(config.REDIS_CONN)

    def set_json(self, key, value, ex=None):
        """存储 JSON 数据"""
        self.client.set(key, json.dumps(value), ex=ex)

    def get_json(self, key):
        """获取 JSON 数据"""
        data = self.client.get(key)
        return json.loads(data) if data else None

    def delete(self, key):
        """删除键值"""
        self.client.delete(key)

    def get_queue(self, key):
        """获取整个队列"""
        return self.client.lrange(key, 0, -1)

    def pop_queue_head(self, key):
        """删除并返回队头元素"""
        return self.client.lpop(key)

    def push_queue_tail(self, key, value):
        """插入元素到队尾"""
        return self.client.rpush(key, value)
