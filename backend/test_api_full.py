"""测试完整 API 调用"""
import requests
import random
import json

base = 'http://127.0.0.1:5000/api'

username = f'testapi{random.randint(1000, 9999)}'
r = requests.post(f'{base}/auth/register', json={'username': username, 'password': '123456'})
print('注册:', r.status_code)

r = requests.post(f'{base}/auth/login', json={'username': username, 'password': '123456'})
data = r.json()
print('登录:', data['code'])
token = data['data']['token']
headers = {'Authorization': f'Bearer {token}'}

# 上传文件
with open('../test_document.txt', 'rb') as f:
    r = requests.post(f'{base}/analyze', files={'file': ('test.txt', f)}, headers=headers)

result = r.json()
print()
print('API code:', result['code'])
print('API msg:', result['msg'])
print()
print('data 字段:', list(result['data'].keys()) if result.get('data') else 'NO DATA')
print()
print('summary:', result['data'].get('summary', '')[:80])
print('theme:', result['data'].get('theme'))
print('keywords count:', len(result['data'].get('keywords', [])))
print('study_guide keys:', list(result['data'].get('study_guide', {}).keys()) if result['data'].get('study_guide') else 'None')
print('chapters:', len(result['data'].get('chapters', [])))
