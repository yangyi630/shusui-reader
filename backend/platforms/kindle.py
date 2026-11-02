"""
Kindle 平台 - 真实数据对接
支持方式：Cookie 导入登录（个人用户可用）
官网：https://read.amazon.com  或  https://www.amazon.cn/kindle-dbs
"""

import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests

logger = logging.getLogger(__name__)


class KindleAPI:
    """
    Kindle API 客户端
    通过 Cookie 方式访问 Kindle 云端阅读，获取真实数据
    """

    BASE_URL = "https://read.amazon.com"
    NOTEBOOK_URL = "https://read.amazon.com/notebook"

    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://read.amazon.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
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
            domain = '.amazon.com'
            if '.cn' in key or 'amazon.cn' in key:
                domain = '.amazon.cn'
            self.session.cookies.set(key, value, domain=domain)

    def check_login(self):
        """检查登录状态"""
        try:
            resp = self.session.get(self.NOTEBOOK_URL, timeout=15, allow_redirects=False)
            if resp.status_code == 200:
                self.user_info = {
                    'user_id': 'kindle_user',
                    'nickname': 'Kindle 用户',
                    'avatar': '',
                }
                return self.user_info
            if resp.status_code == 302:
                # 重定向到登录页
                return None
        except Exception as e:
            logger.debug(f"检查 Kindle 登录状态失败: {e}")

        return None

    def get_bookshelf(self):
        """获取书架/笔记列表"""
        try:
            resp = self.session.get(self.NOTEBOOK_URL, timeout=20)
            if resp.status_code != 200:
                return None

            html = resp.text
            books = []

            # 从 HTML 中提取书籍信息
            # Kindle notebook 页面的书籍列表
            book_pattern = r'<div class="kp-notebook-library-each-book[^"]*"[^>]*>.*?<h2[^>]*>(.*?)</h2>.*?<p[^>]*>(.*?)</p>'
            matches = re.findall(book_pattern, html, re.DOTALL)

            asin_pattern = r'data-asin="([^"]+)"'
            asins = re.findall(asin_pattern, html)

            for i, (title, author) in enumerate(matches):
                book_id = asins[i] if i < len(asins) else f'kindle_book_{i}'
                books.append({
                    'id': book_id,
                    'title': title.strip(),
                    'author': author.strip(),
                    'cover': '',
                    'platform': 'kindle',
                    'read_progress': 0,
                    'highlights_count': 0,
                    'book_status': 1,
                    'last_read': 0,
                })

            return books

        except Exception as e:
            logger.error(f"获取 Kindle 书架失败: {e}")
            return None

    def get_highlights(self, book_id):
        """获取书籍划线"""
        try:
            url = f"{self.NOTEBOOK}?asin={book_id}"
            resp = self.session.get(url, timeout=20)
            if resp.status_code != 200:
                return []

            html = resp.text
            highlights = []

            # 提取划线
            highlight_pattern = r'<span[^>]*id="highlight[^"]*"[^>]*>(.*?)</span>'
            matches = re.findall(highlight_pattern, html, re.DOTALL)

            for i, text in enumerate(matches):
                text = re.sub(r'<[^>]+>', '', text).strip()
                if text:
                    highlights.append({
                        'id': f'{book_id}_hl_{i}',
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
            logger.error(f"获取 Kindle 划线失败 ({book_id}): {e}")
            return []

    def sync_all_data(self, max_books=50, with_highlights=True):
        """同步全部数据"""
        result = {
            'platform': 'kindle',
            'platform_name': 'Kindle',
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
            logger.error(f"Kindle 同步失败: {e}")
            result['error'] = str(e)

        return result

    @staticmethod
    def get_cookie_guide():
        """获取 Cookie 导入教程"""
        return {
            'title': 'Kindle Cookie 导入教程',
            'steps': [
                {'step': 1, 'title': '打开 Kindle 云端阅读', 'desc': '在电脑浏览器中打开 https://read.amazon.com/notebook'},
                {'step': 2, 'title': '登录亚马逊账号', 'desc': '使用您的 Kindle 绑定的亚马逊账号登录'},
                {'step': 3, 'title': '打开开发者工具', 'desc': '按 F12 或右键 → 检查，打开开发者工具'},
                {'step': 4, 'title': '找到 Cookie', 'desc': '切换到 Network（网络）标签，刷新页面，点击任意请求，在 Headers 中找到 Cookie 字段'},
                {'step': 5, 'title': '复制 Cookie', 'desc': '右键 Cookie 值 → 复制值，然后粘贴到下方输入框'},
            ],
            'tips': [
                'Kindle 云端阅读地址因地区而异，国内用户可能需要 amazon.cn',
                'Cookie 包含您的登录凭证，请勿分享给他人'
            ]
        }
