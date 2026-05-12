import pandas as pd
import numpy as np
from compare_control_focal_papers_DI import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe, get_all_last_metrics
import json
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def get_altmetric_counts(altmetric_path):
    combined_data = {}
    with open(altmetric_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = json.loads(line)
            doi = line['doi']
            record = {
                'cited_by_Facebooks_count': line.get('cited_by_fbwalls_count', 0),
                'cited_by_blogs_count': line.get('cited_by_feeds_count', 0),
                'cited_by_google_accounts_count': line.get('cited_by_gplus_count', 0),
                'cited_by_news_count': line.get('cited_by_msm_count', 0),
                'cited_by_twitter_accounts_count': line.get('cited_by_tweeters_count', 0),
                'cited_by_wikipedia_count': line.get('cited_by_wikipedia_count', 0),
                # 'cited_by_patents_count': line.get('cited_by_patents_count', 0),
                # 'cited_by_total_count': line.get('cited_by_accounts_count', 0),
                # 'altmetric_score': line.get('score', 0),
            }
            combined_data[doi] = record
    
    altmetric_df = pd.DataFrame.from_dict(combined_data, orient='index')
    altmetric_df.index.name = 'doi'
    altmetric_df = altmetric_df.reset_index()
    
    cols_to_convert = altmetric_df.columns.difference(['doi'])
    altmetric_df[cols_to_convert] = altmetric_df[cols_to_convert].apply(pd.to_numeric, errors='coerce')
    
    if altmetric_df[cols_to_convert].isna().any().any():
        print("警告：部分数据无法转换为数值型，已被设为NaN。以下是包含NaN的列：")
        print(altmetric_df[cols_to_convert].isna().sum())
    
    return altmetric_df

def get_year_data(time,df):
    year_to_data = {year: group for year, group in df.groupby('Year')}
    data=year_to_data[time]
    del data['Year']
    return data

def compute_rank(df, percentile=0.1):
    """
    对数值列计算rank，并统计前percentile中label=1（focal）的比例。

    参数：
        df: 包含数据的DataFrame，必须有'label'列（1=focal, 0=control）
        percentile: 统计前多少比例的数据（默认前10%）

    返回：
        results: 字典 {列名: (前percentile中focal的数量, 前percentile总数量)}
    """
    # 确保label列存在
    if 'label' not in df.columns:
        raise ValueError("DataFrame必须包含'label列（1=focal, 0=control）")

    # 获取数值列（排除DOI和label）
    numeric_cols = [col for col in df.columns 
                   if col not in ['DOI', 'label'] 
                   and pd.api.types.is_numeric_dtype(df[col])]
    results = {}
    for col in numeric_cols:
        # 计算排名（降序，值越大排名越高）
        df[f'rank_{col}'] = df[col].rank(ascending=False, method='min')
        # print(df)
        # 前percentile的阈值
        threshold = int(len(df) * percentile)
        top_df = df[df[f'rank_{col}'] <= threshold]
        # 统计focal数量
        focal_count = top_df['label'].sum()
        total_count = len(top_df)
        results[col] = focal_count
        print(f"{col}: 前{percentile*100:.0f}%中 {focal_count}/{total_count} 是focal")
    print(results)
    return results

def plot_rank_counts(results_dict, time):
    """
    绘制柱状图，显示各指标前percentile中focal论文的数量
    
    参数：
        results_dict: 字典格式 {指标名: focal_count}
        time: 用于标题的时间标识
    """
    groups_order = [
        'DI', 'DI5', 'mDI', 'DI_xing', 'DI_jing',          # 第一组（DI相关）
        'SDI', 'SDI5', 'mSDI', 'SDI_xing', 'SDI_jing',      # 第二组（SDI相关）
        # 'citations',                                        # 第三组开始（Altmetric）
        # 'cited_by_Facebooks_count',
        # 'cited_by_blogs_count',
        # 'cited_by_google_accounts_count',
        # 'cited_by_news_count',
        # 'cited_by_twitter_accounts_count',
        # 'cited_by_wikipedia_count'
    ]
    plt.rcParams['mathtext.fontset'] = 'stix'  # 使用 STIX 字体（类似 Times New Roman）
    plt.rcParams['font.family'] = 'Times New Roman'  # 设置普通文本字体
    plt.rcParams['font.size'] = 13  # 可选：设置字体大小

    # 按分组顺序提取数据
    counts = [results_dict.get(col, 0) for col in groups_order]
    labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$', r'$\mathrm{DI^{*}}$',r'$\mathrm{\text{DI#}}$',  
          r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$', r'$\mathrm{SDI^{*}}$', r'$\mathrm{\text{SDI#}}$']
        #   r'$\mathrm{CCs}$', r'$\mathrm{FCs}$', r'$\mathrm{BCs}$', r'$\mathrm{GACs}$', r'$\mathrm{NCs}$', r'$\mathrm{TACs}$', r'$\mathrm{WCs}$']

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
    group_colors = [
    '#7AC5CD', '#7AC5CD', '#7AC5CD', '#7AC5CD', '#7AC5CD',  # 明亮蓝
    '#FFA500', '#FFA500', '#FFA500', '#FFA500', '#FFA500',  # 活力橙
    '#3CB44B', '#3CB44B', '#3CB44B', '#3CB44B',             # 鲜绿色
    '#3CB44B', '#3CB44B', '#3CB44B'
]

    # 位置设置（保持分组间距）
    x_pos = list(range(len(groups_order)))
    for i in [5, 10]:  # 在组间添加间距
        x_pos[i:] = [x + 0.5 for x in x_pos[i:]]
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(6, 4.5))

    bars = plt.bar(x_pos, counts, color=group_colors, width=0.9)
    plt.rcParams['hatch.color'] = '#555555'  # 统一设置为灰色

    # 设置柱状图样式
    for i, bar in enumerate(bars):
        if i < 5:          # 第一组
            bar.set_edgecolor('#F8F8F8')  # 先设置边缘颜色
            bar.set_hatch('/')
        elif i < 10:       # 第二组
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

    # 图表装饰
    plt.xticks(ticks=x_pos, labels=labels, rotation=0,fontsize=11)
    plt.title(f'Publication age = {time}',fontsize=18)
    plt.ylabel('number of experimental papers', fontsize=14)
    # plt.ylim(0, max(counts)*1.2)
    plt.ylim(0, 50)
    plt.tight_layout()
    plt.savefig(f'alt_disruption/control_group_two/figs/{time}_count_of_ranked_papers_1.png',dpi=300,bbox_inches='tight')

# def plot_rank_counts_double(results_dict1, results_dict2, time,percentile):
#     """
#     绘制并排柱状图，对比 results_dict1 和 results_dict2 在各指标上的 focal 论文数量
    
#     参数：
#         results_dict1: 字典格式 {指标名: focal_count}
#         results_dict2: 字典格式 {指标名: focal_count}
#         time: 用于标题的时间标识
#     """
#     groups_order = [
#         'DI', 'DI5', 'mDI', 'DI_xing',           # 第一组（DI相关）
#         'SDI', 'SDI5', 'mSDI', 'SDI_xing',       # 第二组（SDI相关）
#     ]

#     labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$', 
#               r'$\mathrm{DI^{*}}$',  
#               r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$', 
#               r'$\mathrm{SDI^{*}}$']

#     # 提取数据
#     counts1 = [results_dict1.get(col, 0) for col in groups_order]
#     counts2 = [results_dict2.get(col, 0) for col in groups_order]

#     # 设置字体
#     plt.rcParams['mathtext.fontset'] = 'stix'
#     plt.rcParams['font.family'] = 'Times New Roman'
#     plt.rcParams['font.size'] = 13

#     # x 轴位置
#     x = list(range(len(groups_order)))
#     bar_width = 0.4 # 两组柱子的间距

#     fig, ax = plt.subplots(figsize=(5.5, 4))

#     # 绘制两组柱子
#       # 设置柱状图样式
   
#     bars1 = ax.bar([i - bar_width/2 for i in x], counts1, 
#                    width=bar_width, label=r'$\mathcal{A} \cup \mathcal{C}_1$', color="#6CC3CE")#7AC5CD
#     bars2 = ax.bar([i + bar_width/2 for i in x], counts2, 
#                    width=bar_width, label=r'$\mathcal{A} \cup \mathcal{C}_2$', color="#C2222D")#FFA500
#     for i, bar in enumerate(bars1):
#         bar.set_edgecolor('#F8F8F8')  # 先设置边缘颜色
#         bar.set_hatch('/')


#     for i, bar in enumerate(bars2):
#         bar.set_edgecolor('#F8F8F8')  # 先设置边缘颜色
#         bar.set_hatch('\\')
    

#     # 添加数值标签
#     for bars in [bars1, bars2]:
#         for bar in bars:
#             yval = bar.get_height()
#             ax.text(bar.get_x() + bar.get_width()/2, yval, 
#                     str(int(yval)), ha='center', va='bottom', fontsize=10)

#     # 设置坐标轴和标题
#     ax.set_xticks(x)
#     ax.set_xticklabels(labels, rotation=0, fontsize=12)
#     ax.set_title(f'Top {int(percentile*100)}% of publication age = {time}', fontsize=16)
#     ax.set_ylabel('number of experimental papers', fontsize=14)
#     ax.set_ylim(0, 200)
#     # ax.set_ylim(0, 250)
#     # ax.set_ylim(0, 50)

#     # 添加图例
#     ax.legend(fontsize=12)

#     plt.tight_layout()
#     plt.savefig(f'alt_disruption/control_group_two_new/figs/{time}_count_of_ranked_papers_{percentile}.png',dpi=300,bbox_inches='tight')

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
    ax.set_ylim(0, 260)

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
        f'alt_disruption/control_group_two_new/figs/{time}_count_of_ranked_papers_{percentile}.png',
        dpi=300, bbox_inches='tight'
    )

def draw_kdeplot(exp_df,con_df):
    exp_tac=exp_df['citations']
    con_tac=con_df['citations']
    sns.kdeplot(exp_tac, fill=True, label=r'$mathcal{A}\cup\mathcal{C}_1$', alpha=0.5)
    sns.kdeplot(con_tac, fill=True, label="control group 2", alpha=0.5)
    plt.legend()
    plt.savefig(f'alt_disruption/control_group_two/figs/fenbu.png',dpi=300,bbox_inches='tight')


def rank_top(time,percentile):

    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_DI_and_its_variants.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_DI_and_its_variants.jsonl')
    control_df2_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_DI_and_its_variants_group2.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    control_df2_DI['label']=0
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_SDI_and_its_variants.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_SDI_and_its_variants.jsonl')
    control_df2_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_SDI_and_its_variants_group2.jsonl')
    
    focal_altmetric_df = get_altmetric_counts('alt_disruption/final_run_experiment/data/experimental_groups_social_counts.json')
    control_altmetric1_df = get_altmetric_counts('alt_disruption/final_run_experiment/data/control_papers_altmetric_counts.jsonl')
    control_altmetric2_df = get_altmetric_counts('alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl')
    print(experiment_df_DI)
    draw_kdeplot(experiment_df_DI,control_df2_DI)
    
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
    print(all_data1.columns)
    # all_data.to_csv('alt_disruption/control_group_two/figs/3_count_of_ranked_papers_0.05.csv')
    print('---------------------统计前10的实验组论文数量')
    results_dict1=compute_rank(all_data1,  percentile)

    all_data2=pd.concat([focal_merge_df,control2_merge_df1])

    results_dict2=compute_rank(all_data2,  percentile)
    all_data2.to_csv('alt_disruption/control_group_two_new/figs/10_count_of_ranked_papers_0.05.csv')


    #实验组和单个控制组
    # plot_rank_counts(results_dict, time)

    #实验组和双控制组
    plot_rank_counts_double(results_dict1,results_dict2, time,percentile)
if __name__ == '__main__':
    time=3
    percentile=0.1
    rank_top(time,percentile)