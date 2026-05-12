#每个指标整体分布，不需要加时间，即每个数据集中所有数据 指标值
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.rc('font',family='Times New Roman') 
import seaborn as sns
from scipy.stats import ttest_ind
import os
import json
from scipy import stats

def jsonl_DI_index_to_dataframe(file_path):
    rows = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            for doi, year_data in data.items():
                for year, metrics in year_data.items():
                    row = {
                    'DOI': doi,
                    'Year': int(year),
                    'DI': metrics.get('di','None'),
                    'DI5': metrics.get('di5','None'),
                    'mDI': metrics.get('mdi','None'),
                    'DI_xing': metrics.get('di_xing','None'),
                    'DI_jing': metrics.get('di_jing','None'),
                    # 'DI5_xing': metrics.get('di5_xing','None'),
                    # 'DI5_jing': metrics.get('di5_jing','None'),
                    # 'mDI5': metrics.get('mdi5','None'),
                    'citations':metrics['counts']['ni']+metrics['counts']['nj']
                    }
                    rows.append(row)
    
    return pd.DataFrame(rows)

def jsonl_SDI_index_to_dataframe(file_path):
    rows = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            for doi, year_data in data.items():
                for year, metrics in year_data.items():
                    row = {
                    'DOI': doi,
                    'Year': int(year),
                    'SDI': metrics.get('sDI','None'),
                    'SDI5': metrics.get('sDI5','None'),
                    'mSDI': metrics.get('msDI','None'),
                    'SDI_xing': metrics.get('sDI_xing','None'),
                    'SDI_jing': metrics.get('sDI_jing','None'),
                    # 'SDI5_xing': metrics.get('sDI5_xing','None'),
                    # 'SDI5_jing': metrics.get('sDI5_jing','None'),
                    # 'mSDI5': metrics.get('msDI5','None'),
                    # 'citations':metrics['counts']['ni']+metrics['counts']['nj']
                    }
                    rows.append(row)
    
    return pd.DataFrame(rows)

def get_all_last_metrics(df):
    """
    获取每个DOI所有指标的最后一个非空值
    
    返回:
    包含每个DOI所有指标最后值的DataFrame
    """
    # 定义我们关心的所有指标列
    # metric_cols = ['DI', 'DI_xing', 'DI_jing', 'mDI', 
    #                'DI5', 'DI5_xing', 'DI5_jing', 'mDI5','citations']
    metric_cols = ['SDI', 'SDI_xing', 'SDI_jing', 'mSDI', 
                   'SDI5', 'SDI5_xing', 'SDI5_jing', 'mSDI5','citations']

    metric_cols=list(df.columns)[2:]
    # 按DOI分组，对每个指标取最后一个非空值
    last_metrics = df.groupby('DOI').agg({
        col: lambda x: x.dropna().iloc[-1] if not x.dropna().empty else None
        for col in metric_cols
    })
    
    return last_metrics

def get_last_non_null_values(df, metric_col):
    """
    获取每个DOI在指定指标下的最后一个非空值
    
    参数:
    df: 包含所有指标的DataFrame
    metric_col: 要查询的指标列名 (如 'DI', 'DI5'等)
    
    返回:
    包含每个DOI最后一个非空值的Series
    """
    # 按DOI分组，并获取每组中指定指标的最后一个非空值
    last_values = df.groupby('DOI').apply(
        lambda group: group[metric_col].dropna().iloc[-1] if not group[metric_col].dropna().empty else None
    )
    # print(last_values)
    # last_values = df.loc[df['Year'] == 5].set_index('DOI')['DI']
 
    return last_values

def plot_density_comparison(metric, control_df1,control_df2, experiment_df,save_fig_path):
    """
    绘制两组数据的密度对比图并计算统计检验
    
    参数:
    metric: 要比较的指标列名
    df1: 第一组数据的DataFrame
    title: 图表标题 (默认自动生成)
    xlabel: x轴标签 (默认使用metric)
    figsize: 图表大小 (默认(10,6))
    """
    # 全局设置字体大小
    plt.rcParams.update({
        'font.size': 18,           # 默认字体大小
        'axes.titlesize': 18,      # 标题字体大小
        'axes.labelsize': 18,      # 坐标轴标签字体大小
        'xtick.labelsize': 18,     # X轴刻度标签字体大小
        'ytick.labelsize': 18,     # Y轴刻度标签字体大小
        'legend.fontsize': 16,     # 图例字体大小
    })
    plt.rc('font',family='Times New Roman') 
    figsize=(8, 6)
    # 准备数据
    control_data1 = get_last_non_null_values(control_df1, metric).dropna()
    control_data2 = get_last_non_null_values(control_df2, metric).dropna()
    data2 = get_last_non_null_values(experiment_df, metric).dropna()
    control_data2.to_csv('alt_disruption/control_group_two_new/figs/control_group 2.csv')
    data2.to_csv('alt_disruption/control_group_two_new/figs/experimental.csv')
    print(control_data2)
    print(data2)
    # 计算均值和统计检验

    control_mean1,control_mean2, mean2 = np.mean(control_data1), np.mean(control_data2),np.mean(data2)
    t_stat, p_value1 = stats.ttest_ind(control_data1, data2, equal_var=False)
    t_stat, p_value2= stats.ttest_ind(control_data2, data2, equal_var=False)

    
    # 创建图形
    plt.figure(figsize=figsize)
    
    # 绘制密度图
    sns.histplot(control_data1, kde=True, color='blue', label=f'Control group 1 (mean={control_mean1:.3e})', stat="density", linestyle='--' )
    sns.histplot(control_data2, kde=True, color='green', label=f'Control group 2 (mean={control_mean2:.3e})', stat="density", linestyle='--' )
    sns.histplot(data2, kde=True, color='red',  label=f'Experimental group (mean={mean2:.3e})', stat="density", linewidth=0)
    # 绘制密度图
    # sns.kdeplot(data1, label=f"Control papers (mean={mean1:.3e})", fill=True)
    # sns.kdeplot(data2, label=f"Experimental groups (mean={mean2:.3e})", fill=True)
    # 在图中添加平均值
    plt.axvline(control_mean1, color='blue', linestyle='--',linewidth=2)
    plt.axvline(control_mean2, color='green', linestyle=':',linewidth=2)
    plt.axvline(mean2, color='red', linestyle='-.',linewidth=2)
    if metric=='DI':
        plt.ylim(0,100)
        plt.xlim(-0.1,0.1)
        plt.xlabel(metric)
    if metric=='DI_jing':
        plt.ylim(0,70)
        plt.xlim(0,0.2)
        plt.xlabel('DI#')
    if metric=='DI_xing':
        plt.ylim(0,250)
        plt.xlim(0,0.1)
        plt.xlabel('DI*')
    if metric=='DI5':
        plt.xlim(-0.1,0.15)
        plt.ylim(0,180)
        plt.xlabel(r'$ \mathrm{DI}_{5} $')
    if metric=='mDI':
        plt.ylim(0,1)
        plt.xlim(-40,40)
        plt.xlabel('mDI')


    if metric=='SDI':
        plt.ylim(0,10)
        plt.xlim(-0.4,1)
        plt.xlabel(metric)
    if metric=='SDI_jing':
        plt.ylim(0,100)
        plt.xlim(0,0.1)
        plt.xlabel('SDI#')
    if metric=='SDI_xing':
        plt.ylim(0,20)
        plt.xlim(0,1)
        plt.xlabel('SDI*')
    if metric=='SDI5':
        plt.xlim(0,1)
        plt.ylim(0,14)
        plt.xlabel(r'$ \mathrm{SDI}_{5} $')
    if metric=='mSDI':
        # plt.ylim(0,1)
        plt.xlim(-20,500)
        plt.xlabel('mSDI')
    
    plt.ylabel("Density")
    
    # 添加统计信息
    plt.annotate(f"T-test 1 p-value 1 = {p_value1:.3e}\nT-test 2 p-value 2 = {p_value2:.3e}", 
                 xy=(0.51, 0.6), xycoords='axes fraction')

    
    # 添加图例
    plt.legend(loc='upper right')
    
    # 显示图形
    plt.savefig(save_fig_path,dpi=400,bbox_inches='tight')

def plot_boxplot_comparison(metric, control_df1, control_df2, experiment_df, save_fig_path):
    """
    绘制三组数据的箱线图对比，并计算统计检验
    """
    # 字体设置
    plt.rcParams.update({
        'font.size': 18,
        'axes.titlesize': 18,
        'axes.labelsize': 18,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'legend.fontsize': 16,
    })
    plt.rc('font', family='Times New Roman')

    figsize = (8, 6)

    # 准备数据
    control_data1 = get_last_non_null_values(control_df1, metric).dropna()
    control_data2 = get_last_non_null_values(control_df2, metric).dropna()
    exp_data = get_last_non_null_values(experiment_df, metric).dropna()

    # 均值
    control_mean1 = np.mean(control_data1)
    control_mean2 = np.mean(control_data2)
    exp_mean = np.mean(exp_data)

    # t-test
    _, p_value1 = stats.ttest_ind(control_data1, exp_data, equal_var=False)
    _, p_value2 = stats.ttest_ind(control_data2, exp_data, equal_var=False)

    # 合并为 DataFrame（方便画箱线图）
    plot_df = pd.DataFrame({
        'Value': pd.concat([exp_data, control_data1, control_data2], ignore_index=True),
        'Group': (['Experimental group'] * len(exp_data) +
                  ['Control group 1'] * len(control_data1) +
                  ['Control group 2'] * len(control_data2))
    })

    # 开始画图
    plt.figure(figsize=figsize)

    box = plt.boxplot(
        [exp_data, control_data1, control_data2],
        labels=[r'$ \mathcal{A}$', r'$ \mathcal{C}_1 $', r'$ \mathcal{C}_2 $'],
        patch_artist=True,
        showfliers=False,
        widths=0.6
    )

    # 颜色（和你原来的风格保持一致）
    colors = ['lightblue', 'lightgreen', 'lightcoral']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    # # 均值点
    # plt.scatter([1, 2, 3], [exp_mean, control_mean1, control_mean2],
    #             color='black', marker='D', zorder=3, label='Mean')

    # 轴标签
    plt.ylabel(metric)

    # 不同指标的坐标范围（沿用你原来的设定）
    if metric == 'DI':
        plt.ylim(-0.1, 0.1)
    if metric == 'DI_jing':
        plt.ylim(0, 0.2)
        plt.ylabel('DI#')
    if metric == 'DI_xing':
        plt.ylim(0, 0.1)
        plt.ylabel('DI*')
    if metric == 'DI5':
        plt.ylim(-0.1, 0.15)
        plt.ylabel(r'$ \mathrm{DI}_{5} $')
    if metric == 'mDI':
        plt.ylim(-40, 40)

    if metric == 'SDI':
        plt.ylim(-0.4, 1)
    if metric == 'SDI_jing':
        plt.ylim(0, 0.1)
        plt.ylabel('SDI#')
    if metric == 'SDI_xing':
        plt.ylim(0, 1)
        plt.ylabel('SDI*')
    if metric == 'SDI5':
        plt.ylim(0, 1)
        plt.ylabel(r'$ \mathrm{SDI}_{5} $')
    if metric == 'mSDI':
        plt.xlim(0.5, 3.5)
        plt.ylim(-20, 500)

    # p-value 注释
    plt.annotate(
        f'T-test (CG1 vs Exp): p = {p_value1:.3e}\n'
        f'T-test (CG2 vs Exp): p = {p_value2:.3e}',
        xy=(0.02, 0.95),
        xycoords='axes fraction',
        verticalalignment='top'
    )

    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(save_fig_path, dpi=400, bbox_inches='tight')
def plot_boxplot_comparison(metric, control_df1,  experiment_df, save_fig_path):
    """
    绘制三组数据的箱线图对比，并计算统计检验
    """
    # 字体设置
    plt.rcParams.update({
        'font.size': 14,
        'axes.titlesize': 18,
        'axes.labelsize': 18,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'legend.fontsize': 16,
    })
    plt.rc('font', family='Times New Roman')
    figsize = (8, 6)
    plt.figure(figsize=figsize)

    # 准备数据
    control_data1 = get_last_non_null_values(control_df1, metric).dropna()
    exp_data = get_last_non_null_values(experiment_df, metric).dropna()

    # t-test
    _, p_value1 = stats.ttest_ind(control_data1, exp_data, equal_var=False)

    # 合并为 DataFrame（方便画箱线图）
    plot_df = pd.DataFrame({
        'Value': pd.concat([exp_data, control_data1], ignore_index=True),
        'Group': (['Experimental group'] * len(exp_data) +
                  ['Control group 1'] * len(control_data1))
    })

    # 画箱线图
    box = plt.boxplot(
        [exp_data, control_data1],
        labels=[r'$ \mathcal{B}$', r'$ \mathcal{C}_\mathcal{B} $'],
        patch_artist=True,
        showmeans=False,
        showfliers=False,
        widths=0.3,
        meanprops=dict(marker='D', markerfacecolor='gold', markeredgecolor='black', markersize=8),  # 自定义均值点
        medianprops=dict(color='black', linewidth=2)  # 中位数线
    )

    # 箱子颜色及四分位线加粗
    colors = ['red', 'blue']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
    # 须（min/max线）
    for whisker in box['whiskers']:
        whisker.set(color='black', linewidth=1.5)
    # 须末端横线
    for cap in box['caps']:
        cap.set(color='black', linewidth=1.5)
    # 异常点
    for flier, color in zip(box['fliers'], colors):
        flier.set(marker='o', color=color, alpha=0.6)

    if metric=='SDI':
        y_max=0.8
        plt.ylim([-0.2,1.2])
        plt.ylabel(metric)
    if metric=='SDI_xing':
        y_max=0.8
        plt.ylim([-0.2,1.2])
        plt.ylabel('SDI*')
    if metric=='SDI5':
        y_max=0.8
        plt.ylim([-0.2,1.2])
        plt.ylabel(r'$ \mathrm{SDI}_{5} $')

    if metric=='mSDI':
        y_max=1.2
        plt.ylabel('mSDI')
    if metric=='DI':
        y_max=0.1
        height=0.02
        plt.ylabel(metric)
        plt.ylim([-0.1,0.15])
    if metric=='DI_xing':
        y_max=0.25
        height=0.02
        plt.ylabel('DI*')
    if metric=='DI5':
        y_max=0.28
        height=0.02
        plt.ylim([-0.1,0.4])
        plt.ylabel(r'$ \mathrm{DI}_{5} $')
    if metric=='mDI':
        plt.ylabel('mDI')

    # 轴标签
    #添加显著性标注
    # 这里以 t-test 举例
    def add_significance(x1, x2, y, text, height=0.1):
        """x1, x2:箱子索引(1开始)，y:高度，text:标记内容"""
        plt.plot([x1, x1, x2, x2], [y, y+height, y+height, y], lw=1.5, c='black')
        plt.text((x1+x2)/2, y+height, text, ha='center', va='bottom', fontsize=14)

    # 比较 exp vs control group 1
    def pval_to_stars(p):
        if p < 0.001:
            return '***'
        elif p < 0.01:
            return '**'
        elif p < 0.05:
            return '*'
        else:
            return 'NS'
    # y_max = max(np.max(exp_data), np.max(control_data1))
    # add_significance(1, 2, y_max+0.04, pval_to_stars(p_value1))# sdi
    add_significance(1, 2, y_max+0.01, pval_to_stars(p_value1),height) #di

    
    plt.tight_layout()
    plt.savefig(save_fig_path, dpi=400, bbox_inches='tight')


def compare_experimental_and_controls(name,index_name,save_fig_path):
    # 使用示例
    if name=='DI' :
        experiment_df = jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_DI_and_its_variants_nonobel.jsonl')
        control_df1=jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_DI_and_its_variants_nonobel.jsonl')
        # control_df2=jsonl_DI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control2_group_DI_and_its_variants_nonobel.jsonl')

    if name=='SDI':
        experiment_df = jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/experimental_group_SDI_and_its_variants_nonobel.jsonl')
        control_df1=jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control1_group_SDI_and_its_variants_nonobel.jsonl')
        # control_df2=jsonl_SDI_index_to_dataframe('alt_disruption/reviwer1/new_data_results/control2_group_SDI_and_its_variants_nonobel.jsonl')

    # print(experiment_df)
    # control_data2 = get_last_non_null_values(control_df2, index_name)
    # plot_density_comparison(index_name,control_df1, control_df2,experiment_df ,save_fig_path )
    plot_boxplot_comparison(index_name, control_df1, experiment_df, save_fig_path)
if __name__ == '__main__':
    index_name=['DI_xing','DI','DI5']
    # index_name=['SDI_xing','SDI','SDI5']
    for index in index_name:
        compare_experimental_and_controls('DI', index, f'alt_disruption/reviwer1/new_data_results/figs/compare_focal_control_{index}_box_nonobel.png')
    