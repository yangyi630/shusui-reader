"""
番茄读书平台 - 真实数据对接
支持方式：Cookie 导入登录（个人用户可用）
官网：https://fanqienovel.com
"""

import os
import re
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class FanqieAPI:
    """
    番茄读书 API 客户端
    通过 Cookie 方式访问番茄读书网页版接口，获取真实数据
    """

    BASE_URL = "https://fanqienovel.com"
    API_URL = "https://fanqienovel.com/api"

    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://fanqienovel.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://fanqienovel.com'
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
            self.session.cookies.set(key, value, domain='.fanqienovel.com')

    def check_login(self):
        """检查登录状态"""
        try:
            url = f"{self.API_URL}/user/info"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and data.get('data'):
                    user_data = data['data']
                    self.user_info = {
                        'user_id': user_data.get('user_id', user_data.get('userId', '')),
                        'nickname': user_data.get('nickname', user_data.get('name', '')),
                        'avatar': user_data.get('avatar', user_data.get('avatarUrl', '')),
                    }
                    return self.user_info
        except Exception as e:
            logger.debug(f"检查番茄登录状态失败: {e}")

        # 备用：访问书架判断
        try:
            books = self.get_bookshelf()
            if books is not None and len(books) > 0:
                self.user_info = {
                    'user_id': 'fanqie_cookie_user',
                    'nickname': '番茄读书用户',
                    'avatar': '',
                }
                return self.user_info
        except:
            pass

        return None

    def get_bookshelf(self, count=50):
        """获取书架列表"""
        all_books = []
        try:
            url = f"{self.API_URL}/book/shelf"
            params = {'count': count, 'offset': 0}
            resp = self.session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    books = data.get('data', [])
                    for book in books:
                        all_books.append({
                            'id': str(book.get('book_id', book.get('bookId', ''))),
                            'title': book.get('book_name', book.get('title', '')),
                            'author': book.get('author', ''),
                            'cover': book.get('cover', book.get('thumbUrl', '')),
                            'platform': 'fanqie',
                            'read_progress': book.get('read_progress', book.get('progress', 0)),
                            'highlights_count': book.get('note_count', book.get('markCount', 0)),
                            'book_status': book.get('status', 1),
                            'last_read': book.get('last_read_time', 0),
                        })
            return all_books
        except Exception as e:
            logger.error(f"获取番茄书架失败: {e}")
            return None

    def get_highlights(self, book_id):
        """获取书籍划线/标注"""
        try:
            url = f"{self.API_URL}/book/highlights"
            params = {'book_id': book_id}
            resp = self.session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    highlights = data.get('data', [])
                    result = []
                    for h in highlights:
                        result.append({
                            'id': str(h.get('highlight_id', h.get('id', ''))),
                            'quote': h.get('text', h.get('content', '')),
                            'book_id': str(book_id),
                            'chapter': h.get('chapter_title', h.get('chapterName', '')),
                            'page': h.get('position', ''),
                            'create_time': h.get('create_time', 0),
                            'color': h.get('color', 0),
                            'tags': [],
                        })
                    return result
            return []
        except Exception as e:
            logger.error(f"获取番茄划线失败 ({book_id}): {e}")
            return []

    def sync_all_data(self, max_books=50, with_highlights=True):
        """同步全部数据"""
        result = {
            'platform': 'fanqie',
            'platform_name': '番茄读书',
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

                    if (i + 1) % 5 == 0:
                        time.sleep(1)
                    else:
                        time.sleep(0.3)

                result['highlights'] = all_highlights
                result['highlight_count'] = len(all_highlights)

            result['success'] = True

        except Exception as e:
            logger.error(f"番茄同步失败: {e}")
            result['error'] = str(e)

        return result

    @staticmethod
    def get_cookie_guide():
        """获取 Cookie 导入教程"""
        return {
            'title': '番茄读书 Cookie 导入教程',
            'steps': [
                {'step': 1, 'title': '打开番茄读书网页版', 'desc': '在电脑浏览器中打开 https://fanqienovel.com'},
                {'step': 2, 'title': '扫码登录', 'desc': '使用抖音/头条账号扫码登录番茄读书网页版'},
                {'step': 3, 'title': '打开开发者工具', 'desc': '按 F12 或右键 → 检查，打开开发者工具'},
                {'step': 4, 'title': '找到 Cookie', 'desc': '切换到 Network（网络）标签，刷新页面，点击任意请求，在 Headers 中找到 Cookie 字段'},
                {'step': 5, 'title': '复制 Cookie', 'desc': '右键 Cookie 值 → 复制值，然后粘贴到下方输入框'},
            ],
            'tips': [
                'Cookie 包含您的登录凭证，请勿分享给他人',
                'Cookie 有有效期，过期后需要重新获取'
            ]
        }
