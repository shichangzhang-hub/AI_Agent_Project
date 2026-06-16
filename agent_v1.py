import requests
import pandas as pd # 导入我们刚安装的表格处理工具
from openai import OpenAI

# ==========================================
# 步骤一：抓取外部数据 (程序的眼睛)
# ==========================================
print("1. 正在全网搜罗最新情报...")
url = "https://jsonplaceholder.typicode.com/posts/1"
response = requests.get(url)
news_data = response.json()
title = news_data['title']
body = news_data['body']
print("情报获取成功！\n")

# ==========================================
# 步骤二：交给大模型处理 (程序的大脑)
# ==========================================
print("2. 正在将情报提交给智谱大脑进行分析...")
# 换成了你刚刚申请的智谱专属钥匙
API_KEY = "your_api_key_here"
# 换成了智谱的大门地址
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/" 

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 将抓取到的动态变量 {title} 和 {body} 塞进提示词里
prompt = f"请将下面这段拉丁文翻译成中文，并用一句话总结它的核心意思。\n\n标题：{title}\n正文：{body}"

ai_response = client.chat.completions.create(
    model="glm-4-flash", # 这里改成了智谱的免费高频模型
    messages=[
        {"role": "system", "content": "你是一个资深的情报分析师，擅长精准提炼信息。"},
        {"role": "user", "content": prompt}
    ]
)
ai_summary = ai_response.choices[0].message.content
print("分析完成！\n")

# ==========================================
# 步骤三：封装与自动化输出 (程序的手)
# ==========================================
print("3. 正在生成实体简报 Excel...")

# 1. 把零散的数据整理成表格需要的格式（列表里嵌套字典）
excel_data = [{
    "新闻来源标题": title,
    "原始外文正文": body,
    "AI 深度总结": ai_summary
}]

# 2. 将数据转换为数据框（DataFrame），并导出为 Excel 文件
df = pd.DataFrame(excel_data)
df.to_excel("每日AI自动简报.xlsx", index=False)

print("🎉 任务圆满结束！请查看左侧文件夹，你的 Excel 报告已经生成。")