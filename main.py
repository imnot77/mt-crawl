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
from utils.logger import Logger

logger = Logger(__name__).get_logger()

# Redis configuration
REDIS_QUEUE = 'upload_queue'

# Connect to Redis using the handler
r = RedisHandler()

def get_content(url, crawler):
    # Your insert logic here
    try:
        res = crawler.crawl_page(url, retry=2)
        if len(res) == 2:
            detail, comment = res
        if detail == "wrong link":
            logger.error(f"Wrong link for URL: {url}")
            return "wrong link"
        # 生成格式化后的json并打印
        if not detail:
            logger.error(f"Failed to crawl detail for URL: {url}")
            return "failed"
    except Exception as e:
        logger.error(f"Exception occurred while crawling {url}: {e}")
        return "failed"
    res = {
        "raw_url": url,
        "uploader": 0,
        "upload_timestamp": int(time.time()),
        "detail": detail,
        "comment": comment
    }
    return res

def upsert_item(col, item):
    voteTaskNo = item.get("detail", {}).get("taskInfo", {}).get("voteTaskNo", None)
    if voteTaskNo:
        col.replace_one({"detail.taskInfo.voteTaskNo": voteTaskNo}, item, upsert=True)
        logger.info(f"Upserted item with voteTaskNo: {voteTaskNo}")
    else:
        col.insert_one(item)
        logger.info("Inserted new item with voteTaskNo")

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
            # 防止内存泄漏
            print(f"Processing {len(queue_items)} items from the queue...")
            # Initialize WebDriverManager and CookiesPool
            cookies_pool = None
            webdriver_manager = None
            try:
                webdriver_manager = WebDriverManager()
                cookies_pool = CookiesPool(max_size=100)
                crawler = CoreCrawler(webdriver_manager, cookies_pool)
                coll = MongoClient(config.MONGO_CONN)[config.DB_NAME][config.PROBLEM_COLLECTION]
                process_cnt = min(len(queue_items), 8)  # Process up to 8 items
                logger.info(f"Current patch process count: {process_cnt}")
                for _ in range(process_cnt):
                    raw = r.pop_queue_head(REDIS_QUEUE)
                    try:
                    # decode if it is json, otherwise continue
                        if not raw:
                            continue
                        data = None
                        try:
                            raw = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                            data = json.loads(raw)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        if isinstance(data, dict) and 'userId' in data and 'taskId' in data:
                            userId = data['userId']
                            taskId = data['taskId']
                            logger.info(f"Processing item: userId={userId}, taskId={taskId[:7]}...")
                            uploader = data.get('uploader', 'unknown')
                            existing_doc = coll.find_one({"userId": userId, "taskId": taskId})
                            if existing_doc:
                                continue
                            url = f"https://zqt.meituan.com/xiaomei/vote/jury/api/r/rediectByScene?jumpScene=mockTaskShare&userId={userId}&channel=mockTaskShare&encryptMockTaskNo={taskId}"
                            res = get_content(url, crawler)
                            if res == "wrong link":
                                logger.error(f"Wrong link for URL: {url}")
                                with open("wrong_links.txt", "a") as f:
                                    f.write(f"{userId}, {taskId}\n")
                                continue
                            if not isinstance(res, dict):
                                # failed to get content
                                raise Exception(f"Failed to get content for URL: {url}")
                            res['userId'] = userId
                            res['taskId'] = taskId
                            res['uploader'] = uploader
                            if res:
                                upsert_item(coll, res)
                    except Exception as e:
                        logger.error(f"Error processing item from queue: {e}")
                        # get exception lineno
                        import traceback
                        exc_info = traceback.format_exc()
                        logger.error(f"Exception info: {exc_info}")
                        # Reinsert the item into the queue if processing fails
                        r.push_queue_tail(REDIS_QUEUE, raw)  # Reinsert the item if processing fails
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
            finally:
                if webdriver_manager:
                    webdriver_manager.quit()
                    # 删除webdriver_manager释放内存
                    del webdriver_manager
                if cookies_pool:
                    cookies_pool.clear()
                    # 删除cookies_pool释放内存
                    del cookies_pool

if __name__ == "__main__":
    import os
    os.makedirs("screenshots", exist_ok=True)
    process_queue()