import json
import mysql.connector
from mysql.connector import pooling
from collections import defaultdict, Counter
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# 数据库配置
databases = {
    'host': 'YOUR_DB_HOST',
    'port': 'YOUR_MYSQL_PORT',
    'database': 'YOUR_DATABASE',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD'
}

# 全局连接池
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

# 全局引用缓存（避免重复查询）
GLOBAL_CITATION_CACHE = {}

def get_db_connection():
    """获取数据库连接（从连接池）"""
    return connection_pool.get_connection()

def get_batch_citations(dois):
    """批量获取多个DOI的引用信息（优先从缓存读取）"""
    if not dois:
        return {}
    
    # 分离已缓存和未缓存的DOIs
    uncached_dois = [doi.lower() for doi in dois if doi.lower() not in GLOBAL_CITATION_CACHE]
    cached_results = {doi: GLOBAL_CITATION_CACHE[doi.lower()] for doi in dois if doi.lower() in GLOBAL_CITATION_CACHE}
    
    # 只查询未缓存的数据
    if uncached_dois:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 分块查询（防止SQL语句过长）
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
                
                # 更新全局缓存
                for cited_doi, citing_doi, creation in results:
                    cited_doi_lower = cited_doi.lower()
                    if cited_doi_lower not in GLOBAL_CITATION_CACHE:
                        GLOBAL_CITATION_CACHE[cited_doi_lower] = {}
                    GLOBAL_CITATION_CACHE[cited_doi_lower][citing_doi] = creation
            
            # 合并缓存结果
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
    """按年份组织引用信息"""
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
    """加载论文发表年份数据"""
    path = 'alt_disruption/final_run_experiment/data/papers_2_puby.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_paper_to_refs():
    """加载论文参考文献数据"""
    path = 'alt_disruption/final_run_experiment/data/papers_2_refs_doi.json'
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compute_all_metrics(doi, refs, paper_to_puby, time_span):
    """计算所有指标：DI、DI5及其变体"""
    try:
        # 动态加载当前DOI及其参考文献的引用数据
        dois_to_fetch = [doi] + refs
        get_batch_citations(dois_to_fetch)  # 结果会自动更新到全局缓存
        
        # 获取所需数据
        start_year = paper_to_puby[doi]
        focal_citations = GLOBAL_CITATION_CACHE.get(doi.lower(), {})
        focal_puby = get_puby_citations(focal_citations)
        
        # 合并所有参考文献的引用数据
        all_refs_citations_dict = {}
        refs_citation_cts = Counter()
        """refs_citation_cts = Counter({
            "paperA": 2,  # 出现在 ref1 和 ref2 中
            "paperB": 1,
            "paperC": 1
        })"""
        for ref in refs:
            ref_citations = GLOBAL_CITATION_CACHE.get(ref.lower(), {})
            all_refs_citations_dict.update(ref_citations)
            refs_citation_cts.update(ref_citations.keys())
        
        ref_puby = get_puby_citations(all_refs_citations_dict)

        results = {}
        for offset in range(time_span):
            end_year = int(start_year) + offset
            
            # 收集各年份的引用
            focal_year_citations = set()
            ref_year_citations = set()
            for y in range(int(start_year), end_year + 1):
                y_str = str(y)
                focal_year_citations.update(focal_puby.get(y_str, []))
                ref_year_citations.update(ref_puby.get(y_str, []))

            # 计算基础集合
            i = focal_year_citations - ref_year_citations  # 仅被目标论文引用的
            j = focal_year_citations & ref_year_citations  # 被两者共同引用的
            k = ref_year_citations - focal_year_citations  # 仅被参考文献引用的
            
            # 基础计数
            ni = len(i)
            nj = len(j)
            nk = len(k)
            total = ni + nj + nk
            
            # DI相关指标
            di = (ni - nj) / total if total > 0 else None
            di_xing = ni / total if total > 0 else None
            di_jing = nj / total if total > 0 else None
            mdi = (ni + nj) * di if di is not None else None
            
            # DI5相关指标
            nj5 = len(set([c for c in j if refs_citation_cts[c] >= 5]))
            total5 = ni + nj5 + nk
            di5 = (ni - nj5) / total5 if total5 > 0 else None
            di5_xing = ni / total5 if total5 > 0 else None
            di5_jing = nj5 / total5 if total5 > 0 else None
            mdi5 = (ni + nj5) * di5 if di5 is not None else None
            
            results[str(offset)] = {
                'di': di,
                'di_xing': di_xing,
                'di_jing': di_jing,
                'mdi': mdi,
                'di5': di5,
                'di5_xing': di5_xing,
                'di5_jing': di5_jing,
                'mdi5': mdi5,
                'counts': {
                    'ni': ni,
                    'nj': nj,
                    'nk': nk,
                    'nj5': nj5,
                    'total': total,
                    'total5': total5
                }
            }
        
        return doi, results
    except Exception as e:
        print(f"处理 {doi} 时出错: {str(e)}")
        return doi, {"error": str(e)}

def load_handle_doi(path):
    """加载需要处理的DOI列表"""
    handle_dois = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if 'doi' in data:
                handle_dois.add(data['doi'].lower())
    return handle_dois

def load_exist_dois(result_path):
    """加载已处理的DOI列表"""
    processed = set()
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                processed.update(data.keys())
    except FileNotFoundError:
        pass
    return processed

def save_single_result(doi, result, save_path):
    """保存单条结果到文件"""
    try:
        with open(save_path, 'a', encoding='utf-8') as f:
            json.dump({doi: result}, f, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        print(f"保存结果时出错: {e}")

def load_processed_dois(result_path):
    """加载已处理的DOI列表"""
    
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            content=json.load(f)
    except FileNotFoundError:
        pass
    return content 


def main():
    # 初始化数据
    print("加载论文数据...")
    doi_to_refs = get_paper_to_refs()
    paper_to_puby = get_paper_to_puby()
    time_span = 12
    
    # 输入输出路径
    input_path = 'alt_disruption/final_run_experiment/data/control_papers_altmetric_counts.jsonl'
    result_path = 'alt_disruption/final_run_experiment/results/control_papers_DI_and_its_variants_new.jsonl'
    
    # 获取待处理DOIs
    all_dois = load_handle_doi(input_path)
    exist_dois = load_exist_dois(result_path)
    processed_path = 'alt_disruption/final_run_experiment/results/control_papers_integrated.json'
    
    # 加载已处理的DOI
    content = load_processed_dois(processed_path)
    processed_dois=set(content.keys())

    dois_to_process = [doi for doi in all_dois if doi.lower() not in exist_dois]
    print(f"总DOI数: {len(all_dois)}, 待处理DOI数: {len(dois_to_process)}")
    
    # 逐个处理DOI
    for doi in tqdm(dois_to_process, desc="处理DOIs"):
        # if doi not in doi_to_refs or doi not in paper_to_puby:
        #     continue
        if doi in processed_dois:
            save_single_result(doi, content[doi], result_path)
        # 计算指标
        else:
            doi_result = compute_all_metrics(
                doi=doi,
                refs=doi_to_refs[doi],
                paper_to_puby=paper_to_puby,
                time_span=time_span
            )
            
            # 保存结果
            save_single_result(doi, doi_result[1], result_path)
        
    print(f"处理完成！结果保存至: {result_path}")

if __name__ == '__main__':
    main()