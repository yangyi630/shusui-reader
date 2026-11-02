"""
更新 app.html - 增加真实的登录方式
1. 微信扫码登录（微信开放平台）
2. Cookie 导入登录（微信读书真实数据）
3. 连接平台时的 Cookie 导入界面
"""

import re

file_path = r'c:\Users\92783\Desktop\代码\书髓\app.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 添加新的 CSS 样式 ==========
new_css = '''
        /* Cookie 导入弹窗 */
        .modal-mask {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1500;
            padding: 1rem;
        }
        .modal-mask.active { display: flex; }
        .modal {
            background: white;
            border-radius: 16px;
            width: 100%;
            max-width: 480px;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-title { font-size: 1.1rem; font-weight: 600; }
        .modal-close {
            font-size: 1.5rem;
            color: #999;
            cursor: pointer;
            line-height: 1;
        }
        .modal-body { padding: 1.25rem; }
        .modal-footer {
            padding: 1rem 1.25rem;
            border-top: 1px solid #eee;
            display: flex;
            gap: 0.75rem;
            justify-content: flex-end;
        }

        .cookie-textarea {
            width: 100%;
            min-height: 120px;
            padding: 0.75rem;
            border: 2px solid #eee;
            border-radius: 8px;
            font-size: 0.85rem;
            font-family: monospace;
            resize: vertical;
            line-height: 1.5;
        }
        .cookie-textarea:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(200,149,108,0.1);
        }

        .guide-steps {
            background: #faf8f5;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .guide-step {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }
        .guide-step:last-child { margin-bottom: 0; }
        .step-num {
            flex-shrink: 0;
            width: 24px; height: 24px;
            background: var(--accent);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .step-content { font-size: 0.85rem; line-height: 1.6; }
        .step-title { font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
        .step-desc { color: var(--text-2); }

        .tip-box {
            background: rgba(78,205,196,0.1);
            border-left: 3px solid var(--wechat);
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.8rem;
            color: var(--text-2);
            margin-bottom: 1rem;
            line-height: 1.6;
        }

        .btn-wechat {
            width: 100%;
            padding: 0.875rem;
            background: #07c160;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.3s;
        }
        .btn-wechat:hover { background: #06ae56; transform: translateY(-1px); }
        .btn-wechat:disabled { opacity: 0.6; cursor: not-allowed; }

        .login-method-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        .login-method-tab {
            flex: 1;
            min-width: 80px;
            padding: 0.6rem 0.5rem;
            background: #f5f5f5;
            border: none;
            border-radius: 8px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            color: var(--text-2);
        }
        .login-method-tab.active {
            background: rgba(200,149,108,0.15);
            color: var(--accent-2);
            font-weight: 600;
        }
        .login-method-icon { font-size: 1.25rem; margin-bottom: 0.25rem; }
'''

# 在 </style> 之前插入新 CSS
content = content.replace('    </style>', new_css + '    </style>')

# ========== 2. 修改登录页 HTML ==========
# 替换登录选项卡
old_tabs = '''            <div class="login-tabs">
                <button class="login-tab active" onclick="switchLoginTab('qr')">扫码登录</button>
                <button class="login-tab" onclick="switchLoginTab('pwd')">账号密码</button>
            </div>'''

new_tabs = '''            <div class="login-tabs">
                <button class="login-tab active" onclick="switchLoginTab('wechat')">微信登录</button>
                <button class="login-tab" onclick="switchLoginTab('pwd')">账号密码</button>
            </div>'''

content = content.replace(old_tabs, new_tabs)

# 替换二维码登录部分
old_qr_login_start = '            <!-- 二维码登录 -->'
old_qr_login_end = '            </div>\n\n            <!-- 账号密码登录 -->'

# 找到旧的二维码登录部分
pattern = r'            <!-- 二维码登录 -->.*?            </div>\n\n            <!-- 账号密码登录 -->'
match = re.search(pattern, content, re.DOTALL)

if match:
    wechat_login_html = '''            <!-- 微信登录 -->
            <div id="wechatLogin">
                <div class="login-method-tabs">
                    <button class="login-method-tab active" onclick="switchWechatLogin('scan')">
                        <div class="login-method-icon">💬</div>
                        <div>微信扫码</div>
                    </button>
                    <button class="login-method-tab" onclick="switchWechatLogin('cookie')">
                        <div class="login-method-icon">🍪</div>
                        <div>Cookie导入</div>
                    </button>
                </div>

                <!-- 微信扫码 -->
                <div id="wechatScanLogin">
                    <div class="qr-login">
                        <div class="qr-code-box" id="wechatQrBox">
                            <div style="color:#999; text-align:center;">
                                <div style="font-size:2rem; margin-bottom:0.5rem;">💬</div>
                                <div style="font-size:0.85rem;">正在加载微信登录...</div>
                            </div>
                        </div>
                        <div class="qr-tip" id="wechatQrTip">使用微信扫码登录书髓</div>
                        <div class="qr-status" id="wechatQrStatus">等待扫码...</div>
                        <div class="qr-actions">
                            <button class="btn-secondary" onclick="refreshWechatQR()">刷新二维码</button>
                        </div>
                    </div>
                </div>

                <!-- Cookie 导入 -->
                <div id="wechatCookieLogin" style="display:none;">
                    <div class="tip-box">
                        💡 导入微信读书 Cookie，可获取您的真实书架和划线数据。Cookie仅保存在本地服务器。
                    </div>
                    <div class="form-group">
                        <label>微信读书 Cookie</label>
                        <textarea class="cookie-textarea" id="loginCookieInput" placeholder="粘贴从微信读书网页版获取的 Cookie 字符串"></textarea>
                    </div>
                    <button class="btn-primary" onclick="loginByCookie()">导入并登录</button>
                    <div style="margin-top:0.75rem; text-align:center;">
                        <a style="font-size:0.8rem; color:var(--accent); cursor:pointer;" onclick="showCookieGuide()">不知道怎么获取Cookie？</a>
                    </div>
                </div>
            </div>

            <!-- 账号密码登录 -->'''

    content = content.replace(match.group(), wechat_login_html)

# ========== 3. 在 app 末尾添加模态框 HTML ==========
old_body_end = '    <!-- 加载遮罩 -->'

modal_html = '''    <!-- Cookie 导入模态框 -->
    <div class="modal-mask" id="cookieModal">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title" id="cookieModalTitle">连接微信读书</div>
                <span class="modal-close" onclick="closeCookieModal()">×</span>
            </div>
            <div class="modal-body">
                <div class="guide-steps" id="cookieGuide">
                </div>
                <div class="form-group">
                    <label>Cookie 字符串</label>
                    <textarea class="cookie-textarea" id="cookieInput" placeholder="在此粘贴从浏览器复制的完整 Cookie"></textarea>
                </div>
                <div class="tip-box">
                    🔒 Cookie 仅用于同步您的阅读数据，保存在您的本地服务器中，不会上传到任何第三方。
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeCookieModal()">取消</button>
                <button class="btn-primary" onclick="submitCookie()" id="submitCookieBtn">开始同步</button>
            </div>
        </div>
    </div>

    <!-- 加载遮罩 -->'''

content = content.replace(old_body_end, modal_html)

# ========== 4. 更新 JavaScript 登录逻辑 ==========
# 找到 switchLoginTab 函数并替换
old_switch = '''        function switchLoginTab(type) {
            document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('qrLogin').style.display = type === 'qr' ? 'block' : 'none';
            document.getElementById('pwdLogin').style.display = type === 'pwd' ? 'block' : 'none';
            document.getElementById('registerPanel').style.display = 'none';

            if (type === 'qr') {
                createQRCode();
            }
        }'''

new_switch = '''        function switchLoginTab(type) {
            document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
            event && event.target && event.target.classList.add('active');
            const wechatLogin = document.getElementById('wechatLogin');
            const pwdLogin = document.getElementById('pwdLogin');
            const registerPanel = document.getElementById('registerPanel');

            if (wechatLogin) wechatLogin.style.display = type === 'wechat' ? 'block' : 'none';
            if (pwdLogin) pwdLogin.style.display = type === 'pwd' ? 'block' : 'none';
            if (registerPanel) registerPanel.style.display = 'none';

            if (type === 'wechat') {
                initWechatLogin();
            }
        }

        function switchWechatLogin(method) {
            document.querySelectorAll('.login-method-tab').forEach(t => t.classList.remove('active'));
            event && event.target && event.target.closest('.login-method-tab') && event.target.closest('.login-method-tab').classList.add('active');
            document.getElementById('wechatScanLogin').style.display = method === 'scan' ? 'block' : 'none';
            document.getElementById('wechatCookieLogin').style.display = method === 'cookie' ? 'block' : 'none';

            if (method === 'scan') {
                initWechatLogin();
            }
        }

        async function initWechatLogin() {
            const res = await api('/wechat/qrcode');
            if (res.code === 0 && res.data) {
                if (res.data.available) {
                    loadWechatQrImage(res.data.qr_url);
                } else {
                    showWechatLoginUnavailable();
                }
            }
        }

        function loadWechatQrImage(qrUrl) {
            const box = document.getElementById('wechatQrBox');
            if (box) {
                box.innerHTML = `<img src="${qrUrl}" alt="微信扫码登录" style="width:170px;height:170px;">`;
            }
            // 打开新窗口方式的备用方案
        }

        function showWechatLoginUnavailable() {
            const box = document.getElementById('wechatQrBox');
            if (box) {
                box.innerHTML = `
                    <div style="color:#999; text-align:center; padding:1rem;">
                        <div style="font-size:2rem; margin-bottom:0.5rem;">⚠️</div>
                        <div style="font-size:0.85rem; line-height:1.6;">
                            微信开放平台未配置<br>
                            <span style="font-size:0.75rem; color:#bbb;">请使用 Cookie 导入方式</span>
                        </div>
                    </div>
                `;
            }
            const tip = document.getElementById('wechatQrTip');
            if (tip) tip.textContent = '建议使用 Cookie 导入方式登录';
            const status = document.getElementById('wechatQrStatus');
            if (status) {
                status.className = 'qr-status scanned';
                status.textContent = '点击上方「Cookie导入」';
            }
        }

        function refreshWechatQR() {
            initWechatLogin();
        }

        async function loginByCookie() {
            const cookie = document.getElementById('loginCookieInput').value.trim();
            if (!cookie) {
                showToast('请输入 Cookie');
                return;
            }

            showLoading('验证 Cookie 中...');

            // 先注册一个临时账号或登录
            try {
                // 先检查 Cookie 是否有效
                const checkRes = await api('/platform/cookie/check', {
                    method: 'POST',
                    body: { platform: 'wechat', cookie: cookie }
                });

                if (checkRes.code !== 0 || !checkRes.data || !checkRes.data.valid) {
                    hideLoading();
                    showToast('Cookie 无效，请重新获取');
                    return;
                }

                // 创建用户（用 cookie 哈希作为标识）
                const uid = 'wx_' + (checkRes.data.user_info && checkRes.data.user_info.user_id ? checkRes.data.user_info.user_id : Math.random().toString(36).slice(2, 10));
                const regRes = await api('/auth/register', {
                    method: 'POST',
                    body: { username: uid, password: 'shushu123' }
                });

                let token, user;
                if (regRes.code === 0 && regRes.data) {
                    token = regRes.data.token;
                    user = regRes.data.user;
                } else {
                    // 已注册，登录
                    const loginRes = await api('/auth/login', {
                        method: 'POST',
                        body: { username: uid, password: 'shushu123' }
                    });
                    if (loginRes.code === 0 && loginRes.data) {
                        token = loginRes.data.token;
                        user = loginRes.data.user;
                    }
                }

                if (token) {
                    setToken(token);
                    currentUser = user;

                    // 同步数据
                    hideLoading();
                    showLoading('同步微信读书数据...');

                    const syncRes = await fetch(API_BASE + '/platform/sync/wechat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ cookie: cookie })
                    });
                    const syncData = await syncRes.json();

                    hideLoading();

                    if (syncData.code === 0) {
                        showToast('登录并同步成功！');
                        setTimeout(() => enterApp(), 800);
                    } else {
                        showToast('登录成功，同步失败：' + (syncData.msg || ''));
                        setTimeout(() => enterApp(), 1000);
                    }
                } else {
                    hideLoading();
                    showToast('登录失败');
                }
            } catch (e) {
                hideLoading();
                showToast('登录失败：' + e.message);
            }
        }

        let currentConnectPlatform = 'wechat';

        function openCookieModal(platform) {
            currentConnectPlatform = platform || 'wechat';
            const modal = document.getElementById('cookieModal');
            const title = document.getElementById('cookieModalTitle');
            const names = { wechat: '微信读书', fanqie: '番茄读书', kindle: 'Kindle', douban: '豆瓣阅读' };
            title.textContent = '连接' + (names[platform] || platform);

            // 加载教程
            loadCookieGuide(platform);

            document.getElementById('cookieInput').value = '';
            modal.classList.add('active');
        }

        function closeCookieModal() {
            document.getElementById('cookieModal').classList.remove('active');
        }

        async function loadCookieGuide(platform) {
            const guideEl = document.getElementById('cookieGuide');
            const res = await api(`/platform/cookie/guide/${platform}`);
            if (res.code === 0 && res.data) {
                const guide = res.data;
                let html = `<div style="font-weight:600; margin-bottom:0.75rem;">📖 ${guide.title}</div>`;
                guide.steps.forEach(step => {
                    html += `
                        <div class="guide-step">
                            <div class="step-num">${step.step}</div>
                            <div class="step-content">
                                <div class="step-title">${step.title}</div>
                                <div class="step-desc">${step.desc}</div>
                            </div>
                        </div>
                    `;
                });
                if (guide.tips && guide.tips.length) {
                    html += '<div style="margin-top:0.75rem; font-size:0.75rem; color:#999; line-height:1.6;">';
                    guide.tips.forEach(tip => {
                        html += `• ${tip}<br>`;
                    });
                    html += '</div>';
                }
                guideEl.innerHTML = html;
            }
        }

        async function submitCookie() {
            const cookie = document.getElementById('cookieInput').value.trim();
            if (!cookie) {
                showToast('请输入 Cookie');
                return;
            }

            const btn = document.getElementById('submitCookieBtn');
            btn.disabled = true;
            btn.textContent = '同步中...';

            showLoading('正在同步数据...');

            try {
                const res = await api(`/platform/sync/${currentConnectPlatform}`, {
                    method: 'POST',
                    body: { cookie: cookie }
                });

                hideLoading();
                btn.disabled = false;
                btn.textContent = '开始同步';

                if (res.code === 0) {
                    closeCookieModal();
                    showToast('同步成功！');
                    loadPlatforms();
                    loadBooks();
                    loadHighlights();
                    updateStats();
                } else {
                    showToast(res.msg || '同步失败');
                }
            } catch (e) {
                hideLoading();
                btn.disabled = false;
                btn.textContent = '开始同步';
                showToast('同步失败：' + e.message);
            }
        }

        function showCookieGuide() {
            openCookieModal('wechat');
        }'''

content = content.replace(old_switch, new_switch)

# ========== 5. 更新 connectPlatform 函数 ==========
old_connect = '''        async function connectPlatform(platform) {
            if (!confirm(`确定要连接${platform === 'wechat' ? '微信读书' : platform === 'fanqie' ? '番茄读书' : platform === 'kindle' ? 'Kindle' : '豆瓣阅读'}吗？`)) {
                return;
            }
            showLoading('连接中...');
            const res = await api(`/platform/sync/${platform}`, { method: 'POST' });
            hideLoading();

            if (res.code === 0) {
                showToast('连接成功！');
                loadPlatforms();
                loadBooks();
                loadHighlights();
                updateStats();
            } else {
                showToast(res.msg || '连接失败');
            }
        }'''

new_connect = '''        async function connectPlatform(platform) {
            if (platform === 'wechat') {
                openCookieModal('wechat');
            } else {
                if (!confirm(`确定要连接${platform === 'fanqie' ? '番茄读书' : platform === 'kindle' ? 'Kindle' : '豆瓣阅读'}吗？（演示数据）`)) {
                    return;
                }
                showLoading('连接中...');
                const res = await api(`/platform/sync/${platform}`, { method: 'POST' });
                hideLoading();

                if (res.code === 0) {
                    showToast('连接成功！');
                    loadPlatforms();
                    loadBooks();
                    loadHighlights();
                    updateStats();
                } else {
                    showToast(res.msg || '连接失败');
                }
            }
        }'''

content = content.replace(old_connect, new_connect)

# ========== 6. 修复 showRegister 和 showLogin ==========
old_show_register = '''        function showRegister() {
            document.getElementById('pwdLogin').style.display = 'none';
            document.getElementById('qrLogin').style.display = 'none';
            document.getElementById('registerPanel').style.display = 'block';
        }'''

new_show_register = '''        function showRegister() {
            document.getElementById('pwdLogin').style.display = 'none';
            const wl = document.getElementById('wechatLogin');
            if (wl) wl.style.display = 'none';
            document.getElementById('registerPanel').style.display = 'block';
        }'''

content = content.replace(old_show_register, new_show_register)

old_show_login = '''        function showLogin() {
            document.getElementById('registerPanel').style.display = 'none';
            document.getElementById('pwdLogin').style.display = 'block';
            document.querySelectorAll('.login-tab')[1].classList.add('active');
            document.querySelectorAll('.login-tab')[0].classList.remove('active');
        }'''

new_show_login = '''        function showLogin() {
            document.getElementById('registerPanel').style.display = 'none';
            document.getElementById('pwdLogin').style.display = 'block';
            const tabs = document.querySelectorAll('.login-tab');
            if (tabs.length >= 2) {
                tabs[1].classList.add('active');
                tabs[0].classList.remove('active');
            }
        }'''

content = content.replace(old_show_login, new_show_login)

# 保存
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("app.html 更新完成！")
