import time
from datetime import datetime
from dbh.redis_handler import RedisHandler
import undetected_chromedriver as uc
import config
import json
from crawler.core_crawler import CoreCrawler
from crawler.webdriver_mgr import WebDriverManager
from crawler.cookies_pool import CookiesPool
from crawler.login_handler import LoginHandler
from pymongo import MongoClient

# Redis configuration
REDIS_QUEUE = 'upload_queue'

# Connect to Redis using the handler
r = RedisHandler()

def get_content(url, crawler):
    # Your insert logic here
    if not url.startswith("https://zqt.meituan.com/xiaomei/vote/jury/api/r/rediectByScene?jumpScene=mockTaskShare&userId="):
        print(f"Invalid URL: {url}")
        return
    detail, comment = crawler.crawl_page(url, retry=3)
    # 生成格式化后的json并打印
    if not detail:
        print(f"Failed to crawl detail for URL: {url}")
        return None
    res = {
        "raw_url": url,
        "uploader": 0,  # 使用 Int64 表示 bigint
        "upload_timestamp": int(time.time()),
        "detail": detail,
        "comment": comment
    }
    return res

def process_queue():
    while True:
        now = datetime.now()
        # Wait until the start of the next minute
        sleep_seconds = 60 - now.second
        print(f"Waiting for {sleep_seconds} seconds until the next minute...")
        time.sleep(sleep_seconds)

        # Read all items from the queue
        queue_items = r.get_queue(REDIS_QUEUE)
        if queue_items:
            webdriver_manager = None
            try:
                webdriver_manager = WebDriverManager()
                cookies_pool = CookiesPool(max_size=100)
                crawler = CoreCrawler(webdriver_manager, cookies_pool)
                coll = MongoClient(config.MONGO_CONN)[config.DB_NAME][config.PROBLEM_COLLECTION]
                for _ in range(len(queue_items)):
                    url = r.pop_queue_head(REDIS_QUEUE)
                    if url:
                        existing_doc = coll.find_one({"raw_url": url})
                        if existing_doc:
                            continue
                        if isinstance(url, bytes):
                            url = url.decode('utf-8', errors='ignore')
                        res = get_content(url.strip(), crawler)
                        if res:
                            coll.insert_one(res)
            except Exception as e:
                print(f"Error processing queue: {e}")
            finally:
                if webdriver_manager:
                    webdriver_manager.quit()

if __name__ == "__main__":
    process_queue()