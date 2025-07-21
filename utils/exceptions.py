class CrawlerError(Exception):
    """基础异常类"""
    pass

class NoAvailableCookiesError(CrawlerError):
    pass

class WebDriverCrashError(CrawlerError):
    pass
