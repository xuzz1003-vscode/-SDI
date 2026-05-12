import pandas as pd
import numpy as np
from compare_control_focal_papers_DI_8 import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe, get_all_last_metrics
import json
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from clickhouse_driver import Client
from datetime import datetime
from compute_DI_and_its_variants_7 import get_batch_papers_puby
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

def get_twitter_count(ids, batch_size=500):
    """
    按论文发表年计算 Twitter 活动：
    - tweet 总数（按 gap_year）
    - unique tweeter 数（按 gap_year）

    Parameters
    ----------
    ids : iterable
        论文 id（doi 或 openalex id）
    batch_size : int
        ClickHouse IN 查询的 batch 大小

    Returns
    -------
    id_2_puby_tweets_count : dict
        {id: {gap_year: tweet_count}}
    id_2_puby_unique_user_mentions_count : dict
        {id: {gap_year: unique_user_count}}
    """

    # ========= 0. 预处理 =========
    ids = list(set(ids))  # 必须去重，避免 SQL 过长
    if not ids:
        return {}, {}

    # id -> publication year
    id_to_puby = get_batch_papers_puby(ids)

    id_2_puby_tweets_count = {}
    id_2_puby_unique_user_mentions_count = {}

    client = make_client(params_clickhouse_openalex)

    try:
        # ========= 1. batch 查询 =========
        for i in range(0, len(ids), batch_size):
            id_batch = ids[i:i + batch_size]
            if not id_batch:
                continue

            sql_query = (
                "SELECT id, tweets "
                "FROM disruption_papers.twitter_data_new "
                "WHERE id IN {}".format(tuple(id_batch))
            )

            results = client.execute(sql_query)

            # ========= 2. 逐篇论文处理 =========
            for pid, tweets in results:
                puby = id_to_puby.get(pid)
                if puby is None:
                    continue

                puby_tweets_count = {}
                puby_unique_user_mentions_count = {}

                if tweets:
                    try:
                        tweets_list = json.loads(tweets)
                    except Exception:
                        tweets_list = []

                    for each in tweets_list:
                        author_id = each.get("author_handle")
                        time_str = each.get("time")
                        if not time_str:
                            continue

                        # 时间解析（两种格式）
                        try:
                            time_obj = datetime.strptime(time_str, "%d %b %Y %I:%M%p")
                        except ValueError:
                            try:
                                time_obj = datetime.strptime(time_str, "%d %b %Y")
                            except ValueError:
                                continue

                        gap_year = int(time_obj.year) - int(puby)
                        if gap_year < 0:
                            continue

                        # tweet 总数
                        puby_tweets_count[gap_year] = puby_tweets_count.get(gap_year, 0) + 1

                        # unique tweeter
                        puby_unique_user_mentions_count.setdefault(gap_year, set())
                        if author_id:
                            puby_unique_user_mentions_count[gap_year].add(author_id.lower())

                # set → count
                puby_unique_user_mentions_count = {
                    k: len(v) for k, v in puby_unique_user_mentions_count.items()
                }

                id_2_puby_tweets_count[pid] = puby_tweets_count
                id_2_puby_unique_user_mentions_count[pid] = puby_unique_user_mentions_count

    finally:
        client.disconnect()

    return id_2_puby_tweets_count, id_2_puby_unique_user_mentions_count

def twitter_dicts_to_panel_df(
    id_2_puby_tweets_count,
    id_2_puby_unique_user_mentions_count,
    max_gap=None
):
    rows = []

    all_ids = set(id_2_puby_tweets_count) | set(id_2_puby_unique_user_mentions_count)

    for pid in all_ids:
        tweet_dict = id_2_puby_tweets_count.get(pid, {})
        user_dict = id_2_puby_unique_user_mentions_count.get(pid, {})

        # 当前论文的最大 gap
        local_max_gap = max(
            tweet_dict.keys() | user_dict.keys(),
            default=0
        )

        # 如果传了 max_gap，用统一上限（推荐做 robustness）
        final_max_gap = max_gap if max_gap is not None else local_max_gap

        for gap_year in range(0, final_max_gap + 1):
            rows.append({
                "DOI": pid,
                "Year": gap_year,
                "tweet_count": tweet_dict.get(gap_year, 0),
                "unique_user_count": user_dict.get(gap_year, 0)
            })

    df_panel = pd.DataFrame(rows)
    return df_panel

def get_altmetric_counts(ids, batch_size=500):
    client = make_client(params_clickhouse_openalex)
    all_results = []

    ids = list(set(ids))  # 顺手去重，能少一半 query size

    try:
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i+batch_size]
            sql = f"""
            SELECT id, facebook_count, blogs_count, google_users_count, news_count,
                   tweets_count, wikipedia_count, citation_count, altmetric_attention_score
            FROM disruption_papers.altmetric_counts_data
            WHERE id IN {tuple(batch)}
            """
            res = client.execute(sql)
            all_results.extend(res)

        df = pd.DataFrame(
            all_results,
            columns=[
                'id', 'facebook_count', 'blogs_count', 'google_users_count',
                'news_count', 'tweets_count', 'wikipedia_count',
                'citation_count', 'altmetric_attention_score'
            ]
        )
        df.rename(columns={'id': 'DOI'}, inplace=True)
        return df

    finally:
        client.disconnect()

def get_year_data(time,df):
    year_to_data = {year: group for year, group in df.groupby('Year')}
    data=year_to_data[time]
    del data['Year']
    return data

# def compute_rank(df, percentile=0.1):
#     """
#     对数值列计算rank，并统计前percentile中label=1（focal）的比例。

#     参数：
#         df: 包含数据的DataFrame，必须有'label'列（1=focal, 0=control）
#         percentile: 统计前多少比例的数据（默认前10%）

#     返回：
#         results: 字典 {列名: (前percentile中focal的数量, 前percentile总数量)}
#     """
#     # 确保label列存在
#     if 'label' not in df.columns:
#         raise ValueError("DataFrame必须包含'label列（1=focal, 0=control）")

#     # 获取数值列（排除DOI和label）
#     numeric_cols = [col for col in df.columns 
#                    if col not in ['DOI', 'label'] 
#                    and pd.api.types.is_numeric_dtype(df[col])]
#     results = {}
#     for col in numeric_cols:
#         # 计算排名（降序，值越大排名越高）
#         df[f'rank_{col}'] = df[col].rank(ascending=False, method='min')
#         # print(df)
#         # 前percentile的阈值
#         threshold = int(len(df) * percentile)
#         top_df = df[df[f'rank_{col}'] <= threshold]
#         # 统计focal数量
#         focal_count = top_df['label'].sum()
#         total_count = len(top_df)
#         results[col] = focal_count
#         print(f"{col}: 前{percentile*100:.0f}%中 {focal_count}/{total_count} 是focal")
#     print(results)
#     return results
def compute_rank(df, percentile=0.1):
    """
    对数值列进行排序，并统计前percentile（固定数量）中 label=1 的数量
    """
    if 'label' not in df.columns:
        raise ValueError("DataFrame必须包含'label'列（1=focal, 0=control）")

    numeric_cols = [
        col for col in df.columns
        if col not in ['DOI', 'label']
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    results = {}
    k = int(len(df) * percentile)

    for col in numeric_cols:
        top_df = df.sort_values(col, ascending=False).head(k)

        focal_count = top_df['label'].sum()
        total_count = len(top_df)

        results[col] = focal_count
        print(f"{col}: 前{percentile*100:.0f}%中 {focal_count}/{total_count} 是 focal")

    return results

def plot_rank_counts(results_dict, percentile):
    """
    绘制柱状图，显示各指标前percentile中focal论文的数量
    
    参数：
        results_dict: 字典格式 {指标名: focal_count}
        time: 用于标题的时间标识
    """
    groups_order = [
        'DI', 'DI5', 'mDI', 'DI_xing',          # 第一组（DI相关）
        'SDI', 'SDI5', 'mSDI', 'SDI_xing',
        'citations','facebook_count', 'blogs_count', 'google_users_count', 'news_count',
        'tweets_count', 'wikipedia_count', 'altmetric_attention_score'     # 第二组（SDI相关）
    ]
    plt.rcParams['mathtext.fontset'] = 'stix'  # 使用 STIX 字体（类似 Times New Roman）
    plt.rcParams['font.family'] = 'Times New Roman'  # 设置普通文本字体
    plt.rcParams['font.size'] = 13  # 可选：设置字体大小

    # 按分组顺序提取数据
    counts = [results_dict.get(col, 0) for col in groups_order]
    labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$', r'$\mathrm{DI^{*}}$',  
          r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$', r'$\mathrm{SDI^{*}}$', 
          r'$\mathrm{CCs}$', r'$\mathrm{FCs}$', r'$\mathrm{BCs}$', r'$\mathrm{GACs}$', r'$\mathrm{NCs}$', r'$\mathrm{TACs}$', 
          r'$\mathrm{WCs}$', r'$\mathrm{AAS}$'
          ]

    #  专业配色方案（使用色盲友好的调色板）
    # group_colors = [
    #     '#4E79A7', '#4E79A7', '#4E79A7', '#4E79A7', '#4E79A7',  # 第一组：蓝色系
    #     '#F28E2B', '#F28E2B', '#F28E2B', '#F28E2B', '#F28E2B',  # 第二组：橙色系
    #     '#59A14F', '#59A14F', '#59A14F', '#59A14F',             # 第三组：绿色系
    #     '#59A14F', '#59A14F', '#59A14F'
    # ]
    
    # group_colors = [
    # '#3A5FCD', '#4682B4', '#5F9EA0', '#7AC5CD', '#8DB6CD',  # 蓝色系渐变
    # '#FF8C00', '#FFA500', '#FFB90F', '#FFC125', '#FFD700',  # 橙色/金色渐变
    # '#2E8B57', '#3CB371', '#66CDAA', '#7FFFD4',            # 绿色系渐变
    # '#98FB98', '#90EE90', '#00FA9A'
    # ]
    group_colors = [ "#745FEC"] * 4 + ["#C81808B7"] * 4 +['#59A14F'] * 8

    # 位置设置（保持分组间距）
    x_pos = list(range(len(groups_order)))
    for i in [4, 8]:  # 在组间添加间距
        x_pos[i:] = [x + 0.5 for x in x_pos[i:]]
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(6, 4.5))

    bars = plt.bar(x_pos, counts, color=group_colors, width=0.9)
    plt.rcParams['hatch.color'] = '#555555'  # 统一设置为灰色

    # 设置柱状图样式
    for i, bar in enumerate(bars):
        if i < 4:          # 第一组
            bar.set_edgecolor('#F8F8F8')  # 先设置边缘颜色
            bar.set_hatch('/')
        elif i < 8:       # 第二组
            bar.set_edgecolor('#F8F8F8')
            bar.set_hatch('\\')
        else:              # 第三组
            bar.set_edgecolor('#F8F8F8')
            bar.set_hatch('x')

    # 添加数值标签
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval ,
                str(int(yval)), ha='center', va='bottom', 
                 color='black', fontsize=14)
    legend_elements = [
        Patch(facecolor="#745FEC", edgecolor='#F8F8F8', hatch='/', 
              label=r'DI-based metrics of $\mathcal{A} \cup \mathcal{C}$'),
        Patch(facecolor="#C81808B7", edgecolor='#F8F8F8', hatch='\\', 
              label=r'SDI-based metrics of $\mathcal{A} \cup \mathcal{C}$'),
        Patch(facecolor='#59A14F', edgecolor='#F8F8F8', hatch='x', 
              label=r'Other metrics of $\mathcal{A} \cup \mathcal{C}$')
        
    ]
    ax.legend(handles=legend_elements, fontsize=10)

    # 图表装饰
    plt.xticks(ticks=x_pos, labels=labels, rotation=0,fontsize=8)
    plt.title(f'Top {int(percentile*100)}%', fontsize=16)
    plt.ylabel('number of experimental papers', fontsize=14)
    plt.ylim(0, max(counts)*1.3)
    # plt.ylim(0, 50)
    plt.tight_layout()
    plt.savefig(f'alt_disruption/reviwer1/new_data_results/figs/count_of_ranked_papers_{percentile}.png',dpi=300,bbox_inches='tight')

def plot_rank_counts_time(results_dict, time, percentile):
    """
    绘制柱状图，显示各指标前percentile中focal论文的数量
    
    参数：
        results_dict: 字典格式 {指标名: focal_count}
        time: 用于标题的时间标识
    """
    groups_order = [
        'DI', 'DI5', 'mDI', 'DI_xing',          # 第一组（DI相关）
        'SDI', 'SDI5', 'mSDI', 'SDI_xing','tweet_count','unique_user_countTAC'

    ]
    plt.rcParams['mathtext.fontset'] = 'stix'  # 使用 STIX 字体（类似 Times New Roman）
    plt.rcParams['font.family'] = 'Times New Roman'  # 设置普通文本字体
    plt.rcParams['font.size'] = 13  # 可选：设置字体大小

    # 按分组顺序提取数据
    counts = [results_dict.get(col, 0) for col in groups_order]
    labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$', r'$\mathrm{DI^{*}}$',
          r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$', r'$\mathrm{SDI^{*}}$','TAC','UTAC'

         
          ]

    group_colors = [ "#745FEC"] * 4 + ["#C81808B7"] * 4 

    # 位置设置（保持分组间距）
    # x_pos = list(range(len(groups_order)))
    # for i in [4, 8]:  # 在组间添加间距
    #     x_pos[i:] = [x - 0.1 for x in x_pos[i:]]
    
    # x_pos = list(range(len(groups_order)))
    x_pos = [0, 0.7, 1.4, 2.1,   3, 3.7, 4.4, 5.1,6,6.8]


    # 只在两组之间加一点点间距
    x_pos[4:] = [x + 0.2 for x in x_pos[4:]]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    bars = plt.bar(x_pos, counts, color=group_colors, width=0.5)
    plt.rcParams['hatch.color'] = '#555555'  # 统一设置为灰色

    # 设置柱状图样式
    for i, bar in enumerate(bars):
        if i < 4:          # 第一组
            bar.set_edgecolor('#F8F8F8')  # 先设置边缘颜色
            bar.set_hatch('/')
        elif i < 8:       # 第二组
            bar.set_edgecolor('#F8F8F8')
            bar.set_hatch('\\')
        else:              # 第三组
            bar.set_hatch('x')

    # 添加数值标签
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval ,
                str(int(yval)), ha='center', va='bottom', 
                 color='black', fontsize=14)
    legend_elements = [
        Patch(facecolor="#745FEC", edgecolor='#F8F8F8', hatch='/', 
              label=r'DI-based metrics of $\mathcal{B} \cup \mathcal{C}_\mathcal{B}$'),
        Patch(facecolor="#C81808B7", edgecolor='#F8F8F8', hatch='\\', 
              label=r'SDI-based metrics of $\mathcal{B} \cup \mathcal{C}_\mathcal{B}$')
    ]
    ax.legend(handles=legend_elements, fontsize=10)

    # 图表装饰
    plt.xticks(ticks=x_pos, labels=labels, rotation=0,fontsize=11)
    plt.title(f'Top {int(percentile*100)}% of publication age = {time}', fontsize=16)
    plt.ylabel('number of breakthrough papers', fontsize=14)
    plt.ylim(0, max(counts)*1.2)
    # plt.ylim(0, 50)
    plt.tight_layout()
    plt.savefig(f'alt_disruption/reviwer1/new_data_results/figs/{time}_count_of_ranked_papers_{percentile}_nonobel_new.png',dpi=300,bbox_inches='tight')


def plot_rank_counts_double(results_dict1, results_dict2, time, percentile):
    """
    绘制并排柱状图，对比 results_dict1 和 results_dict2 在各指标上的 focal 论文数量
    
    参数：
        results_dict1: 字典格式 {指标名: focal_count}
        results_dict2: 字典格式 {指标名: focal_count}
        time: 用于标题的时间标识
    """
    groups_order = [
        'DI', 'DI5', 'mDI', 'DI_xing',           # 第一组（DI相关）
        'SDI', 'SDI5', 'mSDI', 'SDI_xing',       # 第二组（SDI相关）
    ]

    labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$', r'$\mathrm{mDI}$', 
              r'$\mathrm{DI^{*}}$',  
              r'$\mathrm{SDI}$', r'$\mathrm{SDI_{5}}$', r'$\mathrm{mSDI}$', 
              r'$\mathrm{SDI^{*}}$']

    # 提取数据
    counts1 = [results_dict1.get(col, 0) for col in groups_order]
    counts2 = [results_dict2.get(col, 0) for col in groups_order]

    # 设置字体
    plt.rcParams['mathtext.fontset'] = 'stix'
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.size'] = 13

    # x 轴位置
    x = list(range(len(groups_order)))
    bar_width = 0.4

    fig, ax = plt.subplots(figsize=(5.5, 4))

    # 定义颜色映射
    colors1 = ["#6387E0"] * 4 + ["#C25252"] * 4   # C1: 浅蓝(DI)，深蓝(SDI)
    colors2 = ["#745FEC"] * 4 + ["#C81808B7"] * 4   # C2: 浅绿(DI)，深绿(SDI)

    # 绘制两组柱子
    bars1 = ax.bar([i - bar_width/2 for i in x], counts1, 
                   width=bar_width, color=colors1)
    bars2 = ax.bar([i + bar_width/2 for i in x], counts2, 
                   width=bar_width, color=colors2)

    # 添加斜纹区分
    for bar in bars1:
        bar.set_edgecolor('#F8F8F8')
        bar.set_hatch('/')
    for bar in bars2:
        bar.set_edgecolor('#F8F8F8')
        bar.set_hatch('\\')

    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval, 
                    str(int(yval)), ha='center', va='bottom', fontsize=10)

    # 设置坐标轴和标题
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, fontsize=12)
    ax.set_title(f'Top {int(percentile*100)}% of publication age = {time}', fontsize=16)
    ax.set_ylabel('number of experimental papers', fontsize=14)
    # ax.set_ylim(0, 200)
    # ax.set_ylim(0, 260)

    # 手动添加 4 个 legend
    legend_elements = [
        Patch(facecolor="#6387E0", edgecolor='#F8F8F8', hatch='/', 
              label=r'DI-based metrics of $\mathcal{A} \cup \mathcal{C}_1$'),
        Patch(facecolor="#C25252", edgecolor='#F8F8F8', hatch='/', 
              label=r'SDI-based metrics of $\mathcal{A} \cup \mathcal{C}_1$'),
        Patch(facecolor="#745FEC", edgecolor='#F8F8F8', hatch='\\', 
              label=r'DI-based metrics of $\mathcal{A} \cup \mathcal{C}_2$'),
        Patch(facecolor="#C81808B7", edgecolor='#F8F8F8', hatch='\\', 
              label=r'SDI-based metrics of $\mathcal{A} \cup \mathcal{C}_2$')
    ]
    ax.legend(handles=legend_elements, fontsize=10)

    plt.tight_layout()
    plt.savefig(
        f'alt_disruption/reviwer1/new_data_results/figs/{time}_count_of_ranked_papers_{percentile}.png',
        dpi=300, bbox_inches='tight'
    )

def draw_kdeplot(exp_df,con_df):
    exp_tac=exp_df['citations']
    con_tac=con_df['citations']
    sns.kdeplot(exp_tac, fill=True, label=r'$mathcal{A}\cup\mathcal{C}_1$', alpha=0.5)
    sns.kdeplot(con_tac, fill=True, label="control group 2", alpha=0.5)
    plt.legend()
    plt.savefig(f'alt_disruption/control_group_two/figs/fenbu.png',dpi=300,bbox_inches='tight')

def get_each_doi_last_metrics(df):
    """
    获取每个DOI所有指标的最后一个非空值
    
    返回:
    包含每个DOI所有指标最后值的DataFrame
    """
    # 定义我们关心的所有指标列
    metric_cols = ['SDI', 'SDI_xing', 'SDI_jing', 'mSDI', 
                   'SDI5', 'SDI5_xing', 'SDI5_jing', 'mSDI5',
                   'citations','facebook_count', 'blogs_count', 'google_users_count', 'news_count',
                    'tweets_count', 'wikipedia_count', 'altmetric_attention_score' ]

    metric_cols=list(df.columns)[2:]
    # 按DOI分组，对每个指标取最后一个非空值
    last_metrics = df.groupby('DOI').agg({
        col: lambda x: x.dropna().iloc[-1] if not x.dropna().empty else None
        for col in metric_cols
    })
    
    return last_metrics

def rank_top(time,percentile):

    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_DI_and_its_variants.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_DI_and_its_variants.jsonl')
    control_df2_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control2_group_DI_and_its_variants.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    control_df2_DI['label']=0
    
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_SDI_and_its_variants.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_SDI_and_its_variants.jsonl')
    control_df2_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control2_group_SDI_and_its_variants.jsonl')
    focal_altmetric_df = get_altmetric_counts(experiment_df_DI['DOI'].tolist())
    control_altmetric1_df = get_altmetric_counts(control_df1_DI['DOI'].tolist())
    # # control_altmetric2_df = get_altmetric_counts('alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl')
    # print(experiment_df_DI)
    # # draw_kdeplot(experiment_df_DI,control_df2_DI)
    
    print('---------------experimental groups----------------------------------')
    experiment_DI=get_year_data(time,experiment_df_DI)
    experiment_SDI = get_year_data(time,experiment_df_SDI)
    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    # del focal_merge_df['doi']
    
    print('---------------control groups 1 ----------------------------------')
    control1_DI= get_year_data(time,control_df1_DI)
    control1_SDI= get_year_data(time,control_df1_SDI)
    control1_merge_df1 = pd.merge(control1_DI, control1_SDI, left_on='DOI', right_on='DOI', how='left')
    # control1_merge_df = pd.merge(control1_merge_df1, control_altmetric1_df, left_on='DOI', right_on='doi', how='left')
    # del control1_merge_df1['doi']

    print('---------------control groups 2----------------------------------')
    control2_DI= get_year_data(time,control_df2_DI)
    control2_SDI= get_year_data(time,control_df2_SDI)
    control2_merge_df1 = pd.merge(control2_DI, control2_SDI, left_on='DOI', right_on='DOI', how='left')
    # control2_merge_df = pd.merge(control2_merge_df1, control_altmetric2_df, left_on='DOI', right_on='doi', how='left')
    # del control2_merge_df1['doi']


    print('------------------合并数据----------------------------------')
    all_data1=pd.concat([focal_merge_df,control1_merge_df1])
    # print(all_data1.columns)
    # all_data.to_csv('alt_disruption/control_group_two/figs/3_count_of_ranked_papers_0.05.csv')
    print('---------------------的实验组论文数量')
    results_dict1=compute_rank(all_data1,  percentile)

    all_data2=pd.concat([focal_merge_df,control2_merge_df1])

    results_dict2=compute_rank(all_data2,  percentile)
    # all_data2.to_csv('alt_disruption/reviwer1/new_data_results/10_count_of_ranked_papers_0.1.csv')


    #实验组和单个控制组
    # results_dict1=
    # plot_rank_counts(results_dict, time)

    # 实验组和双控制组
    # plot_rank_counts_double(results_dict1,results_dict2, time,percentile)


def rank_top_one_time(time,percentile):

    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_DI_and_its_variants_nonobel.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_DI_and_its_variants_nonobel.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_SDI_and_its_variants_nonobel.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_SDI_and_its_variants_nonobel.jsonl')
    exp_tweets_count, exp_unique_user_mentions_count = get_twitter_count(experiment_df_DI['DOI'].tolist())
    control_tweets_count, control_unique_user_mentions_count = get_twitter_count(control_df1_DI['DOI'].tolist())
    experiment_df_altmetric = twitter_dicts_to_panel_df(exp_tweets_count, exp_unique_user_mentions_count)
    control_altmetric1_df = twitter_dicts_to_panel_df(control_tweets_count, control_unique_user_mentions_count)
    # # draw_kdeplot(experiment_df_DI,control_df2_DI)
    
    print('---------------experimental groups----------------------------------')
    experiment_DI=get_year_data(time,experiment_df_DI)
    experiment_SDI = get_year_data(time,experiment_df_SDI)
    exp_alt_df=get_year_data(time,experiment_df_altmetric)

    focal_merge_df1 = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    focal_merge_df=pd.merge(focal_merge_df1, exp_alt_df, left_on='DOI', right_on='DOI', how='left')
    # print(focal_merge_df.head())
    # del focal_merge_df['doi']
    
    print('---------------control groups 1 ----------------------------------')
    control1_DI= get_year_data(time,control_df1_DI)
    control1_SDI= get_year_data(time,control_df1_SDI)
    control1_alt_df=get_year_data(time,control_altmetric1_df)
    control1_merge_df1 = pd.merge(control1_DI, control1_SDI, left_on='DOI', right_on='DOI', how='left')
    control1_merge_df=pd.merge(control1_merge_df1, control1_alt_df, left_on='DOI', right_on='DOI', how='left')
    # print(control1_merge_df)

    print('------------------合并数据----------------------------------')
    all_data1=pd.concat([control1_merge_df,focal_merge_df])
    # print(all_data1.columns)
    # all_data.to_csv('alt_disruption/control_group_two/figs/3_count_of_ranked_papers_0.05.csv')
    print('---------------------的实验组论文数量')
    results_dict1=compute_rank(all_data1,  percentile)
    print(results_dict1)

    # all_data1.to_csv('alt_disruption/reviwer1/new_data_results/10_count_of_ranked_papers_0.1.csv')
    # # 实验组和双控制组
    # plot_rank_counts_time(results_dict1,time,percentile)

def rank_one_top(percentile):

    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_DI_and_its_variants_nonobel.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_DI_and_its_variants_nonobel.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_SDI_and_its_variants_nonobel.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_SDI_and_its_variants_nonobel.jsonl')
    exp_tweets_count, exp_unique_user_mentions_count = get_twitter_count(experiment_df_DI['DOI'].tolist())
    control_tweets_count, control_unique_user_mentions_count = get_twitter_count(control_df1_DI['DOI'].tolist())
    experiment_df_altmetric = twitter_dicts_to_panel_df(exp_tweets_count, exp_unique_user_mentions_count, fill_missing=True)
    control_altmetric1_df = twitter_dicts_to_panel_df(control_tweets_count, control_unique_user_mentions_count, fill_missing=True)
    # # print(experiment_df_DI)    
    # print('---------------experimental groups----------------------------------')
    focal_merge_df1 = pd.merge(experiment_df_DI, experiment_df_SDI, left_on='DOI', right_on='DOI', how='left')
    focal_merge_df=pd.merge(focal_merge_df1,experiment_df_altmetric, left_on='DOI', right_on='DOI', how='left')
    # print(focal_merge_df)
    exp_df=get_each_doi_last_metrics(focal_merge_df)
    # print(exp_df)
    
    # print('---------------control groups 1 ----------------------------------')
    control1_merge_df1 = pd.merge(control_df1_DI, control_df1_SDI, left_on='DOI', right_on='DOI', how='left')
    control1_merge_df = pd.merge(control1_merge_df1, control_altmetric1_df, left_on='DOI', right_on='DOI', how='left')
    control1_df=get_each_doi_last_metrics(control1_merge_df)

    # print('------------------合并数据----------------------------------')
    all_data1=pd.concat([exp_df,control1_df])
    print(all_data1.columns)
    # all_data1.to_csv('alt_disruption/reviwer1/new_data_results/figs/all_data1.csv')
    # print('---------------------的实验组论文数量')
    results_dict1=compute_rank(all_data1,  percentile)

    # all_data2=pd.concat([focal_merge_df,control2_merge_df1])

    # results_dict2=compute_rank(all_data2,  percentile)
    # # all_data2.to_csv('alt_disruption/reviwer1/new_data_results/10_count_of_ranked_papers_0.1.csv')


    # #实验组和单个控制组
    plot_rank_counts(results_dict1, percentile)

if __name__ == '__main__':
    time=15
    percentile=0.1
    rank_top_one_time(time, percentile)
    # rank_one_top(0.05)
    