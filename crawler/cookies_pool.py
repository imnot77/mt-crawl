# crawler/cookies_pool.py

import random
import threading
import json
import logging
from utils.logger import Logger

logger = Logger(__name__).get_logger()

class CookiesPool:
    def __init__(self, max_size=10):
        self.cookies_list = []
        self.lock = threading.Lock()
        self.max_size = max_size
        self.cookie_id_counter = 0
        self.load_cookies_from_file("cookies.json")  # 初始化时加载 cookies

    def save_cookies_to_file(self, file_path):
        # save cookie json to file
        with self.lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cookies_list, f, ensure_ascii=False, indent=4)
            logger.info(f"Cookies 已保存到文件: {file_path}")

    def load_cookies_from_file(self, file_path):
        """从文件加载 cookies"""
        with self.lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.cookies_list = json.load(f)
                self.cookie_id_counter = max((c["id"] for c in self.cookies_list), default=0)
                logger.info(f"Cookies 已从文件加载: {file_path}")
            except FileNotFoundError:
                logger.warning(f"Cookies 文件未找到: {file_path}, 将使用空池")
            except json.JSONDecodeError:
                logger.error(f"Cookies 文件格式错误: {file_path}, 将使用空池")

    def add_cookies(self, cookies):
        """添加一组 cookies 到池中，并分配唯一 ID"""
        with self.lock:
            if len(self.cookies_list) >= self.max_size:
                logger.info("Cookies 池已满，将移除最早的一组 cookies")
                self.cookies_list.pop(0)

            self.cookie_id_counter += 1
            cookie_entry = {
                "id": self.cookie_id_counter,
                "cookies": cookies
            }
            self.cookies_list.append(cookie_entry)
            logger.info(f"新增 cookies 到池中，ID: {cookie_entry['id']}")
        self.save_cookies_to_file("cookies.json")  # 每次添加后保存到文件
        return cookie_entry["id"]

    def get_random_cookies(self):
        """随机获取一组 cookies"""
        with self.lock:
            if not self.cookies_list:
                return {"cookies": {}}      # 暂时认为不需要cookie
                # logger.error("Cookies 池为空")
                # raise RuntimeError("Cookies 池为空，无法执行爬取任务")

            selected = random.choice(self.cookies_list)
            logger.info(f"从池中获取 cookies，ID: {selected['id']}")
            return selected

    def remove_cookies_by_id(self, cookie_id):
        """根据 ID 删除失效的 cookies"""
        with self.lock:
            original_count = len(self.cookies_list)
            self.cookies_list = [c for c in self.cookies_list if c["id"] != cookie_id]
            removed = len(self.cookies_list) < original_count
            if removed:
                logger.info(f"已从池中删除 cookies，ID: {cookie_id}")
            else:
                logger.warning(f"未找到指定 ID 的 cookies，ID: {cookie_id}")
        self.save_cookies_to_file("cookies.json")  # 每次删除后保存到文件
        return removed

    def clear(self):
        """清空所有 cookies"""
        with self.lock:
            self.cookies_list.clear()
            logger.info("已清空 cookies 池")
