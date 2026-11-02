"""直接测试 analyzer 模块"""
import sys
sys.path.insert(0, '.')
from analyzer import analyze_text

with open('../test_document.txt', 'r', encoding='utf-8') as f:
    text = f.read()

result = analyze_text(text, 'test.txt')

print('顶层字段:', list(result.keys()))
print()
print('summary 是否有值:', bool(result.get('summary')))
print('theme:', result.get('theme'))
print('keywords 数量:', len(result.get('keywords', [])))
print('study_guide:', result.get('study_guide'))
print()
print('第一章:', list(result['chapters'][0].keys()))
print('第一章关键词:', len(result['chapters'][0].get('keywords', [])))
print('第一章要点:', len(result['chapters'][0].get('key_points', [])))
