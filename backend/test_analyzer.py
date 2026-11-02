"""测试智能分析功能"""
import requests
import json

base = 'http://127.0.0.1:5000/api'

# 先注册登录
import random
username = f'testuser{random.randint(1000, 9999)}'
r = requests.post(f'{base}/auth/register', json={'username': username, 'password': '123456'})
print('注册:', r.status_code, r.text[:100])

r = requests.post(f'{base}/auth/login', json={'username': username, 'password': '123456'})
token = r.json()['data']['token']
headers = {'Authorization': f'Bearer {token}'}
print('登录成功')

# 上传文件测试分析
with open('../test_document.txt', 'rb') as f:
    r = requests.post(f'{base}/analyze', files={'file': ('test.txt', f)}, headers=headers)

result = r.json()
print('分析接口:', result['code'], result['msg'])
data = result['data']

print()
print('=== 文档分析结果 ===')
print('文件名:', data.get('filename'))
print('总字数:', data.get('total_chars'))
print('主题:', data.get('theme', {}).get('main_theme'))
print('关键词:', [k['word'] for k in data.get('keywords', [])[:10]])
print('章节数:', len(data.get('chapters', [])))
for ch in data.get('chapters', []):
    title = ch.get('title', '')
    chars = ch.get('char_count', 0)
    points = len(ch.get('key_points', []))
    print(f'  - {title}: {chars}字, {points}要点')

print()
print('摘要:', data.get('summary', '')[:150], '...')
print()
guide = data.get('study_guide', {})
print('学习指南:')
print('  难度:', guide.get('difficulty_level'))
print('  预计阅读时间:', guide.get('estimated_read_time'), '分钟')
print('  核心要点数:', len(guide.get('core_points', [])))
print('  复习问题数:', len(guide.get('review_questions', [])))
print('  思维导图节点数:', len(guide.get('mind_map_outline', [])))
print()
print('智能分析测试通过！')
