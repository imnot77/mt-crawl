# crawler/login_handler.py

import time
import logging
from threading import Lock
from utils.logger import Logger
from crawler.webdriver_mgr import WebDriverManager
from crawler.cookies_pool import CookiesPool

logger = Logger(__name__).get_logger()

class LoginHandler:
    def __init__(self, webdriver_manager: WebDriverManager, cookies_pool: CookiesPool, login_url: str):
        self.webdriver_manager = webdriver_manager
        self.cookies_pool = cookies_pool
        self.login_url = login_url
        self.lock = Lock()
        self.is_logging_in = False
        self.qr_code = ""

    def start_login_process(self, timeout=120):
        """
        启动登录流程，包括：
        - 打开登录页面
        - 等待二维码扫描
        - 获取 cookies
        - 保存 cookies 到池中

        :param timeout: 等待扫描的最大时间（秒）
        :return: 成功与否
        """
        # 如果self.lock是锁了的，宣布失败
        if self.lock.locked():
            logger.warning("其他线程正在进行登录操作")
            return False
        with self.lock:
            if self.is_logging_in:
                logger.warning("已有正在进行的登录流程，跳过本次请求")
                return False
            self.is_logging_in = True
            self.qr_code = ""
            logger.info("开始登录流程")

        try:
            driver = self.webdriver_manager.get_driver()
            driver.get(self.login_url)
            # 获取class为qrcode-img的img
            if not self._wait_for_element(driver, ".qrcode-img", timeout):
                logger.error("登录页面加载超时，未找到二维码元素")
                return False
            # 获取二维码图片(采用截图的方式)
            elem = driver.find_element("css selector", ".qrcode-img")
            self.qr_code = elem.screenshot_as_base64  # 获取二维码图片的 base64 编码
            # 保存图片到本地
            with open("qrcode.png", "wb") as f:
                f.write(elem.screenshot_as_png)

            if not self.wait_for_qr_scan(driver, timeout):
                logger.error("等待二维码扫描超时")
                return False

            cookies = self.get_cookies_after_login(driver)
            if not cookies:
                logger.error("登录后未能获取 cookies")
                return False

            cookie_id = self.cookies_pool.add_cookies(cookies)
            logger.info(f"登录成功，cookies 已保存至池中，ID: {cookie_id}")
            return True

        except Exception as e:
            logger.error(f"登录过程中发生异常: {e}", exc_info=True)
            return False

        finally:
            self.is_logging_in = False
            self.qr_code = ""

    def wait_for_qr_scan(self, driver, timeout=120):
        """
        【用户自定义】等待二维码被扫描，需由用户实现。

        :param driver: WebDriver 实例
        :param timeout: 最大等待时间（秒）
        :return: 是否成功扫描并完成登录（True/False）
        """
        return self._wait_for_url(driver, "https://zqt.meituan.com", timeout)

    def get_cookies_after_login(self, driver):
        """
        【用户自定义】获取登录后的 cookies，需由用户实现。

        :param driver: WebDriver 实例
        :return: cookies 列表（格式应与 Selenium 的 get_cookies() 一致）
        """
        cookies = driver.get_cookies()
        if not cookies:
            logger.error("获取 cookies 失败，可能未完成登录")
            return None
        logger.info(f"获取到 {len(cookies)} 个 cookies")
        return cookies

    def _wait_for_element(self, driver, locator, timeout=120):
        """
        内部辅助方法：等待某个元素出现（可选实现）

        :param driver: WebDriver 实例
        :param locator: 元素定位器（如 CSS selector）
        :param timeout: 超时时间
        :return: 是否找到元素
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, locator))
            )
            return True
        except Exception as e:
            logger.error(f"等待元素 {locator} 超时: {e}")
            return False

    def _wait_for_url(self, driver, url_prefix, timeout=120):
        """
        内部辅助方法：等待某个url前缀出现

        :param driver: WebDriver 实例
        :param url_prefix: 目标 URL 前缀
        :param timeout: 超时时间
        :return: 是否找到元素
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.current_url.startswith(url_prefix)
            )
            return True
        except Exception as e:
            logger.error(f"等待 URL 前缀 {url_prefix} 超时: {e}")
            return False
