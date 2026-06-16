import sqlite3
import os # 引入操作系统路径工具

# ==========================================
# 绝对路径锁定（核心修复点）
# ==========================================
# 获取当前这个 .py 文件所在的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 将目录和数据库文件名拼在一起
DB_FILE = os.path.join(CURRENT_DIR, "company_data.db")

def setup_database():
    print("1. 正在连接/创建本地数据库...")
    # 使用绝对路径连接数据库
    conn = sqlite3.connect(DB_FILE)
    
    # 获取一个“游标”（Cursor）
    cursor = conn.cursor()
    
    # ... 下面的创建表和插入数据的代码保持不变 ...

    print("2. 正在执行 SQL 语句建立数据表...")
    # 【SQL 实战】创建“员工报销额度表”
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            remaining_budget REAL NOT NULL
        )
    ''')

    # 【SQL 实战】创建“IT与报销工单记录表”
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            issue_type TEXT NOT NULL,       -- 工单类型：IT报修 / 财务报销
            description TEXT NOT NULL,      -- 具体事由
            amount REAL DEFAULT 0,          -- 涉及金额（如果是报修则为0）
            status TEXT DEFAULT '已提交'     -- 处理状态
        )
    ''')

    print("3. 正在写入初始测试数据...")
    # 先清空一下预算表，防止重复运行代码导致数据重复
    cursor.execute("DELETE FROM employee_budgets")
    
    # 插入两条测试数据（模拟公司的真实系统）
    test_data = [
        ("张三", 2000.0), # 张三有 2000 块报销额度
        ("李四", 500.0)   # 李四只有 500 块报销额度
    ]
    # 使用 executemany 批量写入数据
    cursor.executemany('''
        INSERT INTO employee_budgets (employee_name, remaining_budget) 
        VALUES (?, ?)
    ''', test_data)

    # 提交保存所有的更改，并关闭连接
    conn.commit()
    conn.close()
    print("🎉 数据库初始化成功！所有表结构和初始数据已就绪。")

# 运行建库函数
if __name__ == "__main__":
    setup_database()