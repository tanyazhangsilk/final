
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.core.config import settings
    print("✅ 成功导入数据库配置。")
except ImportError as e:
    print(f"❌ 导入配置失败: {e}")
    print("请确保项目根目录下存在 'app/core/config.py'。")
    sys.exit(1)

def test_connection():
    """
    使用项目配置测试数据库连接。
    """
    try:
        print(f"正在尝试连接到数据库: {settings.database_url.replace(settings.DB_PASSWORD or settings.MYSQL_PASSWORD, '********')}")
        
        # 创建 SQLAlchemy 引擎
        engine = create_engine(settings.database_url)

        # 尝试建立连接并执行一个简单的查询
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            for row in result:
                if row[0] == 1:
                    print("✅ 数据库连接成功！")
                else:
                    print("❌ 连接成功，但测试查询返回了意外结果。")
        
    except ImportError:
        print("❌ 未能导入 SQLAlchemy。请确保已在虚拟环境中安装所有依赖项。")
        print(r"   运行: .\.venv\Scripts\pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n--- 故障排查建议 ---")
        print("1. 检查 'backend/.env' 文件中的数据库凭据 (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) 是否正确。")
        print("2. 确保 MySQL 服务器正在运行，并且可以从运行此脚本的计算机访问。")
        print("3. 检查防火墙设置，确保端口（默认为 3306）是开放的。")
        print("4. 确认数据库 '" + str(settings.DB_NAME or settings.MYSQL_DB) + "' 已经创建。")

if __name__ == "__main__":
    test_connection()
