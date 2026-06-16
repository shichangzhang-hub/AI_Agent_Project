import requests # 导入我们刚才安装的“电话”工具

# 1. 确定要拨打的电话号码（这是一个免费的测试 API，模拟一篇新闻）
url = "https://jsonplaceholder.typicode.com/posts/1"

# 2. 拨打电话，获取对方的回复
print("正在呼叫外部接口...")
response = requests.get(url)

# 3. 检查电话是否接通（在网络世界，状态码 200 代表一切顺利）
if response.status_code == 200:
    print("接通成功！正在解析内容...\n")
    
    # 4. 把对方回复的格式（JSON）转换成 Python 能看懂的“字典”
    news_data = response.json()
    
    # 5. 提取并打印出我们关心的部分：标题和正文
    print("📰 抓取到的新闻标题：")
    print(news_data['title'])
    print("-" * 30)
    print("📝 抓取到的新闻正文：")
    print(news_data['body'])

else:
    # 如果没接通（比如网络断了，或者网址写错了）
    print(f"抓取失败，错误代码: {response.status_code}")