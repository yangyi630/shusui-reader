"""打印完整返回数据"""
import requests
import random
import json

base = 'http://127.0.0.1:5000/api'

username = f'testdbg{random.randint(1000, 9999)}'
r = requests.post(f'{base}/auth/register', json={'username': username, 'password': '123456'})

r = requests.post(f'{base}/auth/login', json={'username': username, 'password': '123456'})
token = r.json()['data']['token']
headers = {'Authorization': f'Bearer {token}'}

with open('../test_document.txt', 'rb') as f:
    r = requests.post(f'{base}/analyze', files={'file': ('test.txt', f)}, headers=headers)

print('Status:', r.status_code)
print('Content-Type:', r.headers.get('Content-Type'))
print()
result = r.json()
print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
