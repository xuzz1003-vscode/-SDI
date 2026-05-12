import json
import mysql.connector
from mysql.connector import pooling
from collections import defaultdict, Counter
from tqdm import tqdm
import os

# ======= 写死路径：你只改这两个就行 ========
# input_path = 'alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl'

# ==========================================

# 数据库配置
databases = {
    'host': 'YOUR_DB_HOST',
    'port': 'YOUR_MYSQL_PORT',
    'database': 'YOUR_DATABASE',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD'
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

# 全局缓存
GLOBAL_CITATION_CACHE = {}

# ------------------------------------------------------------
# ⚙️ 工具函数定义
# ------------------------------------------------------------

def get_db_connection():
    """返回数据库连接"""
    return connection_pool.get_connection()


def get_batch_citations(ids):
    """
    批量获取引用关系
    输入：
        ids: list[str] 论文id列表
    输出：
        dict {cited_id: [citing_id1, citing_id2, ...]}
    """
    if not ids:
        return {}
    
    uncached_ids = [d for d in ids if d not in GLOBAL_CITATION_CACHE]
    cached_results = {d: GLOBAL_CITATION_CACHE[d] for d in ids if d in GLOBAL_CITATION_CACHE}
    if not uncached_ids:
        return cached_results
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        chunk_size = 2000
        for i in range(0, len(uncached_ids), chunk_size):
            chunk = uncached_ids[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = f"""
                SELECT citing, cited
                FROM works_relation
                WHERE cited IN ({placeholders})
            """
            cursor.execute(query, chunk)
            results = cursor.fetchall()

            for citing, cited in results:
                GLOBAL_CITATION_CACHE.setdefault(cited, set()).add(citing)

        cached_results.update({
            id_: list(GLOBAL_CITATION_CACHE.get(id_, []))
            for id_ in ids
        })

    except mysql.connector.Error as err:
        print(f"[get_batch_citations] 数据库错误: {err}")

    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return cached_results


def get_batch_papers_puby(ids):
    """
    批量获取论文发表时间
    输入：
        ids: list[str]
    输出：
        dict {id: 'YYYY-MM-DD'}
    """
    ids=list(set(ids))
    ids_2_puby = {}
    if not ids:
        return ids_2_puby
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        chunk_size = 2000

        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = f"""
                SELECT id, publication_year
                FROM works
                WHERE id IN ({placeholders})
            """
            cursor.execute(query, chunk)
            results = cursor.fetchall()
            for id_, publication_year in results:
                ids_2_puby[id_] =str(publication_year)
    except mysql.connector.Error as err:
        print(f"[get_batch_papers_puby] 数据库错误: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return ids_2_puby


def get_puby_citations(citations_dict):
    """
    把引文发表时间按年份分组
    输入：
        citations_dict: {citing_id: 'YYYY-MM-DD'}
    输出：
        dict {year: [citing_id1, citing_id2, ...]}
    """
    citation_puby = defaultdict(list)
    for citing_doi, creation in citations_dict.items():
        try:
            if creation:
                if '-' in str(creation):
                    year = int(creation.split('-')[0])
                else: 
                    year=int(creation)
                citation_puby[int(year)].append(citing_doi)
        except Exception:
            continue
    return citation_puby


def compute_all_metrics(id, refs, paper_to_puby, time_span):
    try:
        dois_to_fetch = [id] + refs
        get_batch_citations(dois_to_fetch)
        start_year = paper_to_puby[id]
        focal_citations = GLOBAL_CITATION_CACHE.get(id, set())
        focal_citations_puby= get_batch_papers_puby(focal_citations)
        focal_puby = get_puby_citations(focal_citations_puby)
        refs_citation_cts = Counter()
        all_refs_citations_set = set()
        # 获取参考文献的引用
        for ref in refs:
            ref_citations = GLOBAL_CITATION_CACHE.get(ref, set())
            all_refs_citations_set.update(ref_citations)
            for citing_doi in ref_citations:
                refs_citation_cts[citing_doi] += 1

        ref_citations_puby = get_batch_papers_puby(all_refs_citations_set)
        ref_puby = get_puby_citations(ref_citations_puby)
        results = {}
         # 收集各年份的引用
        time_span=2025-start_year+1
        for offset in range(time_span):
            end_year = int(start_year) + offset
            focal_year_citations = set()
            ref_year_citations = set()
            for y in range(int(start_year), end_year + 1):
                focal_year_citations.update(focal_puby.get(y, []))
                ref_year_citations.update(ref_puby.get(y, []))

            # 计算基本集合
            # 注意：所有 i/j/k 的计算都是在以下时间段中进行的：
            # 从目标论文发表年份（start_year）起，直到 start_year + offset 年份内
            # 即统计的是目标论文发表后第 offset 年的累积引用行为
            i = focal_year_citations - ref_year_citations  # 仅引用目标论文的，在 [focal_year, focal_year+offset] 区间内，仅引用了 foca
            j = focal_year_citations & ref_year_citations  # 共同引用两者的，在 [focal_year, focal_year+offset] 区间内
            k = ref_year_citations - focal_year_citations  # 仅引用参考文献引用，在 [focal_year, focal_year+offset] 区间内
            i_j_k = focal_year_citations | ref_year_citations  # 所有引用

            ni = len(i)
            nj = len(j)
            nk = len(k)
            total = ni + nj + nk
            di = (ni - nj) / total if total > 0 else None
            di_xing = ni / total if total > 0 else None
            di_jing = nj / total if total > 0 else None
            mdi = (ni + nj) * di if di is not None else None
            nj5 = len(set([c for c in j if refs_citation_cts[c] >= 5]))
            total5 = ni + nj5 + nk
            di5 = (ni - nj5) / total5 if total5 > 0 else None
            di5_xing = ni / total5 if total5 > 0 else None
            di5_jing = nj5 / total5 if total5 > 0 else None
            mdi5 = (ni + nj5) * di5 if di5 is not None else None
            results[str(offset)] = {
                'di': di, 'di_xing': di_xing, 'di_jing': di_jing, 'mdi': mdi,
                'di5': di5, 'di5_xing': di5_xing, 'di5_jing': di5_jing, 'mdi5': mdi5,
                'counts': {'ni': ni, 'nj': nj, 'nk': nk, 'nj5': nj5, 'total': total, 'total5': total5}
            }
        return id, results
    except Exception as e:
        print(f"[compute_all_metrics] 处理 {id} 出错: {str(e)}")
        return id, {"error": str(e)}

def load_handle_doi(path):
    handle_dois = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            handle_dois.add(data.get('doi'))
    return handle_dois

def save_single_result(doi, result, save_path):
    with open(save_path, 'a', encoding='utf-8') as f:
        json.dump({doi: result}, f, ensure_ascii=False)
        f.write('\n')
        f.flush()

def load_exist_dois(result_path):
    exist_dois = set()
    if not os.path.exists(result_path):
        return exist_dois
    with open(result_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            exist_dois.update(data.keys())
    return exist_dois

def load_exist_data(path):
    exist_data = dict()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            exist_data.update(data)
    return exist_data
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
def main():
    # 突破性论文
    # with open('alt_disruption/reviwer1/data/breakthrough_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
    #     breakthrough_data=json.load(f)

    # breakthrough_id_list = list(breakthrough_data.keys())
    # print(f"需要处理的突破性论文数量: {len(breakthrough_id_list)}")
    # #诺奖论文
    # with open('alt_disruption/reviwer1/data/nobel_prize_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
    #     nobel_data=json.load(f)
    # nobel_id_list = list(nobel_data.keys())
    # print(f"需要处理的诺奖论文数量: {len(nobel_id_list)}")
    # id_list = set(breakthrough_id_list + nobel_id_list)
    # cited_by_counts twitter_user_counts
    exp_ids_set=set()
    with open('alt_disruption/reviwer1/data/breakthrough_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
        breakthrough_data=json.load(f)
    breakthrough_controls1_list = []
    for exp,controls in breakthrough_data.items():
        exp_ids_set.add(exp)
        breakthrough_controls1_list.extend(controls)
    print(f"需要处理的突破性论文数量: {len(breakthrough_controls1_list)}")
    
    #诺奖论文
    with open('alt_disruption/reviwer1/data/nobel_prize_with_controls_cited_by_counts.json','r',encoding='utf-8') as f:
        nobel_data=json.load(f)
    nobel_controls1_list = []
    for exp,controls in nobel_data.items():
        exp_ids_set.add(exp)
        nobel_controls1_list.extend(controls)
    print(f"需要处理的诺奖论文数量: {len(nobel_controls1_list)}")
    id_list = set(breakthrough_controls1_list + nobel_controls1_list)

    result_path = 'alt_disruption/reviwer1/new_data_results/control1_group_DI_and_its_variants.jsonl'
    exist_ids = load_exist_dois(result_path)
    id_to_refs, id_to_puby = get_papers_works(id_list)

    ids_to_process = [id for id in id_list if id not in exist_ids]
    print(f"总共需要处理的id数量：{len(id_list)},已经处理的id数量：{len(exist_ids)} 待处理 ID 数：{len(ids_to_process)}")

    
    for id in tqdm(ids_to_process, desc="计算 DI 指标"):
        if id not in id_to_refs or id not in id_to_puby:
            print(f"{id}没找到refs 或者是id没有论文发表时间")
            continue
        refs = id_to_refs[id]
        start_year = id_to_puby[id]
        if start_year is None:
            print(f"{id} 发表时间为空，跳过")
            continue
        time_span=2025-start_year+1
        id, result = compute_all_metrics(id, refs, id_to_puby, time_span)
        save_single_result(id, result, result_path)
    print(f"\n✅ 所有结果保存至：{result_path}")

if __name__ == '__main__':
    main()
