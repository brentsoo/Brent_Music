import requests

api_key = "你的API_KEY"
# 检查 v1beta 下的所有可用模型
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    models = response.json()
    print("--- 你可以使用的模型列表 ---")
    for m in models.get('models', []):
        # 只要支持 generateContent 的模型都可以用
        if "generateContent" in m.get('supportedGenerationMethods', []):
            print(f"模型 ID: {m['name']}")
except Exception as e:
    print(f"查询失败: {e}")
