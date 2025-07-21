# utils/logger.py

import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    def __init__(self, name=__name__, level=logging.INFO, log_file="logs/app.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加 handler
        if not self.logger.handlers:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            # 格式化
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s'
            )

            # 控制台输出
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

            # 文件输出（滚动）
            fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def get_logger(self):
        return self.logger