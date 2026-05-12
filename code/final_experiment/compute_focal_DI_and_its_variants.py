import json
import mysql.connector
from collections import defaultdict, Counter
from tqdm import tqdm

# 数据库配置
databases = {
    'host': 'YOUR_DB_HOST',
    'port': 'YOUR_MYSQL_PORT',
    'database': 'YOUR_DATABASE',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD'
}

def get_db_connection():
    return mysql.connector.connect(
        host=databases['host'],
        port=databases['port'],
        user=databases['user'],
        password=databases['password'],
        database=databases['database']
    )

def get_citations(doi):
    """获取论文的引用信息"""
    citations = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT citing_doi, creation FROM opencitations.citation_data_with_doi WHERE LOWER(cited_doi)=LOWER(%s)", (doi,))
        results = cursor.fetchall()
        if results:
            for result in results:
                citations[result[0]] = result[1]
    except mysql.connector.Error as err:
        print(f"[get_citations] 数据库错误: {err}")
        return citations
    finally:
        if conn.is_connected():
            conn.close()
    return citations

def get_puby_citations(citations_dict):
    """按年份组织引用信息"""
    citation_puby = defaultdict(list)
    if not citations_dict:
        return citation_puby

    for doi, puby in tqdm(citations_dict.items(), desc="查询 pub_date"):
        try:
            year = puby.split('-')[0] if puby else None
            citation_puby[year].append(doi)
        except Exception:
            print(f"[get_puby_citations] 查询 {doi} 出错")
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
    start_year = paper_to_puby[doi]
    
    # 获取目标论文的引用
    focal_citations = get_citations(doi)
    focal_puby = get_puby_citations(focal_citations)
    
    # 获取参考文献的引用
    all_refs_citations_dict = {}
    for ref in refs:
        ref_citations = get_citations(ref)
        all_refs_citations_dict.update(ref_citations)
    
    ref_puby = get_puby_citations(all_refs_citations_dict)
    refs_citation_cts = Counter(all_refs_citations_dict.keys())

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

        # 计算基本集合
        i = focal_year_citations - ref_year_citations  # 仅被目标论文引用的
        j = focal_year_citations & ref_year_citations  # 被两者共同引用的
        k = ref_year_citations - focal_year_citations  # 仅被参考文献引用的
        i_j_k = focal_year_citations | ref_year_citations  # 所有引用
        
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
        
        # 保存结果
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

def load_processed_dois(result_path):
    """加载已处理的DOI列表"""
    
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            content=json.load(f)
    except FileNotFoundError:
        pass
    return content 

def save_single_result(doi, result, save_path):
    """保存单条结果到文件"""
    try:
        with open(save_path, 'a', encoding='utf-8') as f:
            json.dump({doi: result}, f, ensure_ascii=False)
            f.write('\n')
            f.flush()
    except Exception as e:
        print(f"保存结果时出错: {e}")

def load_handle_doi(path):
    handle_dois=set()
    with open(path,'r') as f:
        for line in f:
            line=json.loads(line)
            handle_dois.add(line.get('doi').lower())
    return handle_dois

def main():
    # 初始化数据
    doi_to_refs = get_paper_to_refs()
    paper_to_puby = get_paper_to_puby()
    time_span = 12
    
    # 结果文件路径
    result_path='alt_disruption/final_run_experiment/results/experimental_papers_DI_and_its_variants.jsonl'
    processed_path = 'alt_disruption/final_run_experiment/results/focal_papers_integrated.json'
    
    # 加载已处理的DOI
    content = load_processed_dois(processed_path)
    processed_dois=set(content.keys())
    dois=load_handle_doi('alt_disruption/final_run_experiment/data/experimental_groups_social_counts.json'
                         )
    need_dois=set(dois)-set(processed_dois)
    print(len(need_dois))
    # 计算并保存结果
    for doi in tqdm(dois, desc="计算指标"):
        tqdm.write(f'正在处理{doi}')
        if doi in processed_dois:
            save_single_result(doi, content[doi], result_path)
            
        else:
            try:
                refs = doi_to_refs[doi]
                doi, results = compute_all_metrics(doi, refs, paper_to_puby, time_span)
                save_single_result(doi, results, result_path)
                tqdm.write(f"✅ 完成 {doi}")
            except Exception as e:
                tqdm.write(f"❌ 处理 {doi} 出错：{e}")
                # 保存错误信息以便排查
                save_single_result({doi: {"error": str(e)}}, result_path)

    print(f"\n所有指标已保存至：{result_path}")

if __name__ == '__main__':
    main()