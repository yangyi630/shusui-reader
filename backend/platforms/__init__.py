# 平台 API 模块
from .weread import WeReadAPI, WeChatScanLogin, WeReadMockData
from .fanqie import FanqieAPI
from .kindle import KindleAPI
from .douban import DoubanReadAPI

__all__ = [
    'WeReadAPI', 'WeChatScanLogin', 'WeReadMockData',
    'FanqieAPI', 'KindleAPI', 'DoubanReadAPI',
]
