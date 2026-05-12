import json
import numpy as np
from datetime import datetime
import itertools
from tqdm import tqdm
import os
from collections import Counter

def get_paper_to_puby():
    """获取论文DOI到发表年份的映射"""
    path = 'alt_disruption/final_run_experiment/data/papers_2_puby.json'
    with open(path, 'r', encoding='utf-8') as f:
        paper_to_puby = json.load((f))
    return paper_to_puby

def get_paper_to_refs():
    """获取论文DOI到其参考文献列表的映射"""
    path = 'alt_disruption/final_run_experiment/data/papers_2_refs_doi.json'
    with open(path, 'r', encoding='utf-8') as f:
        paper_to_refs = json.load((f))
    return paper_to_refs

def get_twitter_data(twitter_path):
    """
    从Twitter数据文件中提取论文的提及信息
    
    返回格式:
    {
        doi: {
            author_id1: [time1, time2...],
            author_id2: [time1, time2...],
            ...
        }
    }
    """
    user_mentions = dict()
    with open(twitter_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                line_data = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            doi = line_data.get('doi')
            if not doi:
                continue            

            author_id_dict = dict()
            if not line_data['tweets']:
                user_mentions[doi] = {}
                continue

            for each in line_data['tweets']:
                author_id = each['author_handle']
                time_str = each['time']
                try:
                    time_obj = datetime.strptime(time_str, "%d %b %Y %I:%M%p")
                except ValueError:
                    try:
                        time_obj = datetime.strptime(time_str, "%d %b %Y")
                    except ValueError:
                        continue

                formatted_date = time_obj.strftime("%Y")  # 只保留年份
                if author_id not in author_id_dict:
                    author_id_dict[author_id] = [formatted_date]
                else:
                    author_id_dict[author_id].append(formatted_date)

            user_mentions[doi] = author_id_dict

    return user_mentions

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

    # 如果没有参考文献被提及，设置所有指标为None
    if not ref_mention_times:
        return {focal_paper: {}}
    
    # 找到最晚的提及时间并计算时间间隔(年)
    max_mention_time = max(ref_mention_times)
    time_gap = int(max_mention_time) - puby_year 
    
    for i in range(time_gap + 1):
        # 计算提及核心论文的用户
        focal_user_ids = set()
        if focal_paper in user_mentions:
            for user_id, mention_times in user_mentions[focal_paper].items():
                if any(0 <= int(time) - puby_year <= i for time in mention_times):
                    focal_user_ids.add(user_id)

        # 计算提及参考文献的用户(核心论文发表后)
        ref_user_ids = []# 主要用来计算j，需要核心文章发表后提及的才算
        # all_ref_user_ids = set()  # 用于计算k
        for user_id, mention_times in ref_dates_by_user.items():
            for time in mention_times:
                year_diff = int(time) - puby_year
                if year_diff >= 0 and year_diff <= i:
                    ref_user_ids.append(user_id)
                # if year_diff <= i:  # 包括核心论文发表前的提及
                #     all_ref_user_ids.add(user_id)
                #     break

        # 计算各种指标所需的计数
        i_set= set(focal_user_ids) - set(ref_user_ids)  # 仅提及核心论文的用户数
        j_set= set(ref_user_ids) & set(focal_user_ids) # 同时提及核心论文和参考文献的用户数
        k_set= set(ref_user_ids) - set(focal_user_ids) # 仅提及参考文献的用户数
        ni = len(i_set) 
        nj = len(j_set)  
        nk = len(k_set)  
        total = ni + nj + nk  # 总用户数

        # 计算DI5相关指标
        #统计提及参考文献的userid个数，为了方便统计di5
        ref_user_ids_count=Counter(ref_user_ids)
        print(ref_user_ids_count)
        
        # 既提及核心又提及参考文献的用户中，提及次数>=5的用户
        j5_user_ids_set = set([user_id for user_id in j_set if ref_user_ids_count[user_id] >= 5])
        
        nj5 = len(j5_user_ids_set)
        total5 = ni + nj5 + nk
        
        # 计算SDI相关指标
        sdi = (ni - nj) / total if total > 0 else None
        sdi_xing = ni / total if total > 0 else None
        sdi_jing = nj / total if total > 0 else None
        msdi = (ni + nj) * sdi if sdi is not None else None
        
        # 计算DI5相关指标
        sdi5 = (ni - nj5) / total5 if total5 > 0 else None
        sdi5_xing = ni / total5 if total5 > 0 else None
        sdi5_jing = nj5 / total5 if total5 > 0 else None
        mdi5 = (ni + nj5) * sdi5 if sdi5 is not None else None
        
        # 存储当前年份的所有指标
        result[i] = {
            'sDI': float(sdi) if sdi is not None else None,
            'sDI_xing': float(sdi_xing) if sdi_xing is not None else None,
            'sDI_jing': float(sdi_jing) if sdi_jing is not None else None,
            'msDI': float(msdi) if msdi is not None else None,
            'sDI5': float(sdi5) if sdi5 is not None else None,
            'sDI5_xing': float(sdi5_xing) if sdi5_xing is not None else None,
            'sDI5_jing': float(sdi5_jing) if sdi5_jing is not None else None,
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

def load_handle_doi(path):
    """加载需要处理的DOI列表"""
    handle_dois = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            handle_dois.add(data.get('doi'))
    return handle_dois


def main():
    """主函数，计算所有论文的指标并保存结果"""
    # 加载Twitter提及数据
    twitter_path = 'alt_disruption/control_group_two_new/data/all_papers_social_data.jsonl'
    user_mentions = get_twitter_data(twitter_path)

    # 加载论文发表年份和参考文献数据
    fpid_to_puby = get_paper_to_puby()
    fpid_and_fr_dict = get_paper_to_refs()

    # 设置结果保存路径
    save_path = 'alt_disruption/control_group_two_new/results/control_papers_SDI_and_its_variants_group2.jsonl'

    # 检查已处理过的论文，避免重复处理
    processed = set()
    if os.path.exists(save_path):
        with open(save_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed.update(data.keys())
                except:
                    continue
    dois = load_handle_doi('alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl')

    # 处理每篇论文
    with open(save_path, 'a', encoding='utf-8') as f_out:
        for doi in tqdm(dois, desc="计算指标"):
            if doi in processed:
                continue
            puby = int(fpid_to_puby[doi])
            refs_of_focal_paper=fpid_and_fr_dict[doi]
            paper_metrics = compute_metrics(doi, puby, refs_of_focal_paper, user_mentions)
            f_out.write(json.dumps(paper_metrics, ensure_ascii=False) + '\n')
            f_out.flush()

if __name__ == '__main__':
    main()