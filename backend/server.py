"""
书髓 - 后端服务主入口
跨平台阅读精华聚合 + AI 学习助手

功能：
- 用户认证系统（JWT）
- 扫码登录（模拟微信读书扫码登录流程）
- 多平台数据同步
- 书籍和划线管理
- AI 文档分析
"""

import os
import sys
import json
import time
import uuid
import base64
import hashlib
import logging
import io
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import jwt
import qrcode
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from platforms.weread import WeReadAPI, WeChatScanLogin, WeReadMockData
from platforms.fanqie import FanqieAPI
from platforms.kindle import KindleAPI
from platforms.douban import DoubanReadAPI
from analyzer import analyze_text

# ========== 基础配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_DIR = os.path.join(DATA_DIR, 'users')
SYNC_DIR = os.path.join(DATA_DIR, 'sync')
QR_DIR = os.path.join(DATA_DIR, 'qr_codes')

for d in [DATA_DIR, USERS_DIR, SYNC_DIR, QR_DIR]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== Flask 应用初始化 ==========
app = Flask(__name__, static_folder='../', static_url_path='/')
app.secret_key = os.environ.get('SECRET_KEY', 'shushu_secret_2024!@#')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/socket.io/*": {"origins": "*"}
}, supports_credentials=True)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ========== 常量配置 ==========
JWT_SECRET = os.environ.get('JWT_SECRET', 'shushu_jwt_secret_key_2024')
JWT_EXPIRE_DAYS = 7
QR_EXPIRE_SECONDS = 300  # 5分钟

# ========== 工具函数 ==========
def success(data=None, msg="成功"):
    return jsonify({"code": 0, "msg": msg, "data": data, "time": int(time.time())})

def fail(msg="失败", code=-1, data=None):
    return jsonify({"code": code, "msg": msg, "data": data, "time": int(time.time())})

def get_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]

# ========== 文件存储 ==========
class Store:
    """简单的文件存储"""

    @staticmethod
    def save(path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(path, default=None):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    @staticmethod
    def user_path(uid):
        return os.path.join(USERS_DIR, f'{uid}.json')

    @staticmethod
    def sync_path(uid, platform):
        return os.path.join(SYNC_DIR, f'{uid}_{platform}.json')

# ========== JWT 认证 ==========
def create_token(uid):
    payload = {
        'uid': uid,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['uid']
    except:
        return None

def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return fail("请先登录", 401)
        uid = verify_token(token)
        if not uid:
            return fail("登录已过期", 401)
        user = Store.load(Store.user_path(uid))
        if not user:
            return fail("用户不存在", 401)
        request.uid = uid
        request.user = user
        return f(*args, **kwargs)
    return wrapper

# ========== 用户管理 ==========
class UserManager:
    """用户管理"""

    @staticmethod
    def create_user(username, password):
        uid = sha256(username)
        user = Store.load(Store.user_path(uid))
        if user:
            return None, "用户名已存在"

        user = {
            'uid': uid,
            'username': username,
            'password': md5(password),
            'nickname': username,
            'avatar': '',
            'platforms': {},
            'created_at': get_now(),
            'updated_at': get_now()
        }
        Store.save(Store.user_path(uid), user)
        return uid, None

    @staticmethod
    def login(username, password):
        uid = sha256(username)
        user = Store.load(Store.user_path(uid))
        if not user:
            return None, "用户不存在"
        if user.get('password') != md5(password):
            return None, "密码错误"
        token = create_token(uid)
        user['updated_at'] = get_now()
        Store.save(Store.user_path(uid), user)
        return token, None

    @staticmethod
    def get_user(uid):
        return Store.load(Store.user_path(uid))

    @staticmethod
    def update_user(uid, **kwargs):
        user = Store.load(Store.user_path(uid))
        if not user:
            return None
        user.update(kwargs)
        user['updated_at'] = get_now()
        Store.save(Store.user_path(uid), user)
        return user

    @staticmethod
    def link_platform(uid, platform, platform_uid, platform_data=None):
        """关联平台账号"""
        user = Store.load(Store.user_path(uid))
        if not user:
            return None
        if 'platforms' not in user:
            user['platforms'] = {}
        user['platforms'][platform] = {
            'platform_uid': platform_uid,
            'data': platform_data or {},
            'linked_at': get_now()
        }
        user['updated_at'] = get_now()
        Store.save(Store.user_path(uid), user)
        return user

# ========== 二维码登录管理 ==========
class QRLoginManager:
    """
    扫码登录管理器

    状态流转：
    created -> scanned -> confirmed -> expired
        ↓           ↓
    expired     expired
    """

    def __init__(self):
        self.codes = {}  # qr_id -> {status, uid, platform, created_at, user_info}

    def create(self, platform='wechat'):
        """创建登录二维码"""
        qr_id = str(uuid.uuid4())
        now = time.time()

        # 二维码内容：书髓登录凭证
        qr_data = json.dumps({
            'app': 'shushu',
            'type': 'login',
            'qr_id': qr_id,
            'platform': platform,
            'created_at': now
        })

        # 生成二维码图片
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        self.codes[qr_id] = {
            'qr_id': qr_id,
            'platform': platform,
            'status': 'created',
            'created_at': now,
            'user_info': None,
            'uid': None
        }

        return {
            'qr_id': qr_id,
            'qr_image': f"data:image/png;base64,{img_base64}",
            'expire_in': QR_EXPIRE_SECONDS
        }

    def check(self, qr_id):
        """检查二维码状态"""
        qr = self.codes.get(qr_id)
        if not qr:
            return None
        # 检查是否过期
        if time.time() - qr['created_at'] > QR_EXPIRE_SECONDS:
            qr['status'] = 'expired'
        return qr

    def scan(self, qr_id, user_info):
        """扫描二维码"""
        qr = self.codes.get(qr_id)
        if not qr or qr['status'] != 'created':
            return None
        qr['status'] = 'scanned'
        qr['user_info'] = user_info
        # 通知前端
        socketio.emit('qr_status', {
            'qr_id': qr_id,
            'status': 'scanned',
            'user_info': user_info
        })
        return qr

    def confirm(self, qr_id, uid, platform):
        """确认登录"""
        qr = self.codes.get(qr_id)
        if not qr or qr['status'] != 'scanned':
            return None
        qr['status'] = 'confirmed'
        qr['uid'] = uid
        token = create_token(uid)
        # 通知前端
        socketio.emit('qr_status', {
            'qr_id': qr_id,
            'status': 'confirmed',
            'uid': uid,
            'token': token
        })
        return token

    def cleanup(self):
        """清理过期二维码"""
        now = time.time()
        expired_ids = [
            qid for qid, qr in self.codes.items()
            if now - qr['created_at'] > QR_EXPIRE_SECONDS * 2
        ]
        for qid in expired_ids:
            del self.codes[qid]
        return len(expired_ids)

qr_manager = QRLoginManager()

# ========== 模拟平台数据 ==========
class MockPlatformData:
    """模拟各平台数据，用于演示"""

    BOOKS = {
        'wechat': [
            {
                'id': 'wc_001', 'title': '三体', 'author': '刘慈欣',
                'cover': 'santi', 'platform': 'wechat',
                'highlights_count': 32, 'read_progress': 0.85
            },
            {
                'id': 'wc_002', 'title': '天龙八部', 'author': '金庸',
                'cover': 'wuxia', 'platform': 'wechat',
                'highlights_count': 18, 'read_progress': 0.6
            }
        ],
        'fanqie': [
            {
                'id': 'fq_001', 'title': '活着', 'author': '余华',
                'cover': 'huozhe', 'platform': 'fanqie',
                'highlights_count': 25, 'read_progress': 1.0
            },
            {
                'id': 'fq_002', 'title': '百年孤独', 'author': '马尔克斯',
                'cover': 'bainian', 'platform': 'fanqie',
                'highlights_count': 22, 'read_progress': 0.5
            }
        ],
        'kindle': [
            {
                'id': 'kd_001', 'title': '存在与虚无', 'author': '萨特',
                'cover': 'philosophy', 'platform': 'kindle',
                'highlights_count': 12, 'read_progress': 0.3
            },
            {
                'id': 'kd_002', 'title': '人类简史', 'author': '尤瓦尔·赫拉利',
                'cover': 'jian', 'platform': 'kindle',
                'highlights_count': 15, 'read_progress': 0.7
            }
        ],
        'douban': [
            {
                'id': 'db_001', 'title': '万历十五年', 'author': '黄仁宇',
                'cover': 'history', 'platform': 'douban',
                'highlights_count': 8, 'read_progress': 0.9
            },
            {
                'id': 'db_002', 'title': '围城', 'author': '钱钟书',
                'cover': 'weicheng', 'platform': 'douban',
                'highlights_count': 11, 'read_progress': 1.0
            }
        ]
    }

    HIGHLIGHTS = {
        'wc_001': [
            {'quote': '「给岁月以文明，而不是给文明以岁月。」', 'page': '第217页', 'tags': ['#哲学思考', '#文明']},
            {'quote': '「我们都是阴沟里的虫子，但总得有人仰望星空。」', 'page': '第156页', 'tags': ['#理想主义', '#信念']},
            {'quote': '「弱小和无知不是生存的障碍，傲慢才是。」', 'page': '第89页', 'tags': ['#人性反思', '#历史教训']}
        ],
        'wc_002': [
            {'quote': '「有情皆孽，无人不冤。」', 'page': '第342页', 'tags': ['#江湖', '#命运']},
            {'quote': '「侠之大者，为国为民。」', 'page': '第518页', 'tags': ['#侠义', '#责任']}
        ],
        'fq_001': [
            {'quote': '「人是为活着本身而活着，而不是为了活着之外的任何事物所活着。」', 'page': '第123页', 'tags': ['#生命', '#存在']},
            {'quote': '「以笑的方式哭，在死亡的伴随下活着。」', 'page': '第87页', 'tags': ['#苦难', '#坚强']}
        ],
        'fq_002': [
            {'quote': '「生命中所有的灿烂，终要用寂寞来偿还。」', 'page': '第234页', 'tags': ['#孤独', '#宿命']},
            {'quote': '「过去都是假的，回忆是一条没有归途的路。」', 'page': '第156页', 'tags': ['#记忆', '#时间']}
        ],
        'kd_001': [
            {'quote': '「人是自己的创造者。」', 'page': '第45页', 'tags': ['#存在主义', '#自由']},
            {'quote': '「他人即地狱。」', 'page': '第189页', 'tags': ['#人际关系', '#异化']}
        ],
        'kd_002': [
            {'quote': '「人类是唯一能够相信虚构故事的动物。」', 'page': '第89页', 'tags': ['#认知革命', '#虚构']},
            {'quote': '「历史从无正义。」', 'page': '第234页', 'tags': ['#历史', '#公正']}
        ],
        'db_001': [
            {'quote': '「中国两千年来，以道德代替法制，至明代而极，这就是一切问题的症结。」', 'page': '第56页', 'tags': ['#历史', '#制度']}
        ],
        'db_002': [
            {'quote': '「婚姻是一座围城，城外的人想进去，城里的人想出来。」', 'page': '第134页', 'tags': ['#婚姻', '#人生']},
            {'quote': '「对于丑人，细看是一种残忍。」', 'page': '第78页', 'tags': ['#审美', '#人性']}
        ]
    }

    PLATFORM_NAMES = {
        'wechat': '微信读书',
        'fanqie': '番茄读书',
        'kindle': 'Kindle',
        'douban': '豆瓣阅读'
    }

# ========== 数据同步管理 ==========
class SyncManager:
    """数据同步管理器"""

    @staticmethod
    def sync_platform(uid, platform, use_mock=True, cookies=None):
        """
        同步平台数据

        Args:
            uid: 用户ID
            platform: 平台名称
            use_mock: 是否使用模拟数据
            cookies: Cookie 字符串
        """
        if cookies:
            if platform == 'wechat':
                return SyncManager._sync_weread(uid, cookies)
            elif platform == 'fanqie':
                return SyncManager._sync_fanqie(uid, cookies)
            elif platform == 'kindle':
                return SyncManager._sync_kindle(uid, cookies)
            elif platform == 'douban':
                return SyncManager._sync_douban(uid, cookies)
        elif use_mock:
            return SyncManager._mock_sync(uid, platform)
        else:
            return None

    @staticmethod
    def _save_platform_cookie(uid, platform, cookie_str, result):
        """保存 Cookie 到用户信息"""
        user = Store.load(Store.user_path(uid))
        if user:
            if 'platforms' not in user:
                user['platforms'] = {}
            user['platforms'][platform] = {
                'platform_uid': result.get('user_info', {}).get('user_id', ''),
                'cookie': cookie_str,
                'linked_at': get_now(),
                'last_sync': get_now(),
                'user_info': result.get('user_info', {})
            }
            user['updated_at'] = get_now()
            Store.save(Store.user_path(uid), user)

    @staticmethod
    def _sync_weread(uid, cookie_str):
        """同步微信读书真实数据"""
        try:
            api = WeReadAPI(cookie_str)
            result = api.sync_all_data(max_books=50, with_highlights=True)
            if result.get('success'):
                result['synced_at'] = get_now()
                Store.save(Store.sync_path(uid, 'wechat'), result)
                SyncManager._save_platform_cookie(uid, 'wechat', cookie_str, result)
            return result
        except Exception as e:
            logger.error(f"微信读书同步失败: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _sync_fanqie(uid, cookie_str):
        """同步番茄读书真实数据"""
        try:
            api = FanqieAPI(cookie_str)
            result = api.sync_all_data(max_books=50, with_highlights=True)
            if result.get('success'):
                result['synced_at'] = get_now()
                Store.save(Store.sync_path(uid, 'fanqie'), result)
                SyncManager._save_platform_cookie(uid, 'fanqie', cookie_str, result)
            return result
        except Exception as e:
            logger.error(f"番茄读书同步失败: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _sync_kindle(uid, cookie_str):
        """同步 Kindle 真实数据"""
        try:
            api = KindleAPI(cookie_str)
            result = api.sync_all_data(max_books=50, with_highlights=True)
            if result.get('success'):
                result['synced_at'] = get_now()
                Store.save(Store.sync_path(uid, 'kindle'), result)
                SyncManager._save_platform_cookie(uid, 'kindle', cookie_str, result)
            return result
        except Exception as e:
            logger.error(f"Kindle 同步失败: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _sync_douban(uid, cookie_str):
        """同步豆瓣阅读真实数据"""
        try:
            api = DoubanReadAPI(cookie_str)
            result = api.sync_all_data(max_books=50, with_highlights=True)
            if result.get('success'):
                result['synced_at'] = get_now()
                Store.save(Store.sync_path(uid, 'douban'), result)
                SyncManager._save_platform_cookie(uid, 'douban', cookie_str, result)
            return result
        except Exception as e:
            logger.error(f"豆瓣阅读同步失败: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _mock_sync(uid, platform):
        """模拟同步"""
        if platform == 'wechat':
            result = WeReadMockData.get_mock_sync_data()
            result['synced_at'] = get_now()
            Store.save(Store.sync_path(uid, platform), result)
            return result

        books = MockPlatformData.BOOKS.get(platform, [])
        all_highlights = []

        for book in books:
            book_id = book['id']
            highlights = MockPlatformData.HIGHLIGHTS.get(book_id, [])
            for h in highlights:
                h['book_id'] = book_id
                h['book_title'] = book['title']
                h['book_author'] = book['author']
            all_highlights.extend(highlights)

        sync_data = {
            'platform': platform,
            'platform_name': MockPlatformData.PLATFORM_NAMES.get(platform, platform),
            'books': books,
            'highlights': all_highlights,
            'synced_at': get_now(),
            'book_count': len(books),
            'highlight_count': len(all_highlights),
            'success': True
        }

        Store.save(Store.sync_path(uid, platform), sync_data)
        return sync_data

    @staticmethod
    def check_platform_cookie(platform, cookie_str):
        """检查平台 Cookie 是否有效"""
        try:
            if platform == 'wechat':
                api = WeReadAPI(cookie_str)
            elif platform == 'fanqie':
                api = FanqieAPI(cookie_str)
            elif platform == 'kindle':
                api = KindleAPI(cookie_str)
            elif platform == 'douban':
                api = DoubanReadAPI(cookie_str)
            else:
                return {'valid': False, 'error': '不支持的平台'}

            user_info = api.check_login()
            if user_info:
                return {'valid': True, 'user_info': user_info}
            else:
                return {'valid': False, 'error': 'Cookie 无效或已过期'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    @staticmethod
    def get_cookie_guide(platform='wechat'):
        """获取 Cookie 导入教程"""
        if platform == 'wechat':
            return WeReadAPI.get_cookie_guide()
        elif platform == 'fanqie':
            return FanqieAPI.get_cookie_guide()
        elif platform == 'kindle':
            return KindleAPI.get_cookie_guide()
        elif platform == 'douban':
            return DoubanReadAPI.get_cookie_guide()
        return None

    @staticmethod
    def get_sync_data(uid, platform=None):
        """获取同步数据"""
        if platform:
            return Store.load(Store.sync_path(uid, platform))
        else:
            # 获取所有平台数据
            result = {}
            for p in ['wechat', 'fanqie', 'kindle', 'douban']:
                data = Store.load(Store.sync_path(uid, p))
                if data:
                    result[p] = data
            return result

    @staticmethod
    def get_all_books(uid):
        """获取所有书籍（聚合多平台）"""
        all_books = []
        for p in ['wechat', 'fanqie', 'kindle', 'douban']:
            data = Store.load(Store.sync_path(uid, p))
            if data and 'books' in data:
                all_books.extend(data['books'])
        return all_books

    @staticmethod
    def get_all_highlights(uid, book_id=None):
        """获取所有划线"""
        all_highlights = []
        for p in ['wechat', 'fanqie', 'kindle', 'douban']:
            data = Store.load(Store.sync_path(uid, p))
            if data and 'highlights' in data:
                if book_id:
                    all_highlights.extend(
                        [h for h in data['highlights'] if h.get('book_id') == book_id]
                    )
                else:
                    all_highlights.extend(data['highlights'])
        return all_highlights

# ========== API 路由 ==========

# --- 基础路由 ---
@app.route('/api/health')
def health():
    """健康检查"""
    return success({
        'service': '书髓后端服务',
        'version': '1.0.0',
        'status': 'running',
        'time': get_now()
    })

@app.route('/')
def index():
    """首页 - 返回前端页面"""
    return send_from_directory(app.static_folder, 'index.html')

# --- 用户认证 ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    """注册"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return fail("用户名和密码不能为空")
    if len(username) < 2 or len(password) < 4:
        return fail("用户名至少2位，密码至少4位")

    uid, err = UserManager.create_user(username, password)
    if err:
        return fail(err)

    token = create_token(uid)
    user = UserManager.get_user(uid)
    return success({
        'uid': uid,
        'token': token,
        'user': {k: v for k, v in user.items() if k != 'password'}
    }, "注册成功")

@app.route('/api/auth/login', methods=['POST'])
def login():
    """登录"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return fail("用户名和密码不能为空")

    token, err = UserManager.login(username, password)
    if err:
        return fail(err)

    user = UserManager.get_user(sha256(username))
    return success({
        'token': token,
        'user': {k: v for k, v in user.items() if k != 'password'}
    }, "登录成功")

@app.route('/api/auth/info')
@auth_required
def get_user_info():
    """获取用户信息"""
    user = request.user
    # 移除敏感信息
    user.pop('password', None)
    return success(user)

# --- 扫码登录 ---
# --- 微信开放平台扫码登录 ---
@app.route('/api/wechat/qrcode')
def wechat_qrcode():
    """
    获取微信扫码登录二维码（微信开放平台方式）
    需配置 WECHAT_APP_ID, WECHAT_APP_SECRET, WECHAT_REDIRECT_URI
    """
    wechat = WeChatScanLogin()

    if not wechat.is_configured():
        # 未配置微信开放平台，返回提示
        return success({
            'available': False,
            'message': '微信开放平台未配置',
            'guide': '需要在微信开放平台申请网站应用，获取 AppID 和 AppSecret'
        })

    state = str(uuid.uuid4())
    qr_url = wechat.get_qr_connect_url(state=state)

    return success({
        'available': True,
        'qr_url': qr_url,
        'state': state,
        'redirect_uri': wechat.redirect_uri
    })

@app.route('/api/wechat/callback')
def wechat_callback():
    """微信扫码登录回调"""
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return fail('授权失败：缺少 code')

    wechat = WeChatScanLogin()
    if not wechat.is_configured():
        return fail('微信开放平台未配置')

    # 获取 access_token
    token_data = wechat.get_access_token(code)
    if not token_data:
        return fail('获取 access_token 失败')

    # 获取用户信息
    user_info = wechat.get_user_info(
        token_data['access_token'],
        token_data['openid']
    )

    if not user_info or 'openid' not in user_info:
        return fail('获取用户信息失败')

    # 创建或登录用户
    openid = user_info['openid']
    unionid = user_info.get('unionid', '')
    uid = sha256(f'wechat:{openid}')

    user = Store.load(Store.user_path(uid))
    if not user:
        user = {
            'uid': uid,
            'username': f'wx_{openid[:8]}',
            'password': md5(uid),  # 随机密码
            'nickname': user_info.get('nickname', '微信用户'),
            'avatar': user_info.get('headimgurl', ''),
            'platforms': {
                'wechat': {
                    'platform_uid': openid,
                    'unionid': unionid,
                    'openid': openid,
                    'user_info': user_info,
                    'linked_at': get_now()
                }
            },
            'created_at': get_now(),
            'updated_at': get_now()
        }
        Store.save(Store.user_path(uid), user)
    else:
        user['nickname'] = user_info.get('nickname', user.get('nickname', ''))
        user['avatar'] = user_info.get('headimgurl', user.get('avatar', ''))
        if 'platforms' not in user:
            user['platforms'] = {}
        user['platforms']['wechat'] = {
            'platform_uid': openid,
            'unionid': unionid,
            'openid': openid,
            'user_info': user_info,
            'linked_at': get_now()
        }
        user['updated_at'] = get_now()
        Store.save(Store.user_path(uid), user)

    # 生成 token
    token = create_token(uid)

    # 返回 HTML 页面（关闭窗口并通知父页面）
    return f"""
    <html><body>
    <script>
    if (window.opener) {{
        window.opener.postMessage({{
            type: 'wechat_login_success',
            token: '{token}',
            user: JSON.stringify({json.dumps({k:v for k,v in user.items() if k != 'password'}, ensure_ascii=False)})
        }}, '*');
        window.close();
    }} else {{
        document.body.innerHTML = '<div style="text-align:center;padding:50px;font-family:sans-serif;"><h2>登录成功</h2><p>正在跳转...</p></div>';
        setTimeout(() => {{ location.href = '/app.html'; }}, 1000);
    }}
    </script>
    </body></html>
    """

@app.route('/api/qr/create')
def create_qr():
    """创建登录二维码"""
    platform = request.args.get('platform', 'wechat')
    result = qr_manager.create(platform)
    return success(result)

@app.route('/api/qr/check/<qr_id>')
def check_qr(qr_id):
    """检查二维码状态"""
    qr = qr_manager.check(qr_id)
    if not qr:
        return fail("二维码不存在或已过期", 404)
    return success({
        'qr_id': qr_id,
        'status': qr['status'],
        'user_info': qr.get('user_info')
    })

@app.route('/api/qr/scan', methods=['POST'])
def scan_qr():
    """
    扫码接口（模拟平台扫码动作）

    真实场景中，这个接口由微信读书App扫码后调用
    在这里我们提供一个模拟接口用于演示
    """
    data = request.get_json() or {}
    qr_id = data.get('qr_id')
    platform = data.get('platform', 'wechat')
    mock_user = data.get('user_info', {
        'nickname': '书髓用户',
        'avatar': '',
        'platform_uid': f'mock_{platform}_{int(time.time())}'
    })

    if not qr_id:
        return fail("缺少qr_id")

    qr = qr_manager.scan(qr_id, mock_user)
    if not qr:
        return fail("扫码失败：二维码状态无效")

    return success({
        'qr_id': qr_id,
        'status': 'scanned',
        'user_info': mock_user
    }, "扫码成功，请在手机上确认")

@app.route('/api/qr/confirm', methods=['POST'])
def confirm_qr():
    """
    确认登录接口（模拟手机端确认）

    真实场景中，这个接口由微信读书App确认后调用
    """
    data = request.get_json() or {}
    qr_id = data.get('qr_id')
    platform = data.get('platform', 'wechat')
    platform_uid = data.get('platform_uid', f'mock_{platform}_user')

    if not qr_id:
        return fail("缺少qr_id")

    # 创建或获取用户
    uid = sha256(f'{platform}:{platform_uid}')
    user = Store.load(Store.user_path(uid))
    if not user:
        user = {
            'uid': uid,
            'username': f'{platform}_{platform_uid[:8]}',
            'password': md5('123456'),  # 默认密码
            'nickname': f'{MockPlatformData.PLATFORM_NAMES.get(platform, platform)}用户',
            'avatar': '',
            'platforms': {},
            'created_at': get_now(),
            'updated_at': get_now()
        }
        Store.save(Store.user_path(uid), user)

    # 关联平台
    UserManager.link_platform(uid, platform, platform_uid)

    # 确认登录
    token = qr_manager.confirm(qr_id, uid, platform)
    if not token:
        return fail("确认失败：二维码状态无效")

    user = UserManager.get_user(uid)
    return success({
        'token': token,
        'uid': uid,
        'user': {k: v for k, v in user.items() if k != 'password'}
    }, "登录成功")

# --- 平台数据 ---
@app.route('/api/platform/list')
@auth_required
def platform_list():
    """获取已关联的平台列表"""
    user = request.user
    platforms = user.get('platforms', {})
    result = []
    for key, val in platforms.items():
        sync_data = SyncManager.get_sync_data(request.uid, key)
        result.append({
            'platform': key,
            'name': MockPlatformData.PLATFORM_NAMES.get(key, key),
            'linked_at': val.get('linked_at'),
            'book_count': sync_data.get('book_count', 0) if sync_data else 0,
            'highlight_count': sync_data.get('highlight_count', 0) if sync_data else 0
        })
    return success(result)

@app.route('/api/platform/cookie/guide/<platform>')
def get_cookie_guide(platform):
    """获取 Cookie 导入教程"""
    guide = SyncManager.get_cookie_guide(platform)
    if guide:
        return success(guide)
    return fail(f"暂不支持该平台: {platform}")

@app.route('/api/platform/cookie/check', methods=['POST'])
def check_cookie():
    """检查 Cookie 是否有效"""
    data = request.get_json() or {}
    platform = data.get('platform', 'wechat')
    cookie_str = data.get('cookie', '')

    if not cookie_str:
        return fail("Cookie 不能为空")

    if platform == 'wechat':
        result = SyncManager.check_platform_cookie('wechat', cookie_str)
        return success(result)
    elif platform == 'fanqie':
        result = SyncManager.check_platform_cookie('fanqie', cookie_str)
        return success(result)
    elif platform == 'kindle':
        result = SyncManager.check_platform_cookie('kindle', cookie_str)
        return success(result)
    elif platform == 'douban':
        result = SyncManager.check_platform_cookie('douban', cookie_str)
        return success(result)
    else:
        return fail(f"暂不支持该平台: {platform}")

@app.route('/api/platform/sync/<platform>', methods=['POST'])
@auth_required
def sync_platform(platform):
    """同步平台数据"""
    if platform not in ['wechat', 'fanqie', 'kindle', 'douban']:
        return fail(f"不支持的平台: {platform}")

    data = request.get_json() or {}
    cookie_str = data.get('cookie')
    use_mock = data.get('use_mock', True) if not cookie_str else False
    platform_name = MockPlatformData.PLATFORM_NAMES.get(platform, platform)

    # 如果提供了 Cookie，使用真实同步
    if cookie_str:
        sync_data = SyncManager.sync_platform(
            request.uid, platform, use_mock=False, cookies=cookie_str
        )
        if sync_data.get('success'):
            return success(sync_data, f"{platform_name}同步成功")
        else:
            return fail(sync_data.get('error', '同步失败'), data=sync_data)

    # 检查是否已关联且有保存的 Cookie
    user = request.user
    platforms = user.get('platforms', {})
    if platform in platforms and platforms[platform].get('cookie'):
        saved_cookie = platforms[platform]['cookie']
        sync_data = SyncManager.sync_platform(
            request.uid, platform, use_mock=False, cookies=saved_cookie
        )
        if sync_data.get('success'):
            return success(sync_data, f"{platform_name}同步成功")
        logger.info(f"保存的 Cookie 已失效，使用模拟数据: {sync_data.get('error')}")

    # 使用模拟数据
    if platform not in platforms:
        platform_uid = f'mock_{platform}_{request.uid}'
        UserManager.link_platform(request.uid, platform, platform_uid)

    sync_data = SyncManager.sync_platform(request.uid, platform, use_mock=use_mock)
    return success(sync_data, f"{platform_name}同步成功")

@app.route('/api/books')
@auth_required
def get_books():
    """获取所有书籍"""
    platform = request.args.get('platform')
    if platform:
        data = SyncManager.get_sync_data(request.uid, platform)
        books = data.get('books', []) if data else []
    else:
        books = SyncManager.get_all_books(request.uid)
    return success(books)

@app.route('/api/highlights')
@auth_required
def get_highlights():
    """获取划线"""
    book_id = request.args.get('book_id')
    platform = request.args.get('platform')

    if platform:
        data = SyncManager.get_sync_data(request.uid, platform)
        highlights = data.get('highlights', []) if data else []
        if book_id:
            highlights = [h for h in highlights if h.get('book_id') == book_id]
    else:
        highlights = SyncManager.get_all_highlights(request.uid, book_id)

    return success(highlights)

# --- 文档分析 ---
@app.route('/api/analyze', methods=['POST'])
@auth_required
def analyze_document():
    """分析上传的文档"""
    if 'file' not in request.files:
        return fail("请上传文件")

    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return fail("仅支持 .txt 格式文件")

    content = file.read().decode('utf-8', errors='ignore')
    filename = file.filename

    # 智能文本分析
    result = analyze_text(content, filename)

    # 保存分析历史
    user_dir = os.path.join(USERS_DIR, request.uid, 'analyses')
    os.makedirs(user_dir, exist_ok=True)
    analysis_id = str(int(time.time()))
    analysis_file = os.path.join(user_dir, f'{analysis_id}.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump({'id': analysis_id, 'filename': filename,
                   'result': result, 'created_at': get_now()}, f,
                  ensure_ascii=False, indent=2)

    return success(result, "分析完成")

# ========== WebSocket ==========
@socketio.on('connect')
def on_connect():
    logger.info(f"WebSocket连接: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    logger.info(f"WebSocket断开: {request.sid}")

@socketio.on('qr_poll')
def on_qr_poll(data):
    """轮询二维码状态"""
    qr_id = data.get('qr_id')
    if qr_id:
        qr = qr_manager.check(qr_id)
        if qr:
            emit('qr_status', {
                'qr_id': qr_id,
                'status': qr['status'],
                'user_info': qr.get('user_info')
            })

# ========== 定时任务 ==========
scheduler = BackgroundScheduler()

def cleanup_task():
    count = qr_manager.cleanup()
    if count:
        logger.info(f"清理了 {count} 个过期二维码")

scheduler.add_job(cleanup_task, 'interval', minutes=5)

# ========== 启动 ==========
if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("  书髓 - 后端服务启动")
    logger.info(f"  服务地址: http://0.0.0.0:5000")
    logger.info(f"  数据目录: {DATA_DIR}")
    logger.info("=" * 50)

    scheduler.start()

    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("服务停止")
        scheduler.shutdown()
