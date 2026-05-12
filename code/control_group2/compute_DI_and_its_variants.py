import json
import mysql.connector
from mysql.connector import pooling
from collections import defaultdict, Counter
from tqdm import tqdm
import os

# ======= 写死路径：你只改这两个就行 ========
input_path = 'alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl'
result_path = 'alt_disruption/control_group_two_new/results/control_papers_DI_and_its_variants_group2.jsonl'
exist_result_path1='alt_disruption/control_group_two/resluts/control_papers_DI_and_its_variants_group2.jsonl'
exist_result_path='alt_disruption/control_group_one/results/control_papers_DI_and_its_variants.jsonl'
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

GLOBAL_CITATION_CACHE = {}

def get_db_connection():
    return connection_pool.get_connection()

def get_batch_citations(dois):
    if not dois:
        return {}
    uncached_dois = [doi.lower() for doi in dois if doi.lower() not in GLOBAL_CITATION_CACHE]
    cached_results = {doi: GLOBAL_CITATION_CACHE[doi.lower()] for doi in dois if doi.lower() in GLOBAL_CITATION_CACHE}
    if uncached_dois:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            chunk_size = 2000
            for i in range(0, len(uncached_dois), chunk_size):
                chunk = uncached_dois[i:i + chunk_size]
                placeholders = ','.join(['%s'] * len(chunk))
                query = f"""
                SELECT cited_doi, citing_doi, creation 
                FROM opencitations.citation_data_with_doi 
                WHERE LOWER(cited_doi) IN ({placeholders})
                """
                cursor.execute(query, chunk)
                results = cursor.fetchall()
                for cited_doi, citing_doi, creation in results:
                    cited_doi_lower = cited_doi.lower()
                    if cited_doi_lower not in GLOBAL_CITATION_CACHE:
                        GLOBAL_CITATION_CACHE[cited_doi_lower] = {}
                    GLOBAL_CITATION_CACHE[cited_doi_lower][citing_doi] = creation
            cached_results.update({
                doi: GLOBAL_CITATION_CACHE.get(doi.lower(), {})
                for doi in dois
            })
        except mysql.connector.Error as err:
            print(f"[get_batch_citations] 数据库错误: {err}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                conn.close()
    return cached_results

def get_puby_citations(citations_dict):
    citation_puby = defaultdict(list)
    for citing_doi, creation in citations_dict.items():
        try:
            year = creation.split('-')[0] if creation else None
            if year:
                citation_puby[year].append(citing_doi)
        except Exception:
            continue
    return citation_puby

def get_paper_to_puby():
    path = 'alt_disruption/final_run_experiment/data/papers_2_puby.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_paper_to_refs():
    path = 'alt_disruption/final_run_experiment/data/papers_2_refs_doi.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compute_all_metrics(doi, refs, paper_to_puby, time_span):
    try:
        dois_to_fetch = [doi] + refs
        get_batch_citations(dois_to_fetch)
        start_year = paper_to_puby[doi]
        focal_citations = GLOBAL_CITATION_CACHE.get(doi.lower(), {})
        focal_puby = get_puby_citations(focal_citations)
        all_refs_citations_dict = {}
        refs_citation_cts = Counter()
        # 获取参考文献的引用
        for ref in refs:
            ref_citations = GLOBAL_CITATION_CACHE.get(ref.lower(), {})
            for citing_doi in ref_citations:
                refs_citation_cts[citing_doi] += 1
                all_refs_citations_dict[citing_doi] = ref_citations[citing_doi]

        ref_puby = get_puby_citations(all_refs_citations_dict)
        results = {}
         # 收集各年份的引用
        for offset in range(time_span):
            end_year = int(start_year) + offset
            focal_year_citations = set()
            ref_year_citations = set()
            for y in range(int(start_year), end_year + 1):
                y_str = str(y)
                focal_year_citations.update(focal_puby.get(y_str, []))
                ref_year_citations.update(ref_puby.get(y_str, []))

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
        return doi, results
    except Exception as e:
        print(f"[compute_all_metrics] 处理 {doi} 出错: {str(e)}")
        return doi, {"error": str(e)}

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

def main():
    doi_to_refs = get_paper_to_refs()
    paper_to_puby = get_paper_to_puby()
    time_span = 12
    all_dois = load_handle_doi(input_path)
    exist_dois = load_exist_dois(result_path)
    dois_to_process = [doi for doi in all_dois if doi not in exist_dois]
    print(f"总共需要处理的doi数量：{len(all_dois)},已经处理的doi数量：{len(exist_dois)} 待处理 DOI 数：{len(dois_to_process)}")
    exist_data2=load_exist_data(exist_result_path)
    exist_data1=load_exist_data(exist_result_path1)
    exist_data=dict(exist_data1,**exist_data2)
    for doi in tqdm(dois_to_process, desc="计算 DI 指标"):
        if doi not in doi_to_refs or doi not in paper_to_puby:
            print(f"{doi}没找到refs 或者是doi没有论文发表时间")
            continue
        if doi in exist_data:
            print(f"{doi}在控制组1的论文中")
            result=exist_data[doi]
            save_single_result(doi, result, result_path)
        else:
            print(f"{doi}不在控制组1的论文中")
            refs = doi_to_refs[doi]
            doi, result = compute_all_metrics(doi, refs, paper_to_puby, time_span)
            save_single_result(doi, result, result_path)
    print(f"\n✅ 所有结果保存至：{result_path}")

if __name__ == '__main__':
    main()
