
from clickhouse_driver import Client
import json
import pandas as pd
from mysql.connector import pooling
import mysql.connector
from tqdm import tqdm
import time

# ClickHouse 连接参数（OpenAlex）
params_clickhouse_openalex = {
    'host': '',
    'port': '',
    'database': '',
    'user': '',
    'password': ''
}

def make_client(params, retries=2, delay_sec=2):
    last_exc = None
    for _ in range(retries + 1):
        try:
            return Client(
                **params,
                connect_timeout=10,
                send_receive_timeout=30,
            )
        except Exception as e:
            last_exc = e
            time.sleep(delay_sec)
    raise RuntimeError(f"ClickHouse 连接失败: {last_exc}")

# SQL 查询
sql_query = """
SELECT
    id,
    doi,
    tweets,
    is_in_altmetric
FROM disruption_papers.twitter_data_new
WHERE is_in_altmetric = 1 and tweets !='[]'
LIMIT 1000
"""

# 主流程
client = make_client(params_clickhouse_openalex)

try:
    results = client.execute(sql_query)
    print(f"查询成功，返回 {len(results)} 行")

    # 转成 DataFrame
    df = pd.DataFrame(
        results,
        columns=["id", "doi", "tweets", "is_in_altmetric"]
    )

    # 保存为 CSV
    out_path = "alt_disruption/reviwer1/github/data/twitter_data_sample.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")

    print(f"CSV 已保存到: {out_path}")

except Exception as e:
    print(f"执行失败: {e}")
    try:
        client.execute("SELECT 1")
        print("连接仍然可用")
    except Exception as e2:
        print(f"回退查询仍失败: {e2}")
        raise

finally:
    client.disconnect()
    print("ClickHouse 连接已关闭")
