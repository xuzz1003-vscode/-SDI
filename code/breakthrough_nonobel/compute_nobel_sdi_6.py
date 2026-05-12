# openalex 获取期刊数据
import os
# 限制底层库（numpy, sklearn, pandas 等）只使用一个线程，防止 CPU 占用过高
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
from clickhouse_driver import Client
import json
import pandas as pd
import mysql.connector
from mysql.connector import pooling
from tqdm import tqdm
from datetime import datetime
import itertools
from collections import Counter

databases = {
    'host': 'YOUR_DB_HOST',
    'port': 'YOUR_MYSQL_PORT',
    'database': 'YOUR_DATABASE',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD'
}
# 创建 MySQL 连接池
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


def get_papers_works(ids):
    """
    输入：论文 ID 列表
    输出：{论文ID: refs} {论文ID: puby}
    """
    ids_2_refs = {}
    ids_2_puby={}
    ids=list(ids)
    if not ids:
        return ids_2_refs
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        chunk_size = 2000

        for i in tqdm(range(0, len(ids), chunk_size), desc="查询 refs"):
            chunk = ids[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = f"""
                SELECT id, referenced_works,publication_year
                FROM works
                WHERE id IN ({placeholders})
            """
            cursor.execute(query, chunk)
            results = cursor.fetchall()
            for id_, referenced_works,publication_year in results:
                ids_2_refs[id_] = json.loads(referenced_works)
                ids_2_puby[id_] = publication_year
    except mysql.connector.Error as err:
        print(f"❌ refs查询错误: {err}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return ids_2_refs,ids_2_puby

# print(id)
params_clickhouse_openalex = {
    'host':'YOUR_DB_HOST',
    'port':'YOUR_CLICKHOUSE_PORT',
    'database':'openalex',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD'
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
            import time as _t
            _t.sleep(delay_sec)
    raise RuntimeError(f"ClickHouse 连接失败: {last_exc}")

def get_twitter_data(ids, chunk_size=500):
    """
    从 ClickHouse 获取 Twitter 数据，按论文 ID 提取提及信息。
    
    返回格式:
    {
        paper_id1: {
            author_id1: [year1, year2, ...],
            author_id2: [year1, year2, ...],
            ...
        },
        paper_id2: {...},
        ...
    }
    """
    user_mentions = dict()
    ids = list(ids)
    client = make_client(params_clickhouse_openalex)

    try:
        for i in tqdm(range(0, len(ids), chunk_size), desc="查询 Twitter 数据"):
            chunk = ids[i:i + chunk_size]
            # 注意：tuple 单元素时必须加逗号
            id_tuple = tuple(chunk) if len(chunk) > 1 else (chunk[0],)
            sql_query = f"SELECT id, tweets FROM disruption_papers.twitter_data_new WHERE id IN {id_tuple}"
            results = client.execute(sql_query)

            for paper_id, tweets in results:
                if not tweets:
                    continue
                author_dict = {}
                tweets_list = json.loads(tweets)
                for each in tweets_list:
                    author_id = each.get('author_handle')
                    time_str = each.get('time')
                    if not author_id or not time_str:
                        continue
                    # 尝试解析时间
                    try:
                        time_obj = datetime.strptime(time_str, "%d %b %Y %I:%M%p")
                    except ValueError:
                        try:
                            time_obj = datetime.strptime(time_str, "%d %b %Y")
                        except ValueError:
                            continue
                    year = time_obj.strftime("%Y")  # 只保留年份
                    author_dict.setdefault(author_id, []).append(year)
                user_mentions[paper_id] = author_dict

        return user_mentions

    except Exception as e:
        print(f"查询 Twitter 数据失败: {e}")
        return user_mentions

    finally:
        client.disconnect()

def compute_metrics(focal_paper, puby, refs, user_mentions):
    """
    计算论文的各种指标(sDI, DI, DI5等)
    
    参数:
    focal_paper: 核心论文的DOI
    puby: 核心论文的发表年份(格式: 'YYYY')
    refs: 核心论文的参考文献DOI列表
    user_mentions: 包含论文提及信息的字典
    
    返回:
    包含所有指标的计算结果的字典
    """
    result = {}
    
    # 解析发表年份
    puby_year = int(puby)
    

    '''# 存储每个用户对参考文献的提及日期 {
    "user_id1": ["2023-01-15", "2023-02-20", ...],  # 该用户的所有提及日期
    "user_id2": ["2022-12-05", ...],
        ...
    }'''
    ref_dates_by_user = {}

    # 收集每个用户对参考文献的提及信息
    for ref in refs: 
        if ref in user_mentions:
            for user_id, dates in user_mentions[ref].items():
                if user_id in ref_dates_by_user:
                    ref_dates_by_user[user_id].extend(dates)
                else:
                    ref_dates_by_user[user_id] = dates.copy()
    
    # 获取所有参考文献的提及时间
    ref_mention_times = list(itertools.chain(*ref_dates_by_user.values()) if ref_dates_by_user else [])


    # 如果没有参考文献被提及，不直接返回空，而是继续计算
    if not ref_mention_times:
        ref_dates_by_user = {}  # 空字典
        # ref_mention_times = [puby_year]  # 让 time_gap = 0，至少计算核心论文自身
    
    # 找到最晚的提及时间并计算时间间隔(年)
    valid_years = [
                int(max(y))
                for y in user_mentions.get(focal_paper, {}).values()
                if y
            ]

    if valid_years:
        time_gap = max(valid_years) - puby_year
    else:
        time_gap = 0
    # print(f"time_gap: {time_gap}",puby_year)
    for i in range(time_gap + 1):
        # 计算提及核心论文的用户
        focal_user_ids = set()
        if focal_paper in user_mentions:
            for user_id, mention_times in user_mentions[focal_paper].items():
                if any(0 <= int(time) - puby_year <= i for time in mention_times):
                    focal_user_ids.add(user_id)

        # 计算提及参考文献的用户(核心论文发表后)
        ref_user_ids = []
        for user_id, mention_times in ref_dates_by_user.items():
            for time in mention_times:
                year_diff = int(time) - puby_year
                if year_diff >= 0 and year_diff <= i:
                    ref_user_ids.append(user_id)

        # 计算指标
        i_set = set(focal_user_ids) - set(ref_user_ids)
        j_set = set(ref_user_ids) & set(focal_user_ids)
        k_set = set(ref_user_ids) - set(focal_user_ids)
        ni = len(i_set)
        nj = len(j_set)
        nk = len(k_set)
        total = ni + nj + nk

        # DI5 相关
        ref_user_ids_count = Counter(ref_user_ids)
        j5_user_ids_set = set([user_id for user_id in j_set if ref_user_ids_count[user_id] >= 5])
        nj5 = len(j5_user_ids_set)
        total5 = ni + nj5 + nk

        # 计算 sDI / sDI5
        sdi = (ni - nj) / total if total > 0 else (1 if ni>0 else 0)
        sdi_xing = ni / total if total > 0 else (1 if ni>0 else 0)
        sdi_jing = nj / total if total > 0 else 0
        msdi = (ni + nj) * sdi if sdi is not None else None

        sdi5 = (ni - nj5) / total5 if total5 > 0 else (1 if ni>0 else 0)
        sdi5_xing = ni / total5 if total5 > 0 else (1 if ni>0 else 0)
        sdi5_jing = nj5 / total5 if total5 > 0 else 0
        mdi5 = (ni + nj5) * sdi5 if sdi5 is not None else None

        result[i] = {
            'sDI': float(sdi),
            'sDI_xing': float(sdi_xing),
            'sDI_jing': float(sdi_jing),
            'msDI': float(msdi) if msdi is not None else None,
            'sDI5': float(sdi5),
            'sDI5_xing': float(sdi5_xing),
            'sDI5_jing': float(sdi5_jing),
            'msDI5': float(mdi5) if mdi5 is not None else None,
            'counts': {
                'ni': ni,
                'nj': nj,
                'nk': nk,
                'nj5': nj5,
                'total': total,
                'total5': total5
            }
        }
        
    return {focal_paper: result}

def run_sdi_pipeline(
    id_list: list,
    save_path: str
):
    """
    计算论文 SDI 及其变体指标（支持断点续跑）

    参数:
    breakthrough_path : str
        突破性论文 JSON 文件路径
    nobel_path : str
        诺奖论文 JSON 文件路径
    save_path : str
        结果输出 jsonl 文件路径
    """

    # ===== 1. 读取突破性论文 =====
    print(f"需要处理的总论文数量: {len(id_list)}")

    # ===== 4. 获取参考文献 & 发表年份 =====
    fpid_and_fr_dict, fpid_to_puby = get_papers_works(list(id_list))

    # ===== 5. 检查已处理论文（断点续跑） =====
    processed = set()
    if os.path.exists(save_path):
        with open(save_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed.update(data.keys())
                except Exception:
                    continue

    print(f"已处理论文数量: {len(processed)}")

    # ===== 6. 逐篇计算指标 =====
    with open(save_path, 'a', encoding='utf-8') as f_out:
        for pid in tqdm(id_list, desc="计算指标"):
            if pid in processed:
                continue

            # 发表年份
            puby = int(fpid_to_puby[pid])

            # 参考文献
            refs_of_focal_paper = fpid_and_fr_dict.get(pid, [])

            # Twitter 提及数据（核心论文 + 参考文献）
            user_mentions = get_twitter_data(refs_of_focal_paper + [pid])

            # 计算指标
            paper_metrics = compute_metrics(
                pid,
                puby,
                refs_of_focal_paper,
                user_mentions
            )

            # 写入结果
            f_out.write(json.dumps(paper_metrics, ensure_ascii=False) + '\n')
            f_out.flush()

    print("🎯 SDI 计算完成")

def main():
    """主函数，计算所有论文的指标并保存结果"""
    #突破性论文
    with open('alt_disruption/reviwer1/data/breakthrough_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
        breakthrough_data=json.load(f)

    breakthrough_id_list = list(breakthrough_data.keys())
    print(f"需要处理的突破性论文数量: {len(breakthrough_id_list)}")
    #诺奖论文
    with open('alt_disruption/reviwer1/data/nobel_prize_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
        nobel_data=json.load(f)
    nobel_id_list = list(nobel_data.keys())
    print(f"需要处理的诺奖论文数量: {len(nobel_id_list)}")
    id_list = set(breakthrough_id_list + nobel_id_list)
    run_sdi_pipeline(
        id_list=list(id_list),
        save_path='alt_disruption/reviwer1/new_data_results/experimental_group_SDI_and_its_variants.jsonl'
    )
   
if __name__ == '__main__':
    main()