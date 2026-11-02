"""
豆瓣阅读平台 - 真实数据对接
支持方式：Cookie 导入登录（个人用户可用）
官网：https://read.douban.com
"""

import re
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class DoubanReadAPI:
    """
    豆瓣阅读 API 客户端
    通过 Cookie 方式访问豆瓣阅读网页版，获取真实数据
    """

    BASE_URL = "https://read.douban.com"
    API_URL = "https://read.douban.com/api"

    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://read.douban.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://read.douban.com'
        })

        if cookies:
            self.set_cookies(cookies)

        self.user_info = None

    def set_cookies(self, cookies):
        """设置 Cookie"""
        if isinstance(cookies, str):
            cookie_dict = {}
            for item in cookies.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookie_dict[key.strip()] = value.strip()
            cookies = cookie_dict

        for key, value in cookies.items():
            self.session.cookies.set(key, value, domain='.douban.com')

    def check_login(self):
        """检查登录状态"""
        try:
            url = f"{self.BASE_URL}/reader/"
            resp = self.session.get(url, timeout=10, allow_redirects=False)

            if resp.status_code == 200:
                html = resp.text
                # 查找用户信息
                user_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
                if user_match:
                    try:
                        import json
                        data = json.loads(user_match.group(1))
                        user = data.get('user', data.get('reader', {}).get('user', {}))
                        if user:
                            self.user_info = {
                                'user_id': str(user.get('id', user.get('uid', ''))),
                                'nickname': user.get('name', user.get('nickname', '')),
                                'avatar': user.get('avatar', ''),
                            }
                            return self.user_info
                    except:
                        pass

                # 简单判断：包含"书架"且不包含"登录"
                if '书架' in html and '登录' not in html[:2000]:
                    self.user_info = {
                        'user_id': 'douban_user',
                        'nickname': '豆瓣阅读用户',
                        'avatar': '',
                    }
                    return self.user_info

            if resp.status_code == 302:
                return None

        except Exception as e:
            logger.debug(f"检查豆瓣阅读登录状态失败: {e}")

        return None

    def get_bookshelf(self):
        """获取书架列表"""
        try:
            url = f"{self.BASE_URL}/reader/library"
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return None

            html = resp.text
            books = []

            # 从 HTML 中提取书籍
            book_pattern = r'<div class="book-item[^"]*"[^>]*>.*?<a[^>]*href="/reader/(\d+)/"[^>]*>.*?<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"'
            matches = re.findall(book_pattern, html, re.DOTALL)

            for book_id, title, cover in matches:
                books.append({
                    'id': book_id,
                    'title': title,
                    'author': '',
                    'cover': cover,
                    'platform': 'douban',
                    'read_progress': 0,
                    'highlights_count': 0,
                    'book_status': 1,
                    'last_read': 0,
                })

            # 备用：从 script 标签的 JSON 数据中提取
            if not books:
                json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
                if json_match:
                    try:
                        import json
                        data = json.loads(json_match.group(1))
                        book_list = data.get('library', {}).get('books', data.get('books', []))
                        for book in book_list:
                            books.append({
                                'id': str(book.get('id', book.get('bookId', ''))),
                                'title': book.get('title', ''),
                                'author': book.get('author', ''),
                                'cover': book.get('cover', book.get('image', '')),
                                'platform': 'douban',
                                'read_progress': book.get('progress', 0),
                                'highlights_count': book.get('noteCount', 0),
                                'book_status': 1,
                                'last_read': 0,
                            })
                    except:
                        pass

            return books

        except Exception as e:
            logger.error(f"获取豆瓣阅读书架失败: {e}")
            return None

    def get_highlights(self, book_id):
        """获取书籍划线/标注"""
        try:
            url = f"{self.BASE_URL}/reader/{book_id}/annotations"
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return []

            html = resp.text
            highlights = []

            # 提取划线内容
            highlight_pattern = r'<div class="annotation[^"]*"[^>]*>.*?<p[^>]*class="quote[^"]*"[^>]*>(.*?)</p>'
            matches = re.findall(highlight_pattern, html, re.DOTALL)

            for i, text in enumerate(matches):
                text = re.sub(r'<[^>]+>', '', text).strip()
                if text:
                    highlights.append({
                        'id': f'{book_id}_ann_{i}',
                        'quote': text,
                        'book_id': book_id,
                        'chapter': '',
                        'page': '',
                        'create_time': 0,
                        'color': 0,
                        'tags': [],
                    })

            return highlights

        except Exception as e:
            logger.error(f"获取豆瓣阅读划线失败 ({book_id}): {e}")
            return []

    def sync_all_data(self, max_books=50, with_highlights=True):
        """同步全部数据"""
        result = {
            'platform': 'douban',
            'platform_name': '豆瓣阅读',
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
            user_info = self.check_login()
            if not user_info:
                result['error'] = 'Cookie 无效或已过期，请重新登录'
                return result

            result['user_info'] = user_info

            books = self.get_bookshelf()
            if books is None:
                result['error'] = '获取书架失败'
                return result

            books = books[:max_books]
            result['books'] = books
            result['book_count'] = len(books)

            if with_highlights:
                all_highlights = []
                for i, book in enumerate(books):
                    book_id = book['id']
                    highlights = self.get_highlights(book_id)
                    for h in highlights:
                        h['book_title'] = book['title']
                        h['book_author'] = book['author']
                    all_highlights.extend(highlights)
                    book['highlights_count'] = len(highlights)

                    time.sleep(0.5)

                result['highlights'] = all_highlights
                result['highlight_count'] = len(all_highlights)

            result['success'] = True

        except Exception as e:
            logger.error(f"豆瓣阅读同步失败: {e}")
            result['error'] = str(e)

        return result

    @staticmethod
    def get_cookie_guide():
        """获取 Cookie 导入教程"""
        return {
            'title': '豆瓣阅读 Cookie 导入教程',
            'steps': [
                {'step': 1, 'title': '打开豆瓣阅读', 'desc': '在电脑浏览器中打开 https://read.douban.com'},
                {'step': 2, 'title': '登录豆瓣账号', 'desc': '使用您的豆瓣账号登录'},
                {'step': 3, 'title': '打开开发者工具', 'desc': '按 F12 或右键 → 检查，打开开发者工具'},
                {'step': 4, 'title': '找到 Cookie', 'desc': '切换到 Network（网络）标签，刷新页面，点击任意请求，在 Headers 中找到 Cookie 字段'},
                {'step': 5, 'title': '复制 Cookie', 'desc': '右键 Cookie 值 → 复制值，然后粘贴到下方输入框'},
            ],
            'tips': [
                'Cookie 包含您的登录凭证，请勿分享给他人',
                '豆瓣 Cookie 有效期较长，一般可持续数周'
            ]
        }
