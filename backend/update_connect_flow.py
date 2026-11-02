"""
重构连接平台的交互流程：
- 点击平台 → 弹出连接向导
- 第一步：去官网扫码登录（新窗口打开）
- 第二步：复制 Cookie 回来粘贴
- 第三步：开始同步数据
"""

import re

file_path = r'c:\Users\92783\Desktop\代码\书髓\app.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 更新连接平台的模态框，改为向导式 ==========
old_modal = '''    <!-- Cookie 导入模态框 -->
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
    </div>'''

new_modal = '''    <!-- 连接平台模态框 -->
    <div class="modal-mask" id="connectModal">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title" id="connectModalTitle">连接平台</div>
                <span class="modal-close" onclick="closeConnectModal()">×</span>
            </div>
            <div class="modal-body" id="connectModalBody">
            </div>
        </div>
    </div>'''

content = content.replace(old_modal, new_modal)

# ========== 2. 增加更多 CSS 样式 ==========
more_css = '''
        .connect-wizard {
            text-align: center;
        }
        .wizard-steps {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        .wizard-step-dot {
            width: 32px; height: 32px;
            border-radius: 50%;
            background: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            font-weight: 600;
            color: #999;
            transition: all 0.3s;
        }
        .wizard-step-dot.active {
            background: var(--accent);
            color: white;
        }
        .wizard-step-dot.done {
            background: #27ae60;
            color: white;
        }
        .wizard-step-line {
            width: 30px;
            height: 2px;
            background: #eee;
            align-self: center;
        }
        .wizard-step-line.done { background: #27ae60; }

        .wizard-content {
            text-align: left;
            min-height: 280px;
        }
        .wizard-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .wizard-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        .wizard-desc {
            color: var(--text-2);
            font-size: 0.9rem;
            line-height: 1.7;
            margin-bottom: 1.25rem;
            text-align: center;
        }
        .wizard-action {
            text-align: center;
        }
        .btn-open-site {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.875rem 2rem;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: white;
            border: none;
            border-radius: 30px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
        }
        .btn-open-site:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(200,149,108,0.3); }

        .cookie-guide-box {
            background: #faf8f5;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .cookie-guide-title {
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .guide-list {
            list-style: none;
            padding: 0;
        }
        .guide-list li {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            font-size: 0.85rem;
            line-height: 1.6;
        }
        .guide-list li:last-child { margin-bottom: 0; }
        .guide-num {
            flex-shrink: 0;
            width: 22px; height: 22px;
            background: var(--accent);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .guide-text { color: var(--text-2); }
        .guide-text strong { color: var(--text); font-weight: 600; }

        .copy-hint {
            background: rgba(78,205,196,0.1);
            border-radius: 6px;
            padding: 0.75rem 1rem;
            font-size: 0.8rem;
            color: var(--text-2);
            margin-bottom: 0.75rem;
            line-height: 1.6;
        }
        .copy-hint code {
            background: rgba(0,0,0,0.05);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: monospace;
        }

        .wizard-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }
        .wizard-footer .btn-back {
            padding: 0.625rem 1.25rem;
            background: transparent;
            border: 2px solid #eee;
            border-radius: 8px;
            font-size: 0.9rem;
            cursor: pointer;
            color: var(--text-2);
            transition: all 0.3s;
        }
        .wizard-footer .btn-back:hover { border-color: #ddd; color: var(--text); }
        .wizard-footer .btn-next {
            padding: 0.625rem 1.5rem;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .wizard-footer .btn-next:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(200,149,108,0.3); }
        .wizard-footer .btn-next:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        .syncing-box {
            text-align: center;
            padding: 2rem 0;
        }
        .syncing-spinner {
            width: 50px; height: 50px;
            border: 4px solid #eee;
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .syncing-title { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; }
        .syncing-desc { font-size: 0.85rem; color: var(--text-2); }

        .success-box {
            text-align: center;
            padding: 1rem 0;
        }
        .success-icon { font-size: 4rem; margin-bottom: 1rem; }
        .success-title { font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem; color: #27ae60; }
        .success-desc { font-size: 0.9rem; color: var(--text-2); margin-bottom: 1.5rem; }
        .success-stats {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-bottom: 1.5rem;
        }
        .success-stat {
            text-align: center;
            padding: 0.75rem 1rem;
            background: #faf8f5;
            border-radius: 8px;
            min-width: 80px;
        }
        .success-stat-num {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent);
        }
        .success-stat-label { font-size: 0.75rem; color: var(--text-2); }
'''

# 在 </style> 之前插入
content = content.replace('    </style>', more_css + '    </style>')

# ========== 3. 替换 JavaScript 中的相关函数 ==========

# 替换 openCookieModal 等函数为新的连接向导
old_funcs_pattern = r'''        let currentConnectPlatform = 'wechat';

        function openCookieModal\(platform\) \{
.*?
        function showCookieGuide\(\) \{
            openCookieModal\('wechat'\);
        \}'''

new_funcs = '''        let currentConnectPlatform = 'wechat';
        let connectStep = 1;
        let connectPlatformConfig = {
            wechat: {
                name: '微信读书',
                icon: '📱',
                color: '#4ecdc4',
                url: 'https://weread.qq.com',
                hasCookieImport: true,
                cookieKey: 'wr_vid',
                steps: [
                    {
                        title: '前往微信读书官网',
                        desc: '点击下方按钮，在新窗口打开微信读书网页版',
                        action: 'open_site'
                    },
                    {
                        title: '扫码登录并复制 Cookie',
                        desc: '登录后按 F12 打开开发者工具，复制 Cookie',
                        action: 'cookie_input'
                    },
                    {
                        title: '同步数据',
                        desc: '正在同步您的书架和划线数据...',
                        action: 'syncing'
                    }
                ]
            },
            fanqie: {
                name: '番茄读书',
                icon: '🍅',
                color: '#ff6b6b',
                url: 'https://fanqienovel.com',
                hasCookieImport: true,
                steps: [
                    { title: '功能开发中', desc: '番茄读书数据导入功能正在开发中...', action: 'coming' }
                ]
            },
            kindle: {
                name: 'Kindle',
                icon: '📚',
                color: '#f0c040',
                url: 'https://read.amazon.com',
                hasCookieImport: false,
                steps: [
                    { title: '功能开发中', desc: 'Kindle 数据导入功能正在开发中...', action: 'coming' }
                ]
            },
            douban: {
                name: '豆瓣阅读',
                icon: '📖',
                color: '#4a9c5d',
                url: 'https://read.douban.com',
                hasCookieImport: false,
                steps: [
                    { title: '功能开发中', desc: '豆瓣阅读数据导入功能正在开发中...', action: 'coming' }
                ]
            }
        };

        function openConnectModal(platform) {
            currentConnectPlatform = platform;
            connectStep = 1;
            const config = connectPlatformConfig[platform];
            if (!config) return;

            const modal = document.getElementById('connectModal');
            const title = document.getElementById('connectModalTitle');
            title.textContent = '连接' + config.name;

            renderConnectStep();
            modal.classList.add('active');
        }

        function closeConnectModal() {
            document.getElementById('connectModal').classList.remove('active');
        }

        function renderConnectStep() {
            const config = connectPlatformConfig[currentConnectPlatform];
            const body = document.getElementById('connectModalBody');
            const totalSteps = config.steps.length;

            let html = '<div class="connect-wizard">';

            // 步骤指示器
            html += '<div class="wizard-steps">';
            for (let i = 0; i < totalSteps; i++) {
                const stepNum = i + 1;
                let statusClass = '';
                if (stepNum < connectStep) statusClass = 'done';
                else if (stepNum === connectStep) statusClass = 'active';
                html += `<div class="wizard-step-dot ${statusClass}">${stepNum < connectStep ? '✓' : stepNum}</div>`;
                if (i < totalSteps - 1) {
                    html += `<div class="wizard-step-line ${stepNum < connectStep ? 'done' : ''}"></div>`;
                }
            }
            html += '</div>';

            // 步骤内容
            const step = config.steps[connectStep - 1];
            html += '<div class="wizard-content">';

            if (step.action === 'open_site') {
                html += `
                    <div class="wizard-icon">${config.icon}</div>
                    <div class="wizard-title">${step.title}</div>
                    <div class="wizard-desc">${step.desc}<br>在官网完成扫码登录后，回到这里继续下一步</div>
                    <div class="wizard-action">
                        <a href="${config.url}" target="_blank" class="btn-open-site" onclick="setTimeout(() => { connectStep = 2; renderConnectStep(); }, 500);">
                            🔗 打开${config.name}官网
                        </a>
                    </div>
                    <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid #eee;">
                        <div style="font-size:0.85rem; color:var(--text-2); margin-bottom:0.75rem;">登录成功后？</div>
                        <button class="btn-primary" style="width:100%;" onclick="connectStep = 2; renderConnectStep();">
                            已完成登录，下一步 →
                        </button>
                    </div>
                `;
            } else if (step.action === 'cookie_input') {
                html += `
                    <div class="wizard-icon">🍪</div>
                    <div class="wizard-title">复制 Cookie 并粘贴</div>
                    <div class="wizard-desc">在已登录的网页中，按 F12 打开开发者工具，找到 Cookie 并复制</div>

                    <div class="cookie-guide-box">
                        <div class="cookie-guide-title">📖 获取 Cookie 步骤</div>
                        <ul class="guide-list">
                            <li>
                                <span class="guide-num">1</span>
                                <span class="guide-text">在${config.name}页面按 <strong>F12</strong> 打开开发者工具</span>
                            </li>
                            <li>
                                <span class="guide-num">2</span>
                                <span class="guide-text">切换到 <strong>Network（网络）</strong> 标签，刷新一下页面</span>
                            </li>
                            <li>
                                <span class="guide-num">3</span>
                                <span class="guide-text">点击任意一个请求，在右侧 <strong>Headers</strong> 中找到 <strong>Cookie</strong> 字段</span>
                            </li>
                            <li>
                                <span class="guide-num">4</span>
                                <span class="guide-text">右键 Cookie 内容 → <strong>复制值</strong>，粘贴到下方</span>
                            </li>
                        </ul>
                    </div>

                    <div class="form-group">
                        <label style="font-weight:600;">Cookie 字符串</label>
                        <textarea class="cookie-textarea" id="connectCookieInput" placeholder="在这里粘贴从浏览器复制的完整 Cookie..." style="min-height: 100px;"></textarea>
                    </div>

                    <div class="tip-box">
                        🔒 Cookie 仅用于同步您的阅读数据，全部保存在您的本地电脑中，不会上传到任何第三方服务器。
                    </div>
                `;

                html += '</div>'; // end wizard-content

                html += `
                    <div class="wizard-footer">
                        <button class="btn-back" onclick="connectStep = 1; renderConnectStep();">← 上一步</button>
                        <button class="btn-next" id="connectNextBtn" onclick="startConnectSync()">开始同步 →</button>
                    </div>
                `;
            } else if (step.action === 'syncing') {
                html += `
                    <div class="syncing-box">
                        <div class="syncing-spinner"></div>
                        <div class="syncing-title">正在同步数据...</div>
                        <div class="syncing-desc" id="syncingDesc">正在连接${config.name}...</div>
                    </div>
                `;
            } else if (step.action === 'success') {
                html += `
                    <div class="success-box">
                        <div class="success-icon">🎉</div>
                        <div class="success-title">同步成功！</div>
                        <div class="success-desc">已成功获取您的${config.name}数据</div>
                        <div class="success-stats" id="successStats">
                        </div>
                        <button class="btn-primary" style="padding:0.75rem 2rem;" onclick="closeConnectModal();">
                            完成
                        </button>
                    </div>
                `;
            } else if (step.action === 'coming') {
                html += `
                    <div class="success-box">
                        <div class="success-icon">🚧</div>
                        <div class="wizard-title" style="color:var(--accent-2);">${step.title}</div>
                        <div class="wizard-desc">${step.desc}<br>敬请期待！</div>
                        <button class="btn-secondary" style="margin-top:1rem;" onclick="closeConnectModal();">
                            知道了
                        </button>
                    </div>
                `;
            }

            html += '</div>'; // end wizard-content
            html += '</div>'; // end connect-wizard

            body.innerHTML = html;
        }

        async function startConnectSync() {
            const cookie = document.getElementById('connectCookieInput').value.trim();
            if (!cookie) {
                showToast('请粘贴 Cookie 内容');
                return;
            }

            const btn = document.getElementById('connectNextBtn');
            if (btn) {
                btn.disabled = true;
                btn.textContent = '同步中...';
            }

            connectStep = 3;
            renderConnectStep();

            try {
                const res = await api(`/platform/sync/${currentConnectPlatform}`, {
                    method: 'POST',
                    body: { cookie: cookie }
                });

                if (res.code === 0 && res.data && res.data.success) {
                    // 显示成功
                    connectStep = 4;
                    const config = connectPlatformConfig[currentConnectPlatform];
                    config.steps = [
                        { title: '前往官网', desc: '', action: 'open_site' },
                        { title: '复制Cookie', desc: '', action: 'cookie_input' },
                        { title: '同步数据', desc: '', action: 'syncing' },
                        { title: '完成', desc: '', action: 'success' }
                    ];
                    renderConnectStep();

                    // 填充统计数据
                    setTimeout(() => {
                        const statsEl = document.getElementById('successStats');
                        if (statsEl) {
                            statsEl.innerHTML = `
                                <div class="success-stat">
                                    <div class="success-stat-num">${res.data.book_count || 0}</div>
                                    <div class="success-stat-label">本书籍</div>
                                </div>
                                <div class="success-stat">
                                    <div class="success-stat-num">${res.data.highlight_count || 0}</div>
                                    <div class="success-stat-label">条划线</div>
                                </div>
                            `;
                        }
                    }, 100);

                    // 刷新数据
                    loadPlatforms();
                    loadBooks();
                    loadHighlights();
                    updateStats();
                } else {
                    showToast(res.msg || '同步失败');
                    connectStep = 2;
                    renderConnectStep();
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = '开始同步 →';
                    }
                }
            } catch (e) {
                showToast('同步失败：' + e.message);
                connectStep = 2;
                renderConnectStep();
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '开始同步 →';
                }
            }
        }

        function openCookieModal(platform) {
            openConnectModal(platform);
        }

        function closeCookieModal() {
            closeConnectModal();
        }

        function showCookieGuide() {
            openConnectModal('wechat');
        }'''

# 用正则替换
content = re.sub(
    r"        let currentConnectPlatform = 'wechat';\n\n        function openCookieModal\(platform\) \{.*?function showCookieGuide\(\) \{\s*openCookieModal\('wechat'\);\s*\}",
    new_funcs,
    content,
    flags=re.DOTALL
)

# ========== 4. 更新 connectPlatform 函数 ==========
old_connect = '''        async function connectPlatform(platform) {
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

new_connect = '''        function connectPlatform(platform) {
            openConnectModal(platform);
        }'''

content = content.replace(old_connect, new_connect)

# 保存
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("前端连接流程重构完成！")
print("- 向导式三步流程：打开官网 → 复制Cookie → 同步数据")
print("- 自动打开新窗口到对应平台官网")
print("- 详细的 Cookie 获取教程")
print("- 同步进度和成功状态展示")
