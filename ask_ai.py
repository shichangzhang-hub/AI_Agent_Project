from openai import OpenAI # 导入刚刚安装的通讯工具包

# 1. 配置钥匙和地址（核心知识点：大模型 API 鉴权）
API_KEY = "5d8484d8b98445f283b1d0997095ced5.wLgZKwuLxozeqyLv" 
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# 2. 建立连接客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 3. 准备数据（这里是我们刚才在第一阶段抓取到的拉丁文模拟新闻）
news_text = """
quia et suscipit
suscipit recusandae consequuntur expedita et cum
reprehenderit molestiae ut ut quas totam
nostrum rerum est autem sunt rem eveniet architecto
"""

# 4. 核心环节：发送请求与编写提示词 (Prompt Engineering)
print("正在唤醒 DeepSeek 大脑思考中...")
response = client.chat.completions.create(
   model="glm-4-flash", # 2. 把模型名字改成智谱的免费模型
    messages=[
        # System 角色：给 AI 设定“人设”和全局规则
        {"role": "system", "content": "你是一个资深的新闻编辑，精通多国语言，擅长总结核心观点。"},
        
        # User 角色：你给 AI 下达的具体指令（这就是 JD 里的“提示词编写”）
        {"role": "user", "content": f"请将下面这段拉丁文翻译成中文，并用一句话总结它的核心意思。\n\n新闻内容：{news_text}"}
    ]
)

# 5. 剥洋葱一样，把 AI 回复的正文提取出来并打印
print("\n🤖 DeepSeek 的回复：")
print(response.choices[0].message.content)