import json
import pandas as pd
from openai import OpenAI

# 1. 准备大模型通讯器
API_KEY = "your_api_key_here"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ==========================================
# 🌟 核心一：定义本地的“实体工具”
# ==========================================
# 这就是一个普通的 Python 函数，负责生成 Excel
def save_to_excel(title, summary, filename="AI自主保存的简报.xlsx"):
    print(f"\n🔧 [系统底层执行] 正在启动本地工具保存 Excel: {filename}...")
    df = pd.DataFrame([{"新闻标题": title, "核心总结": summary}])
    df.to_excel(filename, index=False)
    return "Excel 文件已成功生成！"

# ==========================================
# 🌟 核心二：给 AI 写的“工具说明书” (Tool Schema)
# ==========================================
# 把我们的 Python 函数用字典的形式描述出来，让大模型能看懂
tools_list = [
    {
        "type": "function",
        "function": {
            "name": "save_to_excel",
            "description": "当用户要求将新闻、总结或任何信息保存/写入 Excel 文件时，必须调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "要保存的新闻标题"},
                    "summary": {"type": "string", "description": "这篇新闻的浓缩总结"}
                },
                "required": ["title", "summary"] # 告诉 AI 这两个参数必填
            }
        }
    }
]

# ==========================================
# 🌟 核心三：下达模糊任务，考验 Agent
# ==========================================
# 我们故意用自然语言，不写死代码逻辑
user_task = "今天我看到一篇关于大模型降价的新闻，正文说多家厂商宣布API免费。你帮我一句话总结下，然后存到表格里吧。"
print(f"🗣️ 老板下达任务: {user_task}\n")
print("🤖 智谱 Agent 正在思考并规划任务路线...")

response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": user_task}],
    tools=tools_list,      # 【关键动作】把工具说明书递给 AI
    tool_choice="auto"     # 【关键动作】让 AI 自己决定用不用工具
)

# ==========================================
# 🌟 核心四：拦截 AI 的决定，并帮它“动手”
# ==========================================
ai_decision = response.choices[0].message

# 检查 AI 是不是决定使用工具了（tool_calls 是否有内容）
if ai_decision.tool_calls:
    print("💡 漂亮！Agent 判定需要使用外部工具！")
    
    for tool_call in ai_decision.tool_calls:
        # 确认 AI 选中的是我们刚才提供的 save_to_excel 工具
        if tool_call.function.name == "save_to_excel":
            
            # AI 非常聪明地帮我们把口语化的句子，转化成了工具需要的参数！
            arguments = json.loads(tool_call.function.arguments)
            print(f"📦 Agent 提取并准备好的参数：\n   - 提取的标题: {arguments.get('title')}\n   - 构思的总结: {arguments.get('summary')}")
            
            # 真正的执行：把 AI 准备好的参数，塞进我们本地的 Python 函数里运行
            save_to_excel(title=arguments.get('title'), summary=arguments.get('summary'))
            print("🎉 Agent 任务圆满闭环！")
else:
    print("Agent 认为只是纯聊天，不需要动用工具。它的回复是：")
    print(ai_decision.content)