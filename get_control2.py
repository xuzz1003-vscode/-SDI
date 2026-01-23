# openalex 获取期刊数据
from clickhouse_driver import Client
import json
import pandas as pd
from mysql.connector import pooling
import mysql.connector
from tqdm import tqdm
params_clickhouse_openalex = {
 
}
databases = {
    'host': '',
    'port': '',
    'database': '',
    'user': '',
    'password': ''
}
connection_pool = pooling.MySQLConnectionPool(
    pool_name="citation_pool",
    pool_size=10,
    host=databases['host'],
    port=databases['port'],
    user=databases['user'],
    password=databases['password'],
    database=databases['database'],
    pool_reset_session=False
)
def get_db_connection():
    """从连接池中获取 MySQL 连接"""
    return connection_pool.get_connection()

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
            import time as _t
            _t.sleep(delay_sec)
    raise RuntimeError(f"ClickHouse 连接失败: {last_exc}")

def get_twitter_user_counts(ids):
    """
    从db中获取Twitter用户提及数据
    
    返回格式:
    {
        id: {
            author_id1: [time1, time2...],
            author_id2: [time1, time2...],
            ...
        }
    }
    """
    ids=list(ids)
    sql_query="SELECT id,tweets,is_in_altmetric from disruption_papers.twitter_data_new  where id in {}".format(tuple(ids))
    client = make_client(params_clickhouse_openalex)
    results = client.execute(sql_query)
    twitter_user_counts=dict()
    for id,tweets,is_in_altmetric in results:
        author_id_set = set()
        if is_in_altmetric ==0:
            continue
        else:
            if  tweets.strip() == '[]':
                twitter_user_counts[id]=0
                continue
        try:    
            tweets_list=json.loads(tweets)
            for each in tweets_list:
                author_id_set .add(each['author_handle'])
            user_mentions = len(author_id_set)
            twitter_user_counts[id]=user_mentions
            
        except Exception as e:
            print(f"执行失败: {e}")
        try:
            results = client.execute('SELECT 1')
        
        except Exception as e2:
            print(f"回退查询仍失败: {e2}")
            raise
        finally:
            client.disconnect()
    return twitter_user_counts
def get_cited_by_counts(ids):
    """
    输入：论文 ID 列表
    输出：{论文ID: cited_by_counts}
    """
    ids=list(ids)
    ids_2_citations = {}

    if not ids:
        return ids_2_citations
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        chunk_size = 2000

        for i in tqdm(range(0, len(ids), chunk_size), desc="查询 cited_by_counts"):
            chunk = ids[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = f"""
                SELECT id, cited_by_count
                FROM works
                WHERE id IN ({placeholders})
            """
            cursor.execute(query, chunk)
            results = cursor.fetchall()
            for id_, cited_by_count in results:
                ids_2_citations[id_] = cited_by_count
    except mysql.connector.Error as err:
        print(f"❌ cited_by_counts查询错误: {err}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return ids_2_citations

def get_controls(experimental_id, twitter_user_counts,exp_ids):
    """
    根据试验组的推特用户数量筛选控制组：
    - 按 twitter_user_counts 的 value 从大到小排序
    - 找到 experimental_id 所在位置
    - 取其上下各 5 篇作为控制组
    """
    control_ids = set()

    if twitter_user_counts is None or experimental_id not in twitter_user_counts:
        return control_ids

    # 1. 按 value 从大到小排序（[(id, count), ...]）
    twitter_user_counts_sorted = sorted(
        twitter_user_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # 2. 找到 experimental_id 的索引位置
    ids_sorted = [pid for pid, _ in twitter_user_counts_sorted]
    idx = ids_sorted.index(experimental_id)

    # 3. 计算上下 5 篇的索引范围
    total = len(ids_sorted)
    start = max(0, idx - 2)
    end = min(len(ids_sorted), idx + 3)  # +3 是因为 Python 切片右开

    # 4. 收集控制组（排除自身 和实验组论文）
    for i in range(start, end):
        if ids_sorted[i] not in exp_ids:
            control_ids.add(ids_sorted[i])
    #如果没收集5篇，先从左边找，再从右边找
    while len(control_ids) < 5:
        if start > 0:
            start -= 1
            candidate = ids_sorted[start]
            if candidate not in exp_ids:
                control_ids.add(candidate)

        elif end < total:
            candidate = ids_sorted[end]
            end += 1
            if candidate not in exp_ids:
                control_ids.add(candidate)

        else:
            break

    return control_ids
import json

def build_controls_from_file(
    input_path: str,
    exp_ids:set,
    output_twitter_path: str,
    output_cited_path: str
):
    """
    从输入文件中读取突破性论文及候选控制组，
    分别基于 Twitter 用户提及数和 cited_by_counts 构建控制组，
    并将结果写入指定的输出文件路径。

    Parameters
    ----------
    input_path : str
        输入 JSON 文件路径（breakthrough_controls_new.json）
    output_twitter_path : str
        基于 Twitter 用户提及数的控制组输出路径
    output_cited_path : str
        基于引用数（cited_by_counts）的控制组输出路径

    Returns
    -------
    tuple
        (output_twitter_path, output_cited_path)
    """

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    exp_controls_twitter = {}
    exp_controls_cited = {}
    set_exp_ids = {}

    for i, line in enumerate(data):
        ids = set()
        experimental_id = line['experimental_id']
        ids.add(experimental_id)

        for c in line.get('controls', []):
            cid = c.get('id')
            if cid is not None:
                ids.add(cid)

        # 获取 Twitter 用户提及数
        twitter_user_counts = get_twitter_user_counts(ids)
        controls_twitter = get_controls(experimental_id, twitter_user_counts, exp_ids)
        if twitter_user_counts is None or twitter_user_counts.get(experimental_id,0) <20:
            continue
        # 获取引用数
        cited_by_counts = get_cited_by_counts(ids)
        controls_cited = get_controls(experimental_id, cited_by_counts, exp_ids)

        # 记录实验组信息（可用于统计）
        set_exp_ids[experimental_id] = twitter_user_counts.get(experimental_id, 0)

        # JSON 不支持 set，这里统一转为 list
        exp_controls_twitter[experimental_id] = list(controls_twitter)
        exp_controls_cited[experimental_id] = list(controls_cited)

    print("成功构建控制组的实验论文数量：", len(exp_controls_twitter))

    with open(output_twitter_path, 'w', encoding='utf-8') as f:
        json.dump(exp_controls_twitter, f, ensure_ascii=False, indent=2)

    with open(output_cited_path, 'w', encoding='utf-8') as f:
        json.dump(exp_controls_cited, f, ensure_ascii=False, indent=2)

    return output_twitter_path, output_cited_path

def get_exp_ids(input_path):
    exp_ids = set()
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i, line in enumerate(data):
        experimental_id = line['experimental_id']
        exp_ids.add(experimental_id)
    return exp_ids

def main():
    input_path1='alt_disruption/reviwer1/data/breakthrough_controls_new.json'
    breakthrough_exp_ids= get_exp_ids(input_path1)

    build_controls_from_file(
            input_path=input_path1,
            exp_ids=breakthrough_exp_ids,
            output_twitter_path='alt_disruption/reviwer1/data/breakthrough_with_controls_twitter_user_counts.json',
            output_cited_path='alt_disruption/reviwer1/data/breakthrough_with_controls_cited_by_counts.json'
        )

if __name__ == '__main__':
    main()