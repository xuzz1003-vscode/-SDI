import pandas as pd
import numpy as np
from compare_control_focal_papers_DI import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe, get_all_last_metrics
import json
import seaborn as sns
import matplotlib.pyplot as plt
def get_summary(df):
    # 确保只处理数值列
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_df = df[numeric_cols]
    
    # 计算基本统计量
    stats = {
        'Mean': round(numeric_df.mean(), 3),
        'Std': round(numeric_df.std(), 3),
        'Min': round(numeric_df.min(), 3),
        '25%': round(numeric_df.quantile(0.25), 3),
        'Median': round(numeric_df.median(), 3),
        '75%': round(numeric_df.quantile(0.75), 3),
        'Max': round(numeric_df.max(), 3),
        'Variance': round(numeric_df.var(), 3)
    }
    
    stats_summary = pd.DataFrame(stats)
    print(stats_summary)
    return stats_summary

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

def draw_corr(data):
    # 将数据转换为 DataFrame
    df = pd.DataFrame(data)

    plt.rcParams['mathtext.fontset'] = 'stix'  # 使用 STIX 字体（类似 Times New Roman）
    # 定义列的新顺序，按照你需要的顺序排列列
    new_order=['DI', 'DI5', 'mDI', 'DI_xing', 'DI_jing', 'SDI', 'SDI5',
       'mSDI', 'SDI_xing', 'SDI_jing', 'citations', 'cited_by_Facebooks_count',
       'cited_by_blogs_count', 'cited_by_google_accounts_count',
       'cited_by_news_count', 'cited_by_twitter_accounts_count',
       'cited_by_wikipedia_count']
    # 确保新顺序中的列都存在于数据中
    df = df.reindex(columns=new_order)
    print(df.columns)
    # 将数值列转换为浮点型，并去除缺失值
    # focal_papers_df = df.drop(columns=['cited_by_patents_count','cited_by_total_count','altmetric_score']).apply(pd.to_numeric, errors='coerce')


    # 计算相关性矩阵
    correlation_matrix = df.corr()

    # 创建一个下三角掩码
    mask = np.zeros_like(correlation_matrix, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True

    # 设置图表样式
    sns.set_theme(style='white', context='paper')  # 使用白色背景和论文风格
    plt.figure(figsize=(10, 8))
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 14})


    # 绘制相关性热图
    heatmap = sns.heatmap(
        correlation_matrix, 
        annot=True, 
        mask=mask,
        # cmap='vlag',
        cmap='RdBu_r',
 
        fmt=".2f", 
        # linewidths=0.5,  # 添加分隔线
        cbar_kws={'shrink': 0.8}  # 调整颜色条的大小
    )

    # 自定义 x 和 y 轴标签
    labels = [r'$\mathrm{DI}$',  r'$\mathrm{DI_{5}}$', r'$\mathrm{mDI}$', r'$\mathrm{DI^{*}}$', r'$\mathrm{\text{DI#}}$',
              r'$\mathrm{SDI}$', r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$', r'$\mathrm{SDI^{*}}$', r'$\mathrm{\text{SDI#}}$',  
              r'$\mathrm{CCs}$',r'$\mathrm{FCs}$', r'$\mathrm{BCs}$', r'$\mathrm{GACs}$', r'$\mathrm{NCs}$', r'$\mathrm{TACs}$', r'$\mathrm{WCs}$']
               
    # 设置自定义标签
    plt.xticks(ticks=[i+0.5 for i in np.arange(len(labels))], labels=labels, rotation=0, va='center', fontsize=11)
    plt.yticks(ticks=[i+0.5 for i in np.arange(len(labels))], labels=labels, rotation=0, fontsize=12,va='center')
    plt.title('Experimental group and the first control group',fontsize=20)

    plt.tight_layout()  # 使布局紧凑
    plt.savefig(f'alt_disruption/control_group_two_new/figs/exp vs control 1.png',dpi=300, bbox_inches='tight')


def compare_experimental_and_controls():
    
    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_DI_and_its_variants.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_DI_and_its_variants.jsonl')
    control_df2_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_DI_and_its_variants_group2.jsonl')

    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_SDI_and_its_variants.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_SDI_and_its_variants.jsonl')
    control_df2_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_SDI_and_its_variants_group2.jsonl')
    
    focal_altmetric_df = get_altmetric_counts('alt_disruption/final_run_experiment/data/experimental_groups_social_counts.json')
    control_altmetric1_df = get_altmetric_counts('alt_disruption/final_run_experiment/data/control_papers_altmetric_counts.jsonl')
    control_altmetric2_df = get_altmetric_counts('alt_disruption/control_group_two_new/data/select_control_altmetric_counts.jsonl')

    print('---------------experimental groups----------------------------------')
    experiment_SDI = get_all_last_metrics(experiment_df_DI)
    experiment_DI=get_all_last_metrics(experiment_df_SDI)

    focal_merge_df1 = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    focal_merge_df= pd.merge(focal_merge_df1, focal_altmetric_df, left_on='DOI', right_on='doi', how='left')
    del focal_merge_df['doi']
    get_summary(focal_merge_df).to_csv('alt_disruption/control_group_two_new/exp_results/experiment_group.csv')
    
    print('---------------control groups----------------------------------')
    control1_DI= get_all_last_metrics(control_df1_DI)
    control1_SDI= get_all_last_metrics(control_df1_SDI)
    control1_merge_df1 = pd.merge(control1_DI, control1_SDI, left_on='DOI', right_on='DOI', how='left')
    control1_merge_df = pd.merge(control1_merge_df1, control_altmetric1_df, left_on='DOI', right_on='doi', how='left')
    del control1_merge_df['doi']
    get_summary(control1_merge_df).to_csv('alt_disruption/control_group_two_new/exp_results/control group 1.csv')



    control2_DI= get_all_last_metrics(control_df2_DI)
    control2_SDI= get_all_last_metrics(control_df2_SDI)
    control2_merge_df1 = pd.merge(control2_DI, control2_SDI, left_on='DOI', right_on='DOI', how='left')
    control2_merge_df = pd.merge(control2_merge_df1, control_altmetric2_df, left_on='DOI', right_on='doi', how='left')
    del control2_merge_df['doi']
    get_summary(control2_merge_df)
    get_summary(control2_merge_df).to_csv('alt_disruption/control_group_two_new/exp_results/control group 2.csv')

    print('------------------计算相似性----------------------------------')
    all_data=pd.concat([focal_merge_df,control1_merge_df])
    print(all_data.columns)
    draw_corr(all_data)

if __name__ == '__main__':
    compare_experimental_and_controls()