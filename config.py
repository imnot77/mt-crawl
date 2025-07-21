import os

MONGO_CONN = os.environ.get("MONGO_CONN", "mongodb://admin:lizibuaileyiou@localhost:27017/")
REDIS_CONN = os.environ.get("REDIS_CONN", "redis://localhost:6379/0")
DB_NAME = os.environ.get("DB_NAME", "mtdb")
PROBLEM_COLLECTION = "meituan"
LOGIN_URL = "https://passport.meituan.com/useraccount/login?continue=https%3A%2F%2Fzqt.meituan.com%2Fcap%2Faccount%2F" \
            "v2%2Fcallback%3Fcap_login_biz%3Dxiaomei%26cap_login_type%3DPASSPORT%26login_change_account%3D%26login_ty" \
            "pe_to_cookie%3Dtrue%26web_url%3Dhttps%253A%252F%252Fzqt.meituan.com%252Fxiaomei%252Fstatic%252Ffsb-share" \
            "-h5%253Fchannel%253DmockTaskShare%2526encryptMockTaskNo%253DQXdRQUFBQkpBZ0FBQUFFN21zKzZBQUFBUENFT05lUldJ" \
            "Nk9sd2lLZmZoNkZWZTFhQk1IeDBQQ0xiZmVvZmd2aWVjNk40QXRvcHVSQ292UFpCWTA1SjQzMVAzQmpBd1RIQjA4ejdmeTE4QUFBQURk" \
            "3I0b2ZMcERKNjBJalZUcGh6ZU9jbCtmTE9XT0dHUURCNW9BakFlcUlBcjdIYXdia1VDdzBla21ZU0M3S1dlM2REQTAvM09wcQ%25253D" \
            "%25253D%2526fromSource%253Dpclogin%2526login_change_account%253D%2526userId%253D4666811730%2526xmeiss%25" \
            "3DnoLogin_4_mockTaskShare_1748875451_99%2526xmlogintag%253Dxm_loginkey_1748875477696"
COOKIE_POOL_SIZE = 10
CRAWLER_RETRY_TIMES = 3
CHROME_DRIVER_PATH = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
