import sqlite3
import os

# ==========================================
# 绝对路径锁定（核心修复点）
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(CURRENT_DIR, "company_data.db")

# ==========================================
# 工具一：查询额度 (只读，负责 SELECT)
# ==========================================
def get_employee_budget(employee_name):
    """查询员工的剩余报销额度"""
    print(f"   [系统底层] 正在查询数据库中 {employee_name} 的额度...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 执行 SQL 语句进行精准查询
    cursor.execute("SELECT remaining_budget FROM employee_budgets WHERE employee_name = ?", (employee_name,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return f"员工 {employee_name} 的剩余报销额度为：{result[0]}元"
    else:
        return f"未找到员工 {employee_name} 的财务信息，请确认姓名是否正确。"

# ==========================================
# 工具二：提交工单 (写入，负责 INSERT 和 UPDATE)
# ==========================================
def submit_ticket(employee_name, issue_type, description, amount=0):
    """提交工单。如果是财务报销，会自动检查并扣除额度"""
    print(f"   [系统底层] 正在为 {employee_name} 写入 {issue_type} 工单...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 核心商业逻辑：如果是报销，必须先验资！
    if issue_type == "财务报销":
        cursor.execute("SELECT remaining_budget FROM employee_budgets WHERE employee_name = ?", (employee_name,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return "提交失败：未找到该员工的财务账户。"
        
        current_budget = result[0]
        if current_budget < amount:
            conn.close()
            return f"❌ 提交失败：额度不足！当前仅剩 {current_budget} 元，无法报销 {amount} 元。"
        
        # 额度够，执行扣款 (UPDATE 语句)
        new_budget = current_budget - amount
        cursor.execute("UPDATE employee_budgets SET remaining_budget = ? WHERE employee_name = ?", (new_budget, employee_name))
        print(f"   [系统底层] 扣款成功！{employee_name} 剩余额度更新为: {new_budget}元")

    # 无论是不是报销，都要把工单记录下来 (INSERT 语句)
    cursor.execute('''
        INSERT INTO tickets (employee_name, issue_type, description, amount)
        VALUES (?, ?, ?, ?)
    ''', (employee_name, issue_type, description, amount))
    
    # 提交改动并关门
    conn.commit()
    conn.close()
    return f"✅ 工单已生成！类型：{issue_type}，事由：{description}。"

# ==========================================
# 本地测试区 (先不带 AI，自己测一下机械臂好不好用)
# ==========================================
if __name__ == "__main__":
    print("--- 正在测试本地数据库接口 ---")
    # 1. 查一下张三初始有多少钱
    print(get_employee_budget("张三"))
    
    # 2. 张三报销打车费 150 元
    print(submit_ticket("张三", "财务报销", "上周五加班打车", 150))
    
    # 3. 再查一下张三的钱，看看扣没扣
    print(get_employee_budget("张三"))
    
    # 4. 李四发起了不需要钱的 IT 报修
    print(submit_ticket("李四", "IT报修", "电脑频繁蓝屏", 0))
    
    # 5. 测试一下防呆机制（张三强行报销 50000 块）
    print(submit_ticket("张三", "财务报销", "买金条", 50000))