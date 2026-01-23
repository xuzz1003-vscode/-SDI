import json
import requests
import time
from tqdm import tqdm
import pandas as pd
import os
from typing import List, Dict, Set, Optional
import mysql.connector
from mysql.connector import pooling
MYSQL_CONFIG = {
   
}

mysql_pool = pooling.MySQLConnectionPool(
    pool_name="openalex_pool",
    pool_size=10,
    pool_reset_session=False,
    **MYSQL_CONFIG
)

def get_mysql_conn():
    """获取 MySQL 连接"""
    return mysql_pool.get_connection()
def get_id_2_doi(ids):
    """
    输入：论文 ID 列表
    输出：{论文ID: doi}
    """
    ids=list(ids)
    ids_2_doi = {}

    if not ids:
        return ids_2_doi
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        chunk_size = 2000

        for i in tqdm(range(0, len(ids), chunk_size), desc="查询 dois"):
            chunk = ids[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = f"""
                SELECT id,simple_doi 
                FROM works
                WHERE id IN ({placeholders})
            """
            cursor.execute(query, chunk)
            results = cursor.fetchall()

            for id_, simple_doi in results:
                ids_2_doi[id_] = simple_doi
    except mysql.connector.Error as err:
        print(f"❌ doi查询错误: {err}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return ids_2_doi

def get_experimental_id(doi: str) -> Optional[Dict]:
    """获取单篇论文的详细信息"""
    try:
        search_url = f"https://api.openalex.org/works?filter=doi:{doi}&per-page=1"
        response = requests.get(search_url)
        data = response.json().get('results', [])
        if not data:
            print(f"⚠️ 没找到 DOI: {doi}")
            return None
        result = data[0]
        return {
            'id': result.get('id'),
            'primary_topic_id': result['primary_topic']['id'].split('/')[-1],
            'publication_year': result['publication_year'],
            'paper_type': result['type'],
            'cited_by_count': result['cited_by_count'],
            'doi': result['doi'],
            'referenced_works_count': result.get('referenced_works_count', 0),
            'referenced_works': result.get('referenced_works', []),
            'related_works': result.get('related_works', [])
        }
    except Exception as e:
        print(f"❌ 错误处理 DOI: {doi} -> {e}")
        return None
    

def get_control_papers(control_data: Dict, experimental_doi: str) -> List[Dict]:
    """
    获取控制组论文：
    - 不限制数量
    - 同 publication_year / paper_type / primary_topic
    - referenced_works_count >= 10
    """
    papers = []
    cursor = '*'

    while cursor:
        try:
            works_url = (
                f"https://api.openalex.org/works"
                f"?filter=publication_year:{control_data['publication_year']},"
                f"type:{control_data['paper_type']},"
                f"primary_topic.id:{control_data['primary_topic_id']}"
                f"&sort=cited_by_count:desc"
                f"&per-page=200&cursor={cursor}"
            )
            response = requests.get(works_url)
            data = response.json()

            batch = data.get('results', [])
            if not batch:
                break

            for paper in batch:
                doi = paper.get('doi')
                refs_count = paper.get('referenced_works_count', 0)

                # 过滤条件
                if (
                    doi
                    and doi != experimental_doi
                    and refs_count >= 10
                ):
                    papers.append({
                        'id': paper.get('id'),
                        'doi': doi,
                        'title': paper.get('display_name'),
                        'cited_by_count': paper.get('cited_by_count', 0),
                        'publication_year': paper.get('publication_year'),
                        'referenced_works_count': refs_count,
                        'referenced_works': paper.get('referenced_works', [])
                    })

            cursor = data.get('meta', {}).get('next_cursor')
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 获取控制组时错误: {e}")
            break

    return papers

def process_with_resume(
    all_items: Set[str],
    output_path: str,
    process_func: callable,
    batch_size: int = 10,
    delay: float = 0.5
) -> Dict:
    """
    支持断点续跑的处理函数（直接操作输出文件）
    
    参数:
        all_items: 所有需要处理的项集合
        output_path: 输出文件路径（同时用于断点续跑）
        process_func: 处理单个项的函数
        batch_size: 每处理多少项后保存一次
        delay: 每次API调用后的延迟(秒)
    """
    # 初始化结果和已处理DOIs
    processed_results = []
    processed_dois = set()
    
    # 如果输出文件已存在，加载已有结果
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                processed_results = json.load(f)
                processed_dois = {r['experimental_doi'] for r in processed_results}
            print(f"✅ 从输出文件恢复，已处理 {len(processed_dois)} 篇论文")
        except Exception as e:
            print(f"⚠️ 加载输出文件失败: {e}")
            # 如果文件损坏，从零开始
            processed_results = []
            processed_dois = set()

    # 准备剩余需要处理的项
    remaining_dois = [doi for doi in all_items if doi not in processed_dois]
    print(f"📊 总论文数: {len(all_items)}，已处理: {len(processed_dois)}，待处理: {len(remaining_dois)}")

    if not remaining_dois:
        print("🎉 所有论文已处理完成")
        return {
            'all_results': processed_results,
            'all_control_dois': set().union(*[set(c['doi'] for c in r['controls']) for r in processed_results])
        }

    # 处理剩余项
    all_control_dois = set().union(*[set(c['doi'] for c in r['controls']) for r in processed_results])
    
    try:
        for i, doi in enumerate(tqdm(remaining_dois, desc="处理进度")):
            experimental_data = get_experimental_id(doi)
            if experimental_data is None:
                continue
                
            controls = get_control_papers(experimental_data, doi)
            result = {
                'experimental_doi': doi,
                'experimental_id': experimental_data.get('id'),
                'controls': controls
            }
            processed_results.append(result)
            all_control_dois.update([c['doi'] for c in controls])

            # 定期保存结果
            if (i + 1) % batch_size == 0 or i == len(remaining_dois) - 1:
                _save_results(output_path, processed_results)
            
            time.sleep(delay)
            
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        print("💾 正在保存已处理的数据...")
        _save_results(output_path, processed_results)
        raise

    print(f"✅ 结果已保存至 {output_path}")
    return {
        'all_results': processed_results,
        'all_control_dois': all_control_dois
    }

def _save_results(path: str, data: List[Dict]) -> None:
    """安全保存结果到文件"""
    # 使用临时文件确保原子性操作
    temp_path = path + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 替换原文件
    if os.path.exists(path):
        os.remove(path)
    os.rename(temp_path, path)



def main():
    # experimental_dois = open_focal_openalex_file()
    output_path = "/breakthrough_controls_new.json"

    with open('/breakthrough_papers_refs_with_twitter.json', 'r') as f:
        ids_2_refs = json.load(f)
    ids=ids_2_refs.keys()
    experimental_dois=list(get_id_2_doi(ids).values())
    # 定义单篇论文处理函数
    def process_single_paper(doi: str) -> Dict:
        experimental_data = get_experimental_id(doi)
        if experimental_data is None:
            return {'experimental_doi': doi,'experimental_id':experimental_data.get('id'), 'controls': []}
        controls = get_control_papers(experimental_data, doi)
        return {'experimental_doi': doi,'experimental_id':experimental_data.get('id'), 'controls': controls}
    
    # 调用处理函数
    result = process_with_resume(
        all_items=experimental_dois,
        output_path=output_path,
        process_func=process_single_paper,
        batch_size=5,
        delay=0.5
    )
    
    print(f"\n✅ 完成！共处理 {len(result['all_results'])} 篇实验论文")
    print(f"🧹 控制组去重后共 {len(result['all_control_dois'])} 篇独立论文")

if __name__ == "__main__":
    main()