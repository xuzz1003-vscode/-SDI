import pandas as pd
import numpy as np
from compare_control_focal_papers_DI import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe, get_all_last_metrics
import json
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker  # 导入格式化模块


def get_year_data(time,df):
    year_to_data = {year: group for year, group in df.groupby('Year')}
    data=year_to_data[time]
    del data['Year']
    return data

def compute_rank(df):
    # 确保label列存在
    if 'label' not in df.columns:
        raise ValueError("DataFrame必须包含'label列（1=focal, 0=control）")

    # 获取数值列（排除DOI和label）
    numeric_cols = [col for col in df.columns 
                   if col not in ['DOI', 'label'] 
                   and pd.api.types.is_numeric_dtype(df[col])]
    for col in numeric_cols:
        # 计算排名（降序，值越大排名越高）
        df[f'rank_{col}'] = df[col].rank(ascending=False, method='min')
    return df
# 绘制某一年的密度图
def plot_single_density(df, index_list, time):
    # 设置全局样式
    # plt.style.use('seaborn')
    plt.rcParams.update({
        'mathtext.fontset': 'stix',
        'font.family': 'Times New Roman',
        'font.size': 13,
        'axes.titlesize': 14,
        'axes.labelsize': 12
    })
    
    # 创建颜色和线型循环
    # colors = plt.cm.tab10(np.linspace(0, 1, len(index_list)))
    # Science期刊风格（高对比度）
    science_colors = [
        '#FF2C00',  # 大红
        # '#0C5DA5',  # 皇家蓝
        # '#4E79A7',  # 深蓝
        '#648FFF',  # 蓝
        # '#00B945',  # 翡翠绿
        # '#FF9500',  # 橙黄
        # '#845B97',  # 紫
        # '#474747',  # 深灰
        '#9e9e9e'   # 浅灰
    ]
    colors = science_colors[:len(index_list)]
    line_styles = ['-', '--', '-.', ':'] * 2  # 循环使用不同线型
    
    fig, ax = plt.subplots(figsize=(6, 5))
    if 'DI' in index_list:
        labels = [r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$']
    if 'SDI' in index_list:
        labels = [  r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$']

    
    for i, index in enumerate(index_list):
        # 获取focal论文的排名数据
        ranking_df = df[df['label'] == 1][f'rank_{index}']
        
        # # 计算并绘制均值线
        mean_rank = ranking_df.mean()
        # ax.axvline(
        #     mean_rank,
        #     color=colors[i],
        #     # linestyle=line_styles[i],
        #     linewidth=1.5,
        #     alpha=0.7,
        #     label=f'{index} Mean: {mean_rank:.0f}'
        # )

          # 绘制密度曲线
        sns.kdeplot(
            ranking_df,
            color=colors[i],
            linestyle=line_styles[i],
            linewidth=2,
            label=f'{labels[i]} Mean: {mean_rank:.0f}',
            ax=ax
        )
    
    # 美化图表
    ax.set_xlabel('Rank Position')
    ax.set_ylabel('Density')
    # ax.set_ylim(0,0.0006)
    ax.set_ylim(0,0.0009)
      # 设置对数坐标
    # ax.set_yscale('log')
    
    # # 调整y轴范围（根据实际数据可能需要调整）
    # ax.set_ylim(1e-6, 1e-2)  # 示例范围，请根据实际数据调整
    
    # ax.set_title(f'Publication age = {time}')
    
    # # 格式化y轴刻度
    # ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f'{y:.0e}'))
    
    # 设置y轴刻度（强制显示4位小数）
    # # y_ticks = [0, 0.0005, 0.001, 0.0015, 0.002]
    # ax.set_yticks(y_ticks)
    # # 使用 FormatStrFormatter 统一格式化为 0.0000
    # ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))
    ax.set_title(f'Publication age = {time}')
    # ax.grid(True, linestyle=':', alpha=0.6)
    
    # 合并图例
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels,
        frameon=True,
        framealpha=0.8,
        loc='upper right',
        # bbox_to_anchor=(1.3, 1)
    )
    
    plt.tight_layout()
    plt.savefig(
        f'alt_disruption/control_group_two_new/figs/ranking_density_SDI_{time}.png',
        dpi=300,
        bbox_inches='tight'
    )
    plt.close()

def plot_density_control1_vs_control2(control_df, DI_based_index, SDI_based_index,time):
    # 设置全局样式
    # plt.style.use('seaborn')
    plt.rcParams.update({
        'mathtext.fontset': 'stix',
        'font.family': 'Times New Roman',
        'font.size': 13,
        'axes.titlesize': 14,
        'axes.labelsize': 12
    })
    

    # colors = science_colors[:len(index_list)]
    line_styles = ['-', '--', '-.', ':'] * 2  # 循环使用不同线型
    
    fig, ax = plt.subplots(figsize=(6, 5))
    # 获取论文的排名数据
    control1_DI = control_df[control_df['label'] == 1][f'rank_{DI_based_index}']
    control1_DI_mean = control1_DI.mean()
    control1_SDI= control_df[control_df['label'] == 1][f'rank_{SDI_based_index}']
    control1_SDI_mean = control1_SDI.mean()
    
    if DI_based_index=='DI5':
        DI_label=r'$\mathrm{DI_{5}}$'
        SDI_label=r'$\mathrm{SDI_{5}}$'
    else:
        DI_label=DI_based_index
        SDI_label=SDI_based_index

    sns.kdeplot(
        control1_DI,
        color="blue",
        linestyle='--',
        linewidth=2,
        label=DI_label,
        ax=ax
    )
    ax.axvline(
            control1_DI_mean,
            color="blue",
            linestyle='--',
            linewidth=1.5,
            alpha=0.7
        )

    sns.kdeplot(
        control1_SDI,
        color="red",
        linestyle='-',
        linewidth=2,
        label=SDI_label,
        ax=ax
    )
    ax.axvline(
            control1_SDI_mean,
            color="red",
            linestyle='-',
            linewidth=1.5,
            alpha=0.7
        )


    ax.text(1, 0.75, fr'Average {DI_label} ranking for $\mathcal{{A}}$: {control1_DI_mean:.0f}', 
        transform=ax.transAxes, color='blue',
        ha='right', va='top')

    ax.text(1, 0.7, fr'Average {SDI_label} ranking for $\mathcal{{A}}$: {control1_SDI_mean:.0f}', 
            transform=ax.transAxes, color='red',
            ha='right', va='top') #0.95, 0.5
    
    # 美化图表
    # if index_name1=='SDI5':
    #     ax.set_xlabel(r'Rankings of $\mathrm{SDI_{5}}$')
    # if index_name1=='DI5':
    #     ax.set_xlabel(r'Rankings of $\mathrm{DI_{5}}$')
    # else:
    #     ax.set_xlabel(f'Rankings of {index_name1}')
    ax.set_ylabel('Density')
    # ax.set_ylim(0, 1.2e-3)  # 设置 y 轴范围为 0 到 1.4e-3，0, 4e-4
    ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    ax.set_title(f'Publication age = {time}')
    ax.set_xlabel(f'Rankings')
        # ax.grid(True, linestyle=':', alpha=0.6)
    
    # 合并图例
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels,
        frameon=True,
        framealpha=0.8,
        loc='upper right',
        # bbox_to_anchor=(1.3, 1)
    )
    
    plt.tight_layout()
    plt.savefig(
        f'alt_disruption/control_group_two_new/figs/ranking_{DI_based_index}_{time}_control2.png',
        dpi=300,
        bbox_inches='tight'
    )
    plt.close()

def rank_top(time):
    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_DI_and_its_variants.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_DI_and_its_variants.jsonl')
    control_df2_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_DI_and_its_variants_group2.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    control_df2_DI['label']=0
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_SDI_and_its_variants.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_SDI_and_its_variants.jsonl')
    control_df2_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_SDI_and_its_variants_group2.jsonl')
    
    
    print('---------------experimental groups----------------------------------')
    experiment_DI=get_year_data(time,experiment_df_DI)
    experiment_SDI = get_year_data(time,experiment_df_SDI)

    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    
    print('---------------control groups----------------------------------')
    control1_DI= get_year_data(time,control_df1_DI)
    control1_SDI= get_year_data(time,control_df1_SDI)
    control1_merge_df = pd.merge(control1_DI, control1_SDI, left_on='DOI', right_on='DOI', how='left')
    print('---------------control groups 2----------------------------------')
    control2_DI= get_year_data(time,control_df2_DI)
    control2_SDI= get_year_data(time,control_df2_SDI)
    control2_merge_df= pd.merge(control2_DI, control2_SDI, left_on='DOI', right_on='DOI', how='left')

    print('------------------合并数据----------------------------------')
    all_data1=pd.concat([focal_merge_df,control1_merge_df])
    # print(all_data.columns)
    # print(all_data)
    print('---------------------统计前10的实验组论文数量')
    results1=compute_rank(all_data1)
    results2=compute_rank(pd.concat([focal_merge_df,control2_merge_df]))
    # plot_single_density(results,['SDI','SDI5','mSDI'], time)
    return results1,results2

def df_mean(df):
    ranking_df = df[df['label'] == 1]
    # Select only numeric columns for mean calculation
    numeric_cols = ranking_df.select_dtypes(include=[np.number]).columns
    mean_rank = ranking_df[numeric_cols].mean()
    return mean_rank
def plot_combined_means(all_means, index_list):
    """绘制多年度指标排名的折线图"""
    plt.figure(figsize=(6, 4.5))
    
    # 设置专业学术风格
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'mathtext.fontset': 'stix',
        'axes.labelsize': 14,
        'axes.titlesize': 14
    })
    
    # 为每个指标绘制折线
    metric_list=[r'$\mathrm{DI}$', r'$\mathrm{DI_{5}}$',r'$\mathrm{mDI}$', r'$\mathrm{SDI}$',r'$\mathrm{SDI_{5}}$',r'$\mathrm{mSDI}$']
    # colors = plt.cm.tab10.colors  # 使用tab10色板
    science_colors = [
        '#648FFF',  # 蓝
        '#845B97',  # 紫
        # '#474747',  # 深灰
        '#9e9e9e' ,  # 浅灰
        '#FF2C00',  # 大红
        '#FF9500',  # 橙黄
        '#00B945',  # 翡翠绿
    ]
    markers = ['o', 's', 'D', '^', 'v']  # 不同标记形状
    line_style=['-.', '-.' ,'-.','-','-','-',] 
    for idx, metric in enumerate(index_list):
        plt.plot(
            all_means.index,  # x轴：年份
            all_means[f'rank_{metric}'],  # y轴：该指标的均值排名
            label=metric_list[idx],
            color=science_colors[idx],
            marker=markers[idx % len(markers)],
            markersize=3,
            linewidth=1.5,
            linestyle=line_style[idx % len(line_style)],
            alpha=0.9
        )
    
    # 美化图表
    plt.xlabel('Publication age')
    plt.ylabel('average ranking of experimental papers')
      # 设置y轴为对数尺度
    plt.ylim(0, 2250)
    # plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    
    # 调整y轴范围（对数尺度下）
    # plt.ylim(100, 10000)  # 根据你的数据调整
    # plt.ylim(200,1800)
    # plt.title('Trend of Mean Rankings by Year', pad=20)
    # plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig('alt_disruption/control_group_two_new/figs/mean_rank_trend_of control 1.png', dpi=300, bbox_inches='tight')
if __name__ == '__main__':
    for y in [3,7,10]:
        results1,results2=rank_top(y)
        plot_density_control1_vs_control2(results2,'mDI','mSDI', y)

        
        

    # # 存储所有年份的结果
    # all_means = pd.DataFrame()
    # index_list = ['DI', 'DI5', 'mDI','SDI', 'SDI5', 'mSDI']  # 要分析的指标列表
    
    # for y in range(0, 11):  # 假设年份为0, 2
    #     results1,results2 = rank_top(y)  # 获取该年份的数据
    #     year_mean = df_mean(results1)  # 计算均值
    #     all_means[y] = year_mean  # 存储结果
    
    # # 转置DataFrame以便绘图
    # all_means = all_means.T
    # all_means.index.name = 'Year'
    # print(all_means)
    
    # # 绘制趋势图
    # plot_combined_means(all_means, index_list)
        