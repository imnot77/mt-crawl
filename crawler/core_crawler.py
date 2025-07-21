# crawler/core_crawler.py
import json
import threading
import time
import logging

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logger import Logger
from utils.exceptions import NoAvailableCookiesError, WebDriverCrashError

logger = Logger(__name__).get_logger()

class CoreCrawler:
    def __init__(self, webdriver_manager, cookies_pool):
        """
        初始化核心爬虫类

        :param webdriver_manager: WebDriverManager 实例
        :param cookies_pool: CookiesPool 实例
        """
        self.webdriver_manager = webdriver_manager
        self.cookies_pool = cookies_pool
        self.driver = self.webdriver_manager.get_driver()
        self.lock = threading.Lock()

    def set_cookies_to_browser(self, cookies):
        """
        将指定 cookies 设置到当前浏览器实例中

        :param cookies: cookies 列表（格式应与 Selenium 的 get_cookies() 一致）
        :return: 是否成功
        """
        try:
            # 如果current_url不存在直接throw
            self.driver.current_url
            # 检查driver是不是在https://zqt.meituan.com的前缀，如果不是，先跳转
            if not self.driver.current_url.startswith("https://zqt.meituan.com"):
                logger.info("当前浏览器未在目标域名，正在跳转到 https://zqt.meituan.com")
                self.driver.get("https://zqt.meituan.com")
            logger.info("正在清除当前浏览器 cookies")
            self.driver.delete_all_cookies()

            logger.info("正在设置新 cookies 到浏览器")
            for cookie in cookies:
                # 修正 cookie 中的 domain 字段（如 localhost 不支持）
                if 'sameSite' in cookie:
                    del cookie['sameSite']
                if 'domain' in cookie and 'localhost' in cookie['domain']:
                    cookie['domain'] = cookie['domain'].replace('localhost', '')
                self.driver.add_cookie(cookie)

            return True
        except Exception as e:
            logger.error(f"设置 cookies 失败: {e}")
            return False

    def _ensure_valid_cookies(self):
        """
        确保当前有可用 cookies，若无则尝试重新登录

        :return: cookies 列表 或 None
        """
        try:
            cookies = self.cookies_pool.get_random_cookies()
            return cookies
        except RuntimeError as e:
            logger.warning("Cookies 池为空，尝试重新登录")
            raise NoAvailableCookiesError("无法获取可用 cookies")

    def _handle_invalid_cookies(self, cookie_id):
        """
        处理 cookies 失效的情况

        :param cookie_id: 失效的 cookies ID
        """
        logger.warning(f"检测到 cookies 失效，ID: {cookie_id}")
        self.cookies_pool.remove_cookies_by_id(cookie_id)

        if not self.cookies_pool.get_random_cookies():
            logger.warning("当前无可用 cookies")

    def _filter_logs(self, requests):
        detail_data = None
        comment_data = []
        for entry in requests:
            if entry.response:
                if 'getmocktasksharedetail' in entry.url:
                    content_type = entry.response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        try:
                            detail_data = entry.response.json()  # 如果是 JSON，可以直接解析
                        except Exception as e:
                            logger.error(f"解析题目 JSON 失败: {e}")
                elif 'pagequerycomment' in entry.url:
                    content_type = entry.response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        try:
                            comment_data.append(entry.response.json())  # 如果是 JSON，可以直接解析
                        except Exception as e:
                            logger.error(f"解析评论 JSON 失败: {e}")
        return detail_data, comment_data

    def _filter_logs_v1(self, logs):
        detail_data = None
        comment_data = []
        keywords = ["getmocktasksharedetail", "pagequerycomment"]
        for entry in logs:
            log = json.loads(entry["message"])["message"]

            if log["method"] == "Network.responseReceived":
                url = log["params"]["response"]["url"]

                if any(kw in url for kw in keywords):
                    # 获取响应体
                    response_body = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": log["params"]["requestId"]}
                    )
                    try:
                        json_data = json.loads(response_body["body"])
                        # print(f"找到匹配的请求: {url}")
                        if "getmocktasksharedetail" in url:
                            detail_data = json_data
                        else:
                            comment_data.append(json_data)
                    except Exception as e:
                        print(f"解析 JSON 失败: {e}")
        return detail_data, comment_data

    def fetch_page_content(self, url):
        """
        【用户自定义】跳转目标页面并截取内容，需由用户实现。

        :param url: 要访问的目标 URL
        :return: 页面内容（如 HTML、JSON、截图等）
        """
        try:
            wait = WebDriverWait(self.driver, 4)
            # 等待 class 名为 "load-more-button" 的元素出现
            logger.info("等待页面加载完成，查找 'load-more-button' 元素...")
            # 找到就点一下，然后继续等继续找，最多循环4次
            for _ in range(4):
                try:
                    load_more_button = wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "load-more-button"))
                    )
                    # 先判断能否点击，然后点击
                    # if load_more_button.is_displayed() and load_more_button.is_enabled():
                    #     try:
                    #         load_more_button.click()
                    #     except Exception as e:
                    #         logger.info(f"点击 'load-more-button' 失败: {e}")
                except TimeoutException:
                    break
        except TimeoutException:
            pass
        logger.info("开始获取")
        logs = self.driver.get_log("performance")
        detail_data, comment_data = self._filter_logs_v1(logs)
        return detail_data, comment_data

    def crawl_page(self, url, retry=3):
        """
        执行爬取任务的核心方法

        :param url: 目标页面地址
        :param retry: 最大重试次数
        :return: 页面内容 或 None
        """
        with self.lock:
            for attempt in range(1, retry + 1):
                try:
                    logger.info(f"尝试爬取页面 (第 {attempt}/{retry} 次): {url}")

                    # 获取可用 cookies
                    cookies = self._ensure_valid_cookies()

                    # 设置 cookies 到浏览器
                    if not self.set_cookies_to_browser(cookies["cookies"]):
                        # self._handle_invalid_cookies(cookies["id"])
                        continue

                    # 跳转目标页面
                    self.driver.get(url)

                    # 验证是否登录成功（如跳转到了登录页）
                    if url.find("xiaomei/vote") != -1 and self._is_redirected_to_login_page():
                        logger.warning("检测到被重定向到登录页，cookies 可能已失效")
                        self._handle_invalid_cookies(cookies["id"])
                        continue

                    # 执行用户自定义的页面内容截取逻辑
                    detail, comment = self.fetch_page_content(url)
                    if detail:
                        if detail['code'] != 0 or 'data' not in detail:
                            logger.error(f"获取题目详情失败，返回内容: {detail}")
                            continue
                        return detail["data"], [i['data'] for i in comment if 'code' in i and i['code'] == 0]

                except Exception as e:
                    logger.error(f"爬取过程中发生异常: {e}", exc_info=True)
                    self.webdriver_manager.restart_driver()
                    time.sleep(5)

        logger.error(f"爬取失败，已达最大重试次数: {retry}")
        return None

    def _is_redirected_to_login_page(self):
        """
        检测是否被重定向到登录页（可选实现）

        :return: 是否被重定向
        """
        from selenium.common.exceptions import TimeoutException

        try:
            WebDriverWait(self.driver, 1).until(
                EC.url_contains("login?")  # 根据实际登录页 URL 判断
            )
            return True
        except TimeoutException:
            return False