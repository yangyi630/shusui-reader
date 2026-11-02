"""
微信读书平台 - 真实数据对接
支持方式：
1. Cookie 导入登录（个人用户可用，真实数据）
2. 微信开放平台扫码登录（需企业资质，框架预留）
"""

import os
import re
import time
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class WeReadAPI:
    """
    微信读书 API 客户端
    通过 Cookie 方式访问微信读书网页版接口，获取真实数据
    """

    BASE_URL = "https://weread.qq.com"
    WEB_URL = "https://weread.qq.com/web"

    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://weread.qq.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://weread.qq.com'
        })

        if cookies:
            self.set_cookies(cookies)

        self.user_info = None

    def set_cookies(self, cookies):
        """
        设置 Cookie

        Args:
            cookies: str (Cookie字符串) 或 dict
        """
        if isinstance(cookies, str):
            cookie_dict = {}
            for item in cookies.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookie_dict[key.strip()] = value.strip()
            cookies = cookie_dict

        for key, value in cookies.items():
            self.session.cookies.set(key, value, domain='.weread.qq.com')

    def parse_cookie_string(self, cookie_str):
        """从浏览器复制的 Cookie 字符串解析"""
        cookies = {}
        if not cookie_str:
            return cookies
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def check_login(self):
        """
        检查是否登录有效

        Returns:
            dict: 用户信息，未登录返回 None
        """
        try:
            url = f"{self.WEB_URL}/user/info"
            resp = self.session.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and data.get('data'):
                    user_data = data['data']
                    self.user_info = {
                        'user_id': user_data.get('user_id', user_data.get('userUid', '')),
                        'nickname': user_data.get('nickname', user_data.get('name', '')),
                        'avatar': user_data.get('avatar', user_data.get('avatarUrl', '')),
                        'gender': user_data.get('gender', 0),
                    }
                    return self.user_info

            # 备用方案：访问书架判断
            books = self.get_bookshelf()
            if books is not None and len(books) > 0:
                self.user_info = {
                    'user_id': 'cookie_user',
                    'nickname': '微信读书用户',
                    'avatar': '',
                }
                return self.user_info

        except Exception as e:
            logger.debug(f"检查登录状态失败: {e}")

        return None

    def get_bookshelf(self, count=50, max_index=1000):
        """
        获取书架书籍列表

        Args:
            count: 每次获取数量
            max_index: 最大获取数量

        Returns:
            list: 书籍列表
        """
        all_books = []
        offset = 0

        try:
            while True:
                url = f"{self.WEB_URL}/shelf/sync"
                params = {
                    'maxIndex': max_index,
                    'currentIndex': len(all_books),
                    'synckey': 0
                }
                resp = self.session.get(url, params=params, timeout=15)

                if resp.status_code != 200:
                    break

                data = resp.json()
                if data.get('code') != 0:
                    break

                books = data.get('data', {}).get('books', [])
                if not books:
                    break

                all_books.extend(books)

                if len(books) < count:
                    break
                if len(all_books) >= max_index:
                    break

                time.sleep(0.3)

            # 转换格式
            result = []
            for book in all_books:
                result.append({
                    'id': book.get('bookId', ''),
                    'title': book.get('title', ''),
                    'author': book.get('author', ''),
                    'cover': book.get('cover', book.get('imgUrl', '')),
                    'platform': 'wechat',
                    'read_progress': book.get('readUpdateInfo', {}).get('readProgress', 0) / 10000 if book.get('readUpdateInfo') else 0,
                    'highlights_count': book.get('highlightCount', 0),
                    'book_status': book.get('bookStatus', 0),
                    'last_read': book.get('lastReadDate', 0),
                })

            return result

        except Exception as e:
            logger.error(f"获取书架失败: {e}")
            return None

    def get_book_detail(self, book_id):
        """获取书籍详情"""
        try:
            url = f"{self.WEB_URL}/book/info"
            params = {'bookId': book_id}
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    return data.get('data', {})
        except Exception as e:
            logger.error(f"获取书籍详情失败: {e}")
        return None

    def get_highlights(self, book_id):
        """
        获取书籍划线/标注

        Args:
            book_id: 书籍 ID

        Returns:
            list: 划线列表
        """
        try:
            url = f"{self.WEB_URL}/book/get_highlights"
            params = {'bookId': book_id}
            resp = self.session.get(url, params=params, timeout=15)

            if resp.status_code != 200:
                return []

            data = resp.json()
            if data.get('code') != 0:
                return []

            highlights = data.get('data', [])
            result = []

            for h in highlights:
                result.append({
                    'id': h.get('highlightId', ''),
                    'quote': h.get('text', h.get('markText', '')),
                    'book_id': book_id,
                    'chapter': h.get('chapterTitle', ''),
                    'page': f"第{h.get('range', '')}位置",
                    'create_time': h.get('createTime', 0),
                    'style': h.get('style', 0),
                    'color': h.get('colorStyle', 0),
                    'tags': [],
                })

            return result

        except Exception as e:
            logger.error(f"获取划线失败 ({book_id}): {e}")
            return []

    def get_bookmarks(self, book_id):
        """获取书签"""
        try:
            url = f"{self.WEB_URL}/book/get_bookmarks"
            params = {'bookId': book_id}
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    return data.get('data', [])
        except Exception as e:
            logger.error(f"获取书签失败: {e}")
        return []

    def get_reviews(self, book_id):
        """获取书评/想法"""
        try:
            url = f"{self.WEB_URL}/review/list"
            params = {
                'bookId': book_id,
                'maxIdx': 0,
                'listType': 11,
                'mine': 1
            }
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    return data.get('data', {}).get('reviews', [])
        except Exception as e:
            logger.error(f"获取书评失败: {e}")
        return []

    def sync_all_data(self, max_books=50, with_highlights=True):
        """
        同步全部数据

        Args:
            max_books: 最多同步的书籍数量
            with_highlights: 是否同步划线

        Returns:
            dict: 同步结果
        """
        result = {
            'platform': 'wechat',
            'platform_name': '微信读书',
            'books': [],
            'highlights': [],
            'notes': [],
            'sync_time': datetime.now().isoformat(),
            'book_count': 0,
            'highlight_count': 0,
            'success': False,
            'error': None
        }

        try:
            # 1. 检查登录
            user_info = self.check_login()
            if not user_info:
                result['error'] = 'Cookie 无效或已过期，请重新登录'
                return result

            result['user_info'] = user_info

            # 2. 获取书架
            books = self.get_bookshelf()
            if books is None:
                result['error'] = '获取书架失败'
                return result

            # 只保留有阅读记录的书
            books = [b for b in books if b.get('book_status') != 4][:max_books]
            result['books'] = books
            result['book_count'] = len(books)

            # 3. 获取划线
            if with_highlights:
                all_highlights = []
                for i, book in enumerate(books):
                    book_id = book['id']
                    highlights = self.get_highlights(book_id)
                    for h in highlights:
                        h['book_title'] = book['title']
                        h['book_author'] = book['author']
                    all_highlights.extend(highlights)

                    # 避免请求过快
                    if (i + 1) % 5 == 0:
                        time.sleep(1)
                    else:
                        time.sleep(0.3)

                result['highlights'] = all_highlights
                result['highlight_count'] = len(all_highlights)

            result['success'] = True

        except Exception as e:
            logger.error(f"同步数据失败: {e}")
            result['error'] = str(e)

        return result

    @staticmethod
    def get_cookie_guide():
        """获取 Cookie 导入教程"""
        return {
            'title': '微信读书 Cookie 导入教程',
            'steps': [
                {
                    'step': 1,
                    'title': '打开微信读书网页版',
                    'desc': '在电脑浏览器中打开 https://weread.qq.com',
                },
                {
                    'step': 2,
                    'title': '扫码登录',
                    'desc': '使用微信扫码登录微信读书网页版',
                },
                {
                    'step': 3,
                    'title': '打开开发者工具',
                    'desc': '按 F12 或右键 → 检查，打开开发者工具',
                },
                {
                    'step': 4,
                    'title': '找到 Cookie',
                    'desc': '切换到 Network（网络）标签，刷新页面，点击任意一个请求，在 Headers 中找到 Cookie 字段',
                },
                {
                    'step': 5,
                    'title': '复制 Cookie',
                    'desc': '右键 Cookie 值 → 复制值，然后粘贴到下方输入框',
                },
            ],
            'tips': [
                'Cookie 包含您的登录凭证，请勿分享给他人',
                'Cookie 有有效期，过期后需要重新获取',
                '建议使用电脑浏览器操作，手机端获取较麻烦'
            ]
        }


class WeChatScanLogin:
    """
    微信开放平台 - 网站应用扫码登录
    需要企业资质申请 AppID 和 AppSecret
    文档：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
    """

    def __init__(self, app_id=None, app_secret=None, redirect_uri=None):
        self.app_id = app_id or os.environ.get('WECHAT_APP_ID', '')
        self.app_secret = app_secret or os.environ.get('WECHAT_APP_SECRET', '')
        self.redirect_uri = redirect_uri or os.environ.get('WECHAT_REDIRECT_URI', '')
        self.base_url = 'https://open.weixin.qq.com/connect'
        self.api_url = 'https://api.weixin.qq.com/sns'

    def get_qr_connect_url(self, state=None):
        """
        生成微信扫码登录 URL

        Args:
            state: 自定义 state 参数，用于防止 CSRF

        Returns:
            str: 扫码登录 URL
        """
        if not self.app_id:
            return None

        params = [
            f'appid={self.app_id}',
            f'redirect_uri={quote(self.redirect_uri)}',
            'response_type=code',
            'scope=snsapi_login',
            f'state={state or "wechat_login"}'
        ]

        return f"{self.base_url}/qrconnect?{'&'.join(params)}#wechat_redirect"

    def get_authorize_url(self, state=None):
        """
        生成授权 URL（跳转到微信授权页）
        """
        if not self.app_id:
            return None

        params = [
            f'appid={self.app_id}',
            f'redirect_uri={quote(self.redirect_uri)}',
            'response_type=code',
            'scope=snsapi_userinfo',
            f'state={state or "wechat_auth"}'
        ]

        return f"{self.base_url}/oauth2/authorize?{'&'.join(params)}#wechat_redirect"

    def get_access_token(self, code):
        """
        用 code 换取 access_token

        Returns:
            dict: {access_token, expires_in, refresh_token, openid, scope, unionid}
        """
        if not self.app_id or not self.app_secret:
            return None

        try:
            url = f"{self.api_url}/oauth2/access_token"
            params = {
                'appid': self.app_id,
                'secret': self.app_secret,
                'code': code,
                'grant_type': 'authorization_code'
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if 'access_token' in data:
                return data
            else:
                logger.error(f"获取 access_token 失败: {data}")
                return None

        except Exception as e:
            logger.error(f"请求 access_token 异常: {e}")
            return None

    def get_user_info(self, access_token, openid):
        """
        获取用户信息

        Returns:
            dict: {openid, nickname, sex, province, city, country, headimgurl, unionid}
        """
        try:
            url = f"{self.api_url}/userinfo"
            params = {
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN'
            }
            resp = requests.get(url, params=params, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None

    def is_configured(self):
        """检查是否已配置微信开放平台"""
        return bool(self.app_id and self.app_secret and self.redirect_uri)


# ============== 模拟数据（用于演示） ==============
class WeReadMockData:
    """微信读书模拟数据"""

    BOOKS = [
        {
            'id': 'BOOK_ID_SANTI',
            'title': '三体',
            'author': '刘慈欣',
            'cover': '',
            'platform': 'wechat',
            'read_progress': 0.85,
            'highlights_count': 32,
            'book_status': 1,
        },
        {
            'id': 'BOOK_ID_HUOZHE',
            'title': '活着',
            'author': '余华',
            'cover': '',
            'platform': 'wechat',
            'read_progress': 1.0,
            'highlights_count': 25,
            'book_status': 1,
        },
        {
            'id': 'BOOK_ID_TIANLONG',
            'title': '天龙八部',
            'author': '金庸',
            'cover': '',
            'platform': 'wechat',
            'read_progress': 0.6,
            'highlights_count': 18,
            'book_status': 1,
        },
        {
            'id': 'BOOK_ID_RENLISHI',
            'title': '人类简史',
            'author': '尤瓦尔·赫拉利',
            'cover': '',
            'platform': 'wechat',
            'read_progress': 0.45,
            'highlights_count': 15,
            'book_status': 1,
        }
    ]

    HIGHLIGHTS = {
        'BOOK_ID_SANTI': [
            {'quote': '「给岁月以文明，而不是给文明以岁月。」', 'chapter': '第二部 黑暗森林', 'tags': ['#哲学思考', '#文明']},
            {'quote': '「弱小和无知不是生存的障碍，傲慢才是。」', 'chapter': '第二部 黑暗森林', 'tags': ['#人性反思', '#历史教训']},
            {'quote': '「我们都是阴沟里的虫子，但总得有人仰望星空。」', 'chapter': '第一部 地球往事', 'tags': ['#理想主义', '#信念']},
            {'quote': '「前进！前进！不择手段地前进！」', 'chapter': '第三部 死神永生', 'tags': ['#决心', '#名言']},
            {'quote': '「宇宙就是一座黑暗森林，每个文明都是带枪的猎人。」', 'chapter': '第二部 黑暗森林', 'tags': ['#黑暗森林法则', '#宇宙']},
        ],
        'BOOK_ID_HUOZHE': [
            {'quote': '「人是为活着本身而活着，而不是为了活着之外的任何事物所活着。」', 'chapter': '活着', 'tags': ['#生命', '#存在']},
            {'quote': '「以笑的方式哭，在死亡的伴随下活着。」', 'chapter': '活着', 'tags': ['#苦难', '#坚强']},
            {'quote': '「没有什么比时间更具有说服力了，因为时间无需通知我们就可以改变一切。」', 'chapter': '活着', 'tags': ['#时间', '#变迁']},
        ],
        'BOOK_ID_TIANLONG': [
            {'quote': '「有情皆孽，无人不冤。」', 'chapter': '全书主旨', 'tags': ['#江湖', '#命运']},
            {'quote': '「侠之大者，为国为民。」', 'chapter': '郭靖相关', 'tags': ['#侠义', '#责任']},
        ],
        'BOOK_ID_RENLISHI': [
            {'quote': '「人类是唯一能够相信虚构故事的动物。」', 'chapter': '认知革命', 'tags': ['#认知革命', '#虚构']},
            {'quote': '「历史从无正义。」', 'chapter': '农业革命', 'tags': ['#历史', '#公正']},
            {'quote': '「金钱是有史以来最普遍也最有效的互信系统。」', 'chapter': '农业革命', 'tags': ['#金钱', '#信任']},
        ]
    }

    @classmethod
    def get_mock_sync_data(cls):
        books = cls.BOOKS
        all_highlights = []

        for book in books:
            book_id = book['id']
            highlights = cls.HIGHLIGHTS.get(book_id, [])
            for h in highlights:
                h['book_id'] = book_id
                h['book_title'] = book['title']
                h['book_author'] = book['author']
                h['platform'] = 'wechat'
            all_highlights.extend(highlights)

        return {
            'platform': 'wechat',
            'platform_name': '微信读书',
            'books': books,
            'highlights': all_highlights,
            'sync_time': datetime.now().isoformat(),
            'book_count': len(books),
            'highlight_count': len(all_highlights),
            'success': True,
            'user_info': {'nickname': '演示用户', 'user_id': 'mock_user'}
        }
