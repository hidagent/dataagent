---
name: api-tester
description: API 测试技能，帮助测试和调试 HTTP API 接口
category: testing
tags: [api, testing, http, rest, debug]
---

# API 测试技能

## 概述

这个技能帮助你测试和调试 HTTP API：
- 发送各种 HTTP 请求
- 验证响应数据
- 性能测试
- 自动化测试脚本生成

## 使用方法

### 1. 基本请求

**GET 请求**
```python
import requests

response = requests.get(
    'https://api.example.com/users',
    headers={'Authorization': 'Bearer token'},
    params={'page': 1, 'limit': 10}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

**POST 请求**
```python
response = requests.post(
    'https://api.example.com/users',
    headers={
        'Authorization': 'Bearer token',
        'Content-Type': 'application/json'
    },
    json={
        'name': '张三',
        'email': 'zhangsan@example.com'
    }
)
```

**文件上传**
```python
with open('file.pdf', 'rb') as f:
    response = requests.post(
        'https://api.example.com/upload',
        files={'file': f},
        data={'description': '文件描述'}
    )
```

### 2. 响应验证

```python
def validate_response(response, expected_status=200):
    """验证 API 响应"""
    # 状态码检查
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}"
    
    # JSON 格式检查
    try:
        data = response.json()
    except ValueError:
        raise AssertionError("Response is not valid JSON")
    
    # 响应时间检查
    assert response.elapsed.total_seconds() < 2, \
        f"Response too slow: {response.elapsed.total_seconds()}s"
    
    return data

# 使用
data = validate_response(response)
assert 'id' in data, "Missing 'id' field"
assert data['status'] == 'success', f"Unexpected status: {data['status']}"
```

### 3. 测试用例模板

```python
import unittest
import requests

class APITestCase(unittest.TestCase):
    BASE_URL = 'https://api.example.com'
    TOKEN = 'your-token'
    
    def setUp(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.TOKEN}',
            'Content-Type': 'application/json'
        })
    
    def test_get_users(self):
        """测试获取用户列表"""
        response = self.session.get(f'{self.BASE_URL}/users')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('users', data)
        self.assertIsInstance(data['users'], list)
    
    def test_create_user(self):
        """测试创建用户"""
        payload = {
            'name': 'Test User',
            'email': 'test@example.com'
        }
        response = self.session.post(
            f'{self.BASE_URL}/users',
            json=payload
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['name'], payload['name'])
    
    def test_invalid_request(self):
        """测试无效请求"""
        response = self.session.post(
            f'{self.BASE_URL}/users',
            json={}  # 缺少必填字段
        )
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
```

### 4. cURL 命令生成

根据请求参数生成 cURL 命令：

```bash
# GET 请求
curl -X GET 'https://api.example.com/users?page=1&limit=10' \
  -H 'Authorization: Bearer token' \
  -H 'Content-Type: application/json'

# POST 请求
curl -X POST 'https://api.example.com/users' \
  -H 'Authorization: Bearer token' \
  -H 'Content-Type: application/json' \
  -d '{"name": "张三", "email": "zhangsan@example.com"}'

# 文件上传
curl -X POST 'https://api.example.com/upload' \
  -H 'Authorization: Bearer token' \
  -F 'file=@/path/to/file.pdf' \
  -F 'description=文件描述'
```

## 输出格式

测试结果应包含：

```markdown
## API 测试报告

### 请求信息
- URL: [完整 URL]
- Method: [HTTP 方法]
- Headers: [请求头]
- Body: [请求体]

### 响应信息
- Status: [状态码] [状态文本]
- Time: [响应时间]
- Headers: [响应头]
- Body:
```json
[响应体]
```

### 验证结果
- ✅ 状态码正确
- ✅ 响应格式正确
- ❌ 字段验证失败: [详情]

### cURL 命令
```bash
[可复制的 cURL 命令]
```
```

## 常见问题排查

1. **401 Unauthorized**: 检查 Token 是否有效
2. **403 Forbidden**: 检查权限配置
3. **404 Not Found**: 检查 URL 路径
4. **500 Internal Server Error**: 查看服务器日志
5. **超时**: 检查网络连接和服务器状态
