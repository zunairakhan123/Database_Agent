import pytest
from testcontainers.mysql import MySqlContainer
import pymysql
from backend.app.database.session_manager import WorkspaceSession

@pytest.mark.integration
def test_mysql_native_federation_live_freshness():
    with MySqlContainer("mysql:8.0") as mysql:
        # 1. Seed MySQL using standard driver (simulating live external DB)
        conn = pymysql.connect(
            host=mysql.get_container_host_ip(),
            port=mysql.get_exposed_port(3306),
            user=mysql.username, password=mysql.password, database=mysql.dbname
        )
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE inventory (sku VARCHAR(32), stock INT);")
            cursor.execute("INSERT INTO inventory VALUES ('SKU-001', 500);")
        conn.commit()
            
        # 2. Attach natively via DuckDB (No Pandas!)
        session = WorkspaceSession("workspace_mysql_live")
        mysql_url = f"mysql://{mysql.username}:{mysql.password}@{mysql.get_container_host_ip()}:{mysql.get_exposed_port(3306)}/{mysql.dbname}"
        
        session.conn.execute(f"ATTACH '{mysql_url}' AS mysql_remote (TYPE MYSQL, READ_ONLY);")
        
        # 3. Read it
        res = session.conn.execute("SELECT stock FROM mysql_remote.inventory;").fetchall()
        assert res[0][0] == 500
        
        # 4. Prove Live Freshness: Update MySQL externally
        with conn.cursor() as cursor:
            cursor.execute("UPDATE inventory SET stock = 100 WHERE sku = 'SKU-001';")
        conn.commit()
        
        # 5. Read again via DuckDB without re-attaching - it must be fresh!
        res_fresh = session.conn.execute("SELECT stock FROM mysql_remote.inventory;").fetchall()
        assert res_fresh[0][0] == 100 
        
        session.close()