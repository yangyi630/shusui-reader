"""
智能文本分析模块
基于 NLP 算法对文本进行深度理解和总结，包括：
- 章节自动识别
- 关键词提取（TF-IDF）
- 关键句提取（TextRank 简化版）
- 自动摘要生成
- 主题段落归纳
- 学习要点提炼
"""

import re
import math
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class TextAnalyzer:
    """智能文本分析器"""

    # 中文停用词
    STOP_WORDS = set('''
    的 了 和 是 就 都 而 及 与 或 一 个 上 下 不 也 很 到 说 要 把 被 给 让 从 向 等
    这 那 你 我 他 她 它 他 们 她 们 它 们 我 们 你 们 自 己 这 样 那 样 这 里 那 里
    在 有 在 于 关 于 对 于 为 了 因 为 所 以 如 果 虽 然 但 是 然 而 不 过 可 是
    人 时 候 地 方 时 间 问 题 方 法 问 题 东 西 事 情 原 因 结 果 过 程 内 容 形 式
    可 以 应 该 能 够 会 能 可 也 就 是 说 可 是 但 是 而 且 并 且 或 者 还 有
    非 常 十 分 特 别 更 加 越 来 越 比 较 稍 微 有 点 比 较 最 更 太 好 坏
    第 第 一 第 二 第 三 其 中 其 它 其 实 事 实 上 实 际 上 基 本 上 大 部 分
    这 个 那 个 哪 个 某 个 每 个 各 个 这 些 那 些 某 些 每 些
    之 后 之 前 以 后 以 前 现 在 过 去 将 来 已 经 正 在 刚 刚
    还 还 是 还 有 还 不 还 没 还 要 还 可 能
    来 去 上 下 进 出 回 到 往 由 自 到 达 离 开
    把 被 将 使 让 令 叫 教 给 给 予
    做 作 为 作 用 进 行 实 现 完 成 达 到
    中 的 得 地 得 着 过 的 得
    ''')

    # 主题关键词（用于识别主题句）
    TOPIC_PATTERNS = [
        r'本文主要(?:介绍|讲述|阐述|论述|讨论|分析|研究|说明|讲解)',
        r'本章.*?(?:主要|重点|核心|关键)',
        r'所谓.*?就是',
        r'.*?是指',
        r'.*?的定义',
        r'总结(?:一下|来说|而言)',
        r'总而言?之',
        r'综上所述',
        r'因此',
        r'所以',
        r'由此可见',
    ]

    # 重点句模式
    KEY_PATTERNS = [
        r'重要的是',
        r'关键在于',
        r'核心是',
        r'重点是',
        r'必须',
        r'需要注意',
        r'值得注意的是',
        r'首先',
        r'其次',
        r'最后',
        r'第一',
        r'第二',
        r'第三',
    ]

    def __init__(self):
        self.word_freq = Counter()
        self.word_doc_freq = defaultdict(int)

    def _segment_chinese(self, text: str) -> List[str]:
        """简单的中文分词（基于常见词汇提取）"""
        # 移除标点和空白
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        words = []

        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z][a-zA-Z0-9]*', text)
        words.extend([w.lower() for w in english_words if len(w) > 2])

        # 中文：提取2-4字的词组（简易分词
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', text)

        for chars in chinese_chars:
            # 2字词
            for i in range(len(chars) - 1):
                w = chars[i:i+2]
                if w not in self.STOP_WORDS and len(w) >= 2:
                    words.append(w)
            # 3字词
            for i in range(len(chars) - 2):
                w = chars[i:i+3]
                if w not in self.STOP_WORDS:
                    words.append(w)
            # 4字词
            for i in range(len(chars) - 3):
                w = chars[i:i+4]
                if w not in self.STOP_WORDS:
                    words.append(w)

        return words

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        sentences = re.split(r'[。！？!?\n；;]', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _split_paragraphs(self, text: str) -> List[str]:
        """分段"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]

    def compute_tfidf(self, documents: List[str]) -> List[Dict[str, float]]:
        """计算 TF-IDF 关键词"""
        all_words_list = []
        for doc in documents:
            words = self._segment_chinese(doc)
            word_freq = Counter(words)
            all_words_list.append(word_freq)

            # 更新文档频率
            unique_words = set(words)
            for w in unique_words:
                self.word_doc_freq[w] += 1

        n_docs = len(documents)
        results = []

        for word_freq in all_words_list:
            tfidf_scores = {}
            total_words = sum(word_freq.values()) or 1

            for word, freq in word_freq.items():
                tf = freq / total_words
                idf = math.log((n_docs + 1) / (self.word_doc_freq.get(word, 0) + 1)) + 1
                tfidf_scores[word] = tf * idf

            results.append(tfidf_scores)

        return results

    def extract_keywords(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """提取关键词"""
        paragraphs = self._split_paragraphs(text)
        if not paragraphs:
            paragraphs = [text]

        tfidf_list = self.compute_tfidf(paragraphs)

        # 合并所有段落的 TF-IDF 分数
        combined = defaultdict(float)
        for scores in tfidf_list:
            for word, score in scores.items():
                combined[word] += score

        # 按分数排序
        sorted_keywords = sorted(combined.items(), key=lambda x: x[1], reverse=True)

        # 去重（包含关系的词保留更长的
        filtered = []
        seen_words = set()
        for word, score in sorted_keywords:
            # 检查是否有更长的词已经包含了这个词
            is_duplicate = False
            for seen in seen_words:
                if word in seen and len(seen) > len(word):
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered.append((word, score))
                seen_words.add(word)
            if len(filtered) >= top_n:
                break

        return filtered[:top_n]

    def score_sentence(self, sentence: str, keywords: List[Tuple[str, float]], position: float) -> float:
        """给句子打分（TextRank 简化版 + 关键词权重 + 位置权重）"""
        score = 0.0
        words_in_sentence = set(self._segment_chinese(sentence))

        # 关键词权重
        keyword_dict = dict(keywords[:20])
        for word in words_in_sentence:
            if word in keyword_dict:
                score += keyword_dict[word]

        # 长度权重：中等长度的句子更可能是关键句
        sent_len = len(sentence)
        if 20 <= sent_len <= 150:
            score *= 1.2
        elif sent_len < 10:
            score *= 0.5

        # 位置权重：段首段尾更重要
        score *= (1.0 + position * 0.3)

        # 主题句模式
        for pattern in self.TOPIC_PATTERNS:
            if re.search(pattern, sentence):
                score *= 1.5
                break

        # 关键句模式
        for pattern in self.KEY_PATTERNS:
            if pattern in sentence:
                score *= 1.3
                break

        return score

    def extract_key_sentences(self, text: str, top_n: int = 5) -> List[Dict]:
        """提取关键句（摘要）"""
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        keywords = self.extract_keywords(text, top_n=30)

        scored = []
        for i, sent in enumerate(sentences):
            position = min(i / len(sentences), 1.0)
            # 位置分数：开头和结尾更重要
            pos_score = 1.0 - abs(position - 0.3) if position < 0.7 else 1.0 - (position - 0.7)
            score = self.score_sentence(sent, keywords, pos_score)
            scored.append({
                'text': sent,
                'score': score,
                'index': i
            })

        # 按分数排序，取前 N 个
        scored.sort(key=lambda x: x['score'], reverse=True)
        top_sentences = scored[:top_n]

        # 按原文顺序排列
        top_sentences.sort(key=lambda x: x['index'])

        result = []
        for s in top_sentences:
            result.append({
                'content': s['text'],
                'score': round(s['score'], 4),
                'type': 'summary' if s['score'] > 0.5 else 'important',
                'level': 'must' if s['score'] > 1.0 else 'important' if s['score'] > 0.5 else 'normal'
            })

        return result

    def identify_chapters(self, text: str) -> List[Dict]:
        """识别章节"""
        lines = text.splitlines()
        chapters = []

        chapter_regex = [
            r'^第\s*[一二三四五六七八九十百零0-9]+\s*[章编部分节]',
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+\d+',
            r'^\d+\.\s+.+',
            r'^[一二三四五六七八九十]+、',
            r'^【.*?】$',
        ]

        current_chapter = None
        chapter_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                if current_chapter:
                    chapter_lines.append('')
                continue

            is_chapter = False
            for pattern in chapter_regex:
                if re.match(pattern, line_stripped):
                    is_chapter = True
                    break

            if is_chapter and len(line_stripped) < 50:
                if current_chapter:
                    current_chapter['content'] = '\n'.join(chapter_lines).strip()
                    current_chapter['char_count'] = len(current_chapter['content'])
                    chapters.append(current_chapter)

                current_chapter = {
                    'title': line_stripped,
                    'content': '',
                    'key_points': [],
                    'summary': '',
                    'keywords': [],
                    'char_count': 0
                }
                chapter_lines = []
            elif current_chapter:
                chapter_lines.append(line_stripped)

        if current_chapter:
            current_chapter['content'] = '\n'.join(chapter_lines).strip()
            current_chapter['char_count'] = len(current_chapter['content'])
            chapters.append(current_chapter)

        # 如果没有识别到章节，按段落分块
        if not chapters:
            paragraphs = self._split_paragraphs(text)
            chunk_size = max(1, len(paragraphs) // 5)
            for i in range(0, len(paragraphs), chunk_size):
                chunk = paragraphs[i:i + chunk_size]
                chunk_text = '\n\n'.join(chunk)
                if chunk_text.strip():
                    # 用第一段作为标题
                    first_line = chunk[0][:30] + ('...' if len(chunk[0]) > 30 else '')
                    chapters.append({
                        'title': f'第{i // chunk_size + 1}部分：{first_line}',
                        'content': chunk_text,
                        'key_points': [],
                        'summary': '',
                        'keywords': [],
                        'char_count': len(chunk_text)
                    })

        return chapters

    def analyze_chapter(self, chapter: Dict) -> Dict:
        """分析单个章节"""
        content = chapter.get('content', '')
        if not content:
            return chapter

        # 提取章节关键词
        keywords = self.extract_keywords(content, top_n=10)
        chapter['keywords'] = [{'word': w, 'score': round(s, 4)} for w, s in keywords]

        # 提取章节关键句
        key_sentences = self.extract_key_sentences(content, top_n=4)
        chapter['key_points'] = key_sentences

        # 生成章节摘要
        if key_sentences:
            chapter['summary'] = key_sentences[0]['content']
        else:
            first_lines = [l for l in content.split('\n') if l.strip()][:2]
            chapter['summary'] = ' '.join(first_lines)[:100]

        return chapter

    def detect_document_theme(self, text: str, chapters: List[Dict]) -> Dict:
        """检测文档整体主题"""
        # 全文关键词
        all_keywords = self.extract_keywords(text, top_n=20)

        # 统计章节主题倾向
        themes = {
            '技术类': ['技术', '方法', '系统', '算法', '程序', '数据', '网络', '软件', '硬件', '开发'],
            '文学类': ['小说', '故事', '人物', '情节', '描写', '文学', '诗歌', '散文', '作者'],
            '历史类': ['历史', '时代', '战争', '王朝', '皇帝', '朝代', '世纪', '年代', '考古'],
            '哲学类': ['哲学', '思想', '存在', '意识', '精神', '价值', '真理', '认识', '唯物主义'],
            '商业类': ['商业', '市场', '企业', '管理', '经济', '投资', '金融', '创业', '营销', '战略', '产品'],
            '科普类': ['科学', '研究', '实验', '发现', '宇宙', '生命', '进化', '基因', '细胞'],
            '心理类': ['心理', '情绪', '行为', '认知', '情感', '人格', '社会', '关系'],
        }

        theme_scores = {}
        keyword_set = set(w for w, s in all_keywords)
        for theme, theme_words in themes.items():
            score = sum(1 for w in theme_words if w in keyword_set)
            theme_scores[theme] = score

        # 找出得分最高的主题
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        main_theme = sorted_themes[0][0] if sorted_themes[0][1] > 0 else '综合类'

        return {
            'main_theme': main_theme,
            'theme_scores': theme_scores,
            'top_keywords': [{'word': w, 'score': round(s, 4)} for w, s in all_keywords[:15]],
        }

    def generate_study_guide(self, text: str, chapters: List[Dict]) -> Dict:
        """生成学习指南"""
        guide = {
            'total_chapters': len(chapters),
            'total_chars': len(text),
            'estimated_read_time': max(1, len(text) // 500),  # 按500字/分钟
            'difficulty_level': '简单',
            'core_points': [],
            'review_questions': [],
            'mind_map_outline': [],
        }

        # 难度评估
        if len(text) < 5000:
            guide['difficulty_level'] = '简单'
        elif len(text) < 20000:
            guide['difficulty_level'] = '中等'
        else:
            guide['difficulty_level'] = '较难'

        # 收集所有章节的核心要点
        all_points = []
        for ch in chapters:
            for point in ch.get('key_points', []):
                all_points.append({
                    'chapter': ch['title'],
                    'content': point['content'],
                    'level': point.get('level', 'normal')
                })

        guide['core_points'] = all_points[:10]

        # 生成复习问题（从关键句生成
        for point in all_points[:5]:
            content = point['content']
            if len(content) > 20:
                # 简单的问题生成：把陈述句改成疑问句
                q = content[:40] + '...？'
                guide['review_questions'].append({
                    'question': q,
                    'hint': point['chapter'],
                    'answer': content
                })

        # 思维导图大纲
        outline = []
        for ch in chapters[:8]:
            sub_points = [kp['content'][:20] + '...' for kp in ch.get('key_points', [])[:3]]
            outline.append({
                'chapter': ch['title'],
                'sub_points': sub_points
            })
        guide['mind_map_outline'] = outline

        return guide

    def full_analysis(self, text: str, filename: str = '') -> Dict:
        """完整分析"""
        result = {
            'filename': filename,
            'total_chars': len(text),
            'total_lines': len(text.splitlines()),
            'chapters': [],
            'summary': '',
            'theme': {},
            'keywords': [],
            'key_points': [],
            'study_guide': {},
        }

        if not text or len(text.strip()) < 50:
            result['summary'] = '文本内容过短，无法进行深度分析。'
            return result

        # 1. 识别章节
        chapters = self.identify_chapters(text)

        # 2. 分析每个章节
        analyzed_chapters = []
        for ch in chapters[:15]:  # 最多分析15章
            analyzed = self.analyze_chapter(ch)
            analyzed_chapters.append(analyzed)
        result['chapters'] = analyzed_chapters

        # 3. 全文主题检测
        theme_info = self.detect_document_theme(text, analyzed_chapters)
        result['theme'] = theme_info
        result['keywords'] = theme_info['top_keywords']

        # 4. 全文关键句（摘要）
        all_key_sentences = self.extract_key_sentences(text, top_n=6)
        result['key_points'] = all_key_sentences

        # 5. 全文摘要
        if all_key_sentences:
            result['summary'] = ' '.join([kp['content'] for kp in all_key_sentences[:3]])
        else:
            result['summary'] = text[:200] + '...'

        # 6. 学习指南
        result['study_guide'] = self.generate_study_guide(text, analyzed_chapters)

        return result


def analyze_text(text: str, filename: str = '') -> Dict:
    """便捷函数：分析文本"""
    analyzer = TextAnalyzer()
    return analyzer.full_analysis(text, filename)


if __name__ == '__main__':
    # 测试
    test_text = """
第一章 认知革命

大约在距今7万到3万年前，出现了新的思维和沟通方式，这也正是所谓的认知革命。

认知革命究竟是怎么发生的呢？为什么偏偏是在这个时间点，而不是更早或更晚？

这一切的原因，至今仍是个谜。普遍认为，一次偶然的基因突变，改变了智人的大脑内部连接方式，让他们以前所未有的方式来思考，用完全新式的语言来沟通。

这次突变的发生，纯粹就是出于纯粹的偶然。但重要的是，这种新的语言有什么特别之处？

最常见的理论，认为人类语言最为独特的地方，在于能够传达关于一些根本不存在的事物的信息。

据我们所知，只有智人能够表达关于从来没有看过、碰过、耳闻过的事物，而且讲得煞有其事。

"虚构"这件事的重点不只在于让人类能够拥有想象，更重要的是可以"一起"想象，共同的想象，编织出种种共同的虚构故事。

这样的虚构故事赋予智人前所未有的能力，让我们得以集结大批人力、灵活合作。

虽然我们没有办法用这种方式和陌生人合作，但正是因为如此，我们才有了社会。

第二章 农业革命

农业革命是人类历史上的一次重大变革，发生在大约1万年前。

农业革命让人类从狩猎采集的生活方式，转变为农业定居的生活方式。

这一转变带来了人口的大幅增长，但也带来了许多新的问题。

农民的工作实际上比狩猎采集者更加辛苦，而且饮食也更加单一。

农业革命可以说是历史上最大的骗局。

为什么这么说呢？因为农业革命并没有带来更好的生活，反而让人类陷入了更辛苦的工作中。

小麦驯化了小麦，而不是人类驯化了小麦。

这是一个非常重要的观点，值得我们深思。

总而言之，农业革命是人类历史的一个重要转折点，它改变了人类社会的结构和人类与自然的关系。

第三章 人类的融合统一

农业革命之后，人类社会开始了不断融合统一的进程。

这个过程中，金钱、帝国、宗教是三大重要力量。

金钱是有史以来最普遍也最有效的互信系统。

帝国的出现，让不同的民族和文化开始融合。

宗教则提供了共同的价值观和信仰体系。

这三大力量共同推动了人类社会的融合统一。
    """

    result = analyze_text(test_text, '人类简史.txt')
    print("文件名:", result['filename'])
    print("总字数:", result['total_chars'])
    print("主题:", result['theme']['main_theme'])
    print("关键词:", [k['word'] for k in result['keywords'][:10]])
    print("章节数:", len(result['chapters']))
    for ch in result['chapters']:
        print(f"  - {ch['title']}: {ch['char_count']}字, {len(ch['key_points'])}个要点")
    print("摘要:", result['summary'][:100], '...')
    print("学习指南 - 难度:", result['study_guide']['difficulty_level'])
    print("预计阅读时间:", result['study_guide']['estimated_read_time'], "分钟")
