import json
from openai import OpenAI
# 导入我们刚才写好的“机械臂”
from db_tools import get_employee_budget, submit_ticket

# 1. 配置大模型
API_KEY = "your_api_key_here"  # 替换成你自己的 API Key
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ==========================================
# 🌟 核心架构：多工具说明书 (Tool Schema)
# ==========================================
# 我们给 AI 准备了两个工具，并加上了严格的字段约束
tools_list = [
    {
        "type": "function",
        "function": {
            "name": "check_budget",
            "description": "当用户想要查询报销额度、剩余预算时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "员工姓名，例如：张三"}
                },
                "required": ["employee_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "当用户想要提交IT报修或财务报销工单时调用。注意：如果是报销，必须确保用户提供了金额和事由，否则不要调用，应向用户追问缺失信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "发起工单的员工姓名"},
                    "issue_type": {"type": "string", "enum": ["IT报修", "财务报销"], "description": "工单类型，只能是这两者之一"},
                    "description": {"type": "string", "description": "报修或报销的具体事由"},
                    "amount": {"type": "number", "description": "如果是财务报销，涉及的金额数。如果是IT报修，默认为0"}
                },
                # 强制约束：这四个字段必须全部收集齐才能调用！
                "required": ["employee_name", "issue_type", "description", "amount"]
            }
        }
    }
]

# ==========================================
# 🌟 核心循环：处理用户消息
# ==========================================
def chat_with_agent(user_message):
    print(f"\n👨‍💼 员工发消息：{user_message}")
    print("🤖 Agent 正在思考和调度...")
    
    # 构建系统人设，强调“反问”机制
    messages = [
        {"role": "system", "content": "你是一个严谨的公司后勤助理。你可以使用工具查额度或提交工单。如果用户提交报销但没有说清楚金额或事由，你必须友善地反问他们，绝不能自己编造数据！"},
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        tools=tools_list,
        tool_choice="auto"
    )

    ai_msg = response.choices[0].message

    # 检查 AI 是否决定调用工具
    if ai_msg.tool_calls:
        for tool_call in ai_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            print(f"   💡 Agent 决定使用工具：[{func_name}]，提取的参数：{args}")
            
            # 真正执行本地的 Python 函数
            if func_name == "check_budget":
                result = get_employee_budget(employee_name=args.get("employee_name"))
                print(f"   返回给用户：{result}")
                
            elif func_name == "create_ticket":
                result = submit_ticket(
                    employee_name=args.get("employee_name"),
                    issue_type=args.get("issue_type"),
                    description=args.get("description"),
                    amount=args.get("amount", 0)
                )
                print(f"   返回给用户：{result}")
    else:
        # 如果 AI 觉得信息不够，没调用工具，它就会走纯文本回复（反问用户）
        print(f"   💬 Agent 回复：{ai_msg.content}")

# ==========================================
# 模拟业务场景测试
# ==========================================
if __name__ == "__main__":
    print("=== 🚀 企业智能工单 Agent 上线 ===")
    
    # 场景1：简单的查询任务
    chat_with_agent("我是李四，帮我查一下我还能报销多少钱？")
    
    # 场景2：完美的提单任务
    chat_with_agent("我是李四，刚才买办公用品花了 200 块，帮我报销一下。")
    
    # 场景3：高级防伪/反问测试（故意不说金额和事由）
    chat_with_agent("我是张三，我要报销！")