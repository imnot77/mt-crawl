import undetected_chromedriver as uc
import config
import json
import time
from crawler.core_crawler import CoreCrawler
from crawler.webdriver_mgr import WebDriverManager
from crawler.cookies_pool import CookiesPool
from crawler.login_handler import LoginHandler


def init_webdriver():
    """
    初始化 WebDriver 实例
    :return: WebDriver 实例
    """
    

    return WebDriverManager()


def run_login(login_handler):
    """
    执行登录流程
    :param webdriver_manager: WebDriver 管理器实例
    :param login_handler: 登录处理器实例
    :return: None
    """
    try:
        success = login_handler.start_login_process(timeout=120)
        if success:
            print("登录成功，cookies 已加入池中")
            return
        print("登录失败")
    except Exception as e:
        print(f"登录失败: {e}")


if __name__ == "__main__":
    # 读取运行参数，判断是--login还是--crawl
    import sys
    if len(sys.argv) < 2:
        print("请提供运行参数：--login 或 --crawl")
        sys.exit(1)
    run_mode = sys.argv[1]
    if run_mode not in ['--login', '--crawl', '--crawl-test']:
        print("无效的运行参数，请使用 --login 或 --crawl")
        sys.exit(1)
    webdriver_manager = init_webdriver()
    cookies_pool = CookiesPool(max_size=100)
    if run_mode == '--login':
        login_handler = LoginHandler(
            webdriver_manager=webdriver_manager,
            cookies_pool=cookies_pool,
            login_url=config.LOGIN_URL
        )
        run_login(login_handler)
    else:
        # 读取--crawl的url
        if len(sys.argv) < 3:
            print("请提供要爬取的 URL")
            sys.exit(1)
        url_to_crawl = sys.argv[2]
        if not url_to_crawl.startswith("http"):
            print("无效的 URL，请确保以 http:// 或 https:// 开头")
            sys.exit(1)
        crawler = CoreCrawler(webdriver_manager, cookies_pool)
        detail, comment = crawler.crawl_page(url_to_crawl, retry=3)
        # 生成格式化后的json并打印
        res = {
            "raw_url": url_to_crawl,
            "uploader": 0,  # 使用 Int64 表示 bigint
            "upload_timestamp": int(time.time()),  # 毫秒级时间戳
            "detail": detail,
            "comment": comment
        }
        if run_mode == '--crawl-test':
            print(json.dumps(res, ensure_ascii=False, indent=2))
            sys.exit(0)
        else:
            from pymongo import MongoClient
            client = MongoClient(config.MONGO_CONN)
            db = client[config.DB_NAME]
            collection = db[config.PROBLEM_COLLECTION]
            # 先查询raw_url是否存在，如果不存在则插入
            existing_doc = collection.find_one({"raw_url": url_to_crawl})
            if existing_doc:
                print("该题目已存在，跳过插入")
            else:
                result = collection.insert_one(res)
                print("插入成功！文档 ID:", result.inserted_id)