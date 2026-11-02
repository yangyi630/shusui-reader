"""
更新前端文档分析展示
添加：全文摘要、主题分类、关键词、学习指南、思维导图等
"""

import re

file_path = r'c:\Users\92783\Desktop\代码\书髓\app.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 添加更多 CSS 样式 ==========
more_css = '''
        .study-overview {
            background: linear-gradient(135deg, #faf8f5, #f5f0e8);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .study-overview-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            color: var(--text);
        }
        .study-overview-text {
            font-size: 0.9rem;
            line-height: 1.8;
            color: var(--text-2);
        }

        .theme-badge {
            display: inline-block;
            padding: 0.35rem 0.875rem;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: white;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 0.5rem;
        }

        .keyword-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }
        .keyword-tag {
            padding: 0.3rem 0.75rem;
            background: rgba(78,205,196,0.1);
            color: var(--accent-2);
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .keyword-tag:hover {
            background: rgba(78,205,196,0.2);
            transform: scale(1.05);
        }
        .keyword-tag.high {
            font-size: 1rem;
            font-weight: 600;
        }
        .keyword-tag.medium {
            font-size: 0.85rem;
        }

        .study-guide-section {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .study-guide-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .study-guide-title::before {
            content: '';
            width: 4px;
            height: 18px;
            background: linear-gradient(180deg, var(--accent), var(--accent-2));
            border-radius: 2px;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 0.75rem;
        }
        .info-item {
            text-align: center;
            padding: 0.75rem;
            background: #faf8f5;
            border-radius: 8px;
        }
        .info-num {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent);
        }
        .info-label {
            font-size: 0.75rem;
            color: var(--text-2);
            margin-top: 0.25rem;
        }

        .question-item {
            padding: 0.75rem 1rem;
            background: #faf8f5;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .question-item:hover {
            background: #f0ebe0;
        }
        .question-text {
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }
        .question-hint {
            font-size: 0.8rem;
            color: var(--accent-2);
        }
        .question-answer {
            display: none;
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px dashed #ddd;
            font-size: 0.85rem;
            color: var(--text-2);
            line-height: 1.6;
        }
        .question-item.show .question-answer {
            display: block;
        }

        .mindmap-container {
            padding: 0.5rem 0;
        }
        .mindmap-chapter {
            margin-bottom: 0.75rem;
            padding-left: 1rem;
            border-left: 3px solid var(--accent);
        }
        .mindmap-chapter-title {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
            color: var(--text);
        }
        .mindmap-points {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .mindmap-points li {
            font-size: 0.8rem;
            color: var(--text-2);
            padding: 0.15rem 0;
            padding-left: 1rem;
            position: relative;
        }
        .mindmap-points li::before {
            content: '•';
            position: absolute;
            left: 0;
            color: var(--accent);
        }

        .chapter-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.875rem 1rem;
            background: white;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }
        .chapter-item:hover {
            background: #faf8f5;
            border-left-color: var(--accent);
            transform: translateX(2px);
        }
        .chapter-item.active {
            background: rgba(78,205,196,0.1);
            border-left-color: var(--accent-2);
        }
        .chapter-num {
            display: inline-block;
            font-size: 0.75rem;
            color: var(--accent-2);
            background: rgba(78,205,196,0.1);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            margin-right: 0.5rem;
        }
        .chapter-count {
            font-size: 0.75rem;
            color: var(--text-3);
            background: #f0ebe0;
            padding: 0.2rem 0.5rem;
            border-radius: 10px;
        }
'''

content = content.replace('    </style>', more_css + '    </style>')

# ========== 2. 更新学习详情页 HTML ==========
old_study_detail = '''            <!-- 学习详情页 -->
            <div class="tab-page" id="tab-study-detail">
                <div class="chapter-back" onclick="backToStudyList()">← 返回文档列表</div>
                <div style="display:grid; grid-template-columns: 1fr; gap: 1rem;">
                    <div class="chapter-list" id="chapterList"></div>
                </div>
            </div>'''

new_study_detail = '''            <!-- 学习详情页 -->
            <div class="tab-page" id="tab-study-detail">
                <div class="chapter-back" onclick="backToStudyList()">← 返回文档列表</div>

                <!-- 全文概览 -->
                <div class="study-overview" id="studyOverview">
                    <div class="study-overview-title">📝 全文摘要</div>
                    <div class="study-overview-text" id="docSummary">分析中...</div>
                </div>

                <!-- 主题分类 + 关键词 -->
                <div class="study-guide-section">
                    <div class="study-guide-title">🏷️ 主题分类</div>
                    <div id="docTheme">
                        <span class="theme-badge">综合类</span>
                    </div>
                    <div class="study-guide-title" style="margin-top:1rem;">🔑 核心关键词</div>
                    <div class="keyword-cloud" id="docKeywords"></div>
                </div>

                <!-- 文档信息 -->
                <div class="study-guide-section">
                    <div class="study-guide-title">📊 文档概况</div>
                    <div class="info-grid" id="docInfoGrid"></div>
                </div>

                <!-- 章节列表 -->
                <div class="study-guide-section">
                    <div class="study-guide-title">📚 章节目录</div>
                    <div class="chapter-list" id="chapterList"></div>
                </div>

                <!-- 学习指南 -->
                <div class="study-guide-section" id="studyGuideSection">
                    <div class="study-guide-title">🎯 学习指南</div>
                    <div id="studyGuideContent"></div>
                </div>

                <!-- 复习问题 -->
                <div class="study-guide-section" id="reviewSection">
                    <div class="study-guide-title">❓ 复习要点</div>
                    <div id="reviewQuestions"></div>
                </div>

                <!-- 思维导图 -->
                <div class="study-guide-section" id="mindmapSection">
                    <div class="study-guide-title">🧠 知识脉络</div>
                    <div class="mindmap-container" id="mindMap"></div>
                </div>
            </div>'''

content = content.replace(old_study_detail, new_study_detail)

# ========== 3. 更新 renderChapterList 和相关函数 ==========
old_render_func = '''        function renderChapterList() {
            const list = document.getElementById('chapterList');
            if (!currentDoc || !currentDoc.chapters) return;

            list.innerHTML = currentDoc.chapters.map((ch, i) => `
                <div class="chapter-item ${i === currentChapterIndex ? 'active' : ''}" onclick="openChapter(${i})">
                    <span>
                        <span class="chapter-num">第${i+1}章</span>
                        ${ch.title || '未命名章节'}
                    </span>
                    <span class="chapter-count">${(ch.key_points || []).length}</span>
                </div>
            `).join('');
        }'''

new_render_func = '''        function renderDocDetail() {
            if (!currentDoc) return;

            // 全文摘要
            document.getElementById('docSummary').textContent = currentDoc.summary || '暂无摘要';

            // 主题
            const themeEl = document.getElementById('docTheme');
            if (currentDoc.theme && currentDoc.theme.main_theme) {
                themeEl.innerHTML = `<span class="theme-badge">${currentDoc.theme.main_theme}</span>`;
            }

            // 关键词
            const kwEl = document.getElementById('docKeywords');
            if (currentDoc.keywords && currentDoc.keywords.length) {
                kwEl.innerHTML = currentDoc.keywords.map((k, i) => {
                    const sizeClass = i < 5 ? 'high' : (i < 10 ? 'medium' : '');
                    return `<span class="keyword-tag ${sizeClass}">${k.word}</span>`;
                }).join('');
            }

            // 文档信息
            const infoGrid = document.getElementById('docInfoGrid');
            const guide = currentDoc.study_guide || {};
            const infoItems = [
                { num: currentDoc.total_chars || 0, label: '总字数' },
                { num: (currentDoc.chapters || []).length, label: '章节数' },
                { num: guide.estimated_read_time || '?', label: '预计阅读(分钟)' },
                { num: guide.difficulty_level || '中等', label: '难度等级' },
            ];
            infoGrid.innerHTML = infoItems.map(item => `
                <div class="info-item">
                    <div class="info-num">${item.num}</div>
                    <div class="info-label">${item.label}</div>
                </div>
            `).join('');

            // 章节列表
            renderChapterList();

            // 学习指南
            const guideEl = document.getElementById('studyGuideContent');
            if (guide.core_points && guide.core_points.length) {
                guideEl.innerHTML = `
                    <div style="font-size:0.85rem; color:var(--text-2); margin-bottom:0.5rem;">
                        从全文提取了 ${guide.core_points.length} 个核心要点，建议优先掌握：
                    </div>
                    <div style="max-height:200px; overflow-y:auto;">
                        ${guide.core_points.slice(0, 5).map(p => `
                            <div style="padding:0.5rem 0; border-bottom:1px solid #f0ebe0; font-size:0.85rem; line-height:1.6;">
                                <span style="color:var(--accent-2); font-weight:500;">[${p.chapter}]</span>
                                ${p.content}
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            // 复习问题
            const reviewEl = document.getElementById('reviewQuestions');
            if (guide.review_questions && guide.review_questions.length) {
                reviewEl.innerHTML = guide.review_questions.map((q, i) => `
                    <div class="question-item" onclick="this.classList.toggle('show')">
                        <div class="question-text">${i + 1}. ${q.question}</div>
                        <div class="question-hint">💡 提示：${q.hint}（点击查看答案）</div>
                        <div class="question-answer">✅ ${q.answer}</div>
                    </div>
                `).join('');
            }

            // 思维导图
            const mindEl = document.getElementById('mindMap');
            if (guide.mind_map_outline && guide.mind_map_outline.length) {
                mindEl.innerHTML = guide.mind_map_outline.map(ch => `
                    <div class="mindmap-chapter">
                        <div class="mindmap-chapter-title">${ch.chapter}</div>
                        <ul class="mindmap-points">
                            ${ch.sub_points.map(p => `<li>${p}</li>`).join('')}
                        </ul>
                    </div>
                `).join('');
            }
        }

        function renderChapterList() {
            const list = document.getElementById('chapterList');
            if (!currentDoc || !currentDoc.chapters) return;

            list.innerHTML = currentDoc.chapters.map((ch, i) => `
                <div class="chapter-item ${i === currentChapterIndex ? 'active' : ''}" onclick="openChapter(${i})">
                    <span>
                        <span class="chapter-num">第${i+1}章</span>
                        ${ch.title || '未命名章节'}
                    </span>
                    <span class="chapter-count">${(ch.key_points || []).length}要点</span>
                </div>
            `).join('');
        }'''

content = content.replace(old_render_func, new_render_func)

# ========== 4. 更新上传成功后的调用 ==========
old_success = '''                    showLoading(false);
                    showToast('分析完成！');
                    currentDoc = res.data;
                    switchTab('study-detail');
                    renderChapterList();'''

new_success = '''                    showLoading(false);
                    showToast('分析完成！');
                    currentDoc = res.data;
                    switchTab('study-detail');
                    renderDocDetail();'''

content = content.replace(old_success, new_success)

# 保存
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("前端文档分析展示升级完成！")
print("- 新增全文摘要展示")
print("- 新增主题分类识别")
print("- 新增核心关键词云")
print("- 新增文档信息统计")
print("- 新增学习指南模块")
print("- 新增复习要点（可展开答案）")
print("- 新增知识脉络思维导图")
