# crawler/webdriver_mgr.py

import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
import time
import logging
from utils.logger import Logger
import config

logger = Logger(__name__).get_logger()

class WebDriverManager:
    def __init__(self, options=None, wire_options=None, retry_limit=3, retry_delay=5):
        self.wire_options = wire_options or {}
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay
        self.driver = None
        self.wechat_ua = (
            "Mozilla/5.0 (Linux; Android 10; MI 8 SE Build/QKQ1.190828.002; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 "
            "MQQBrowser/6.2 TBS/045710 Mobile Safari/537.36 MicroMessenger/8.0.13.1580(0x28000D38) "
            "Process/appbrand0 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64"
        )
        self._initialize_driver()

    def _default_options(self):
        wechat_ua = self.wechat_ua
        chrome_options = uc.ChromeOptions()
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        chrome_options.add_argument('--user-agent=' + wechat_ua)
        chrome_options.add_argument('--disable-gpu')  # 禁用 GPU 硬件加速
        chrome_options.add_argument('--no-sandbox')  # 禁用 GPU 硬件加速
        chrome_options.add_argument('--headless=new')  # 如果需要无头模式，可以取消注释
        chrome_options.add_argument("--window-size=1290,2796")
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument(r'--user-data-dir=./webdriver_data')  # 指定用户数据目录
        chrome_options.add_argument('--disable-features=TranslateUI,BrowserSwitcherService')
        chrome_options.add_argument('--disable-autoupdate')
        return chrome_options

    def _initialize_driver(self):
        """初始化或重新创建 WebDriver 实例"""
        for attempt in range(1, self.retry_limit + 1):
            try:
                logger.info("正在启动 WebDriver...")
                self.driver = uc.Chrome(service=Service(config.CHROME_DRIVER_PATH), options=self._default_options(), seleniumwire_options=self.wire_options)
                self.driver.execute_cdp_cmd("Network.enable", {})
                self.driver.execute_cdp_cmd("Network.setBlockedURLs", {
                    "urls": ["*zqt.meituan.com/auth*", "*zqt.meituan.com/sso/web/auth?*"]
                })
                self.driver.execute_cdp_cmd("Network.setRequestInterception", {
                    "patterns": [
                        {"urlPattern": "*zqt.meituan.com/auth*", "resourceType": "Document", "interceptionStage": "Request"},
                        {"urlPattern": "*zqt.meituan.com/sso/web/auth?*", "resourceType": "Document", "interceptionStage": "Request"}
                    ]
                })
                self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": 430,
                    "height": 932,
                    "deviceScaleFactor": 2,
                    "mobile": False
                })
                # reset user agent
                self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                    "userAgent": self.wechat_ua
                })
                logger.info("WebDriver 启动成功")
                return
            except Exception as e:
                logger.error(f"启动 WebDriver 失败 (尝试 {attempt}/{self.retry_limit}): {e}")
                # get lineno
                import traceback
                exc_info = traceback.format_exc()
                logger.error(f"异常信息: {exc_info}")
                if attempt < self.retry_limit:
                    time.sleep(self.retry_delay)
                else:
                    raise WebDriverException("无法启动 WebDriver，请检查 Chrome 安装和 chromedriver 路径")

    def get_driver(self):
        """返回当前有效的 driver 实例"""
        if not self.driver:
            logger.warning("Driver 未初始化，尝试重新启动")
            self._initialize_driver()
        return self.driver

    def restart_driver(self):
        """重启 WebDriver"""
        self.quit()
        self._initialize_driver()

    def quit(self):
        """安全关闭 WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver 已关闭")
            except Exception as e:
                logger.error(f"关闭 WebDriver 时出错: {e}")
            finally:
                self.driver = None