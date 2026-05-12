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
    
    return last_values

def plot_density_comparison(metric, control_df, experiment_df,save_fig_path):
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
        'axes.titlesize': 16,      # 标题字体大小
        'axes.labelsize': 16,      # 坐标轴标签字体大小
        'xtick.labelsize': 16,     # X轴刻度标签字体大小
        'ytick.labelsize': 16,     # Y轴刻度标签字体大小
        'legend.fontsize': 14,     # 图例字体大小
    })
    plt.rc('font',family='Times New Roman') 
    figsize=(8, 6)
    # 准备数据
    control_data = get_last_non_null_values(control_df, metric).dropna()
    data2 = get_last_non_null_values(experiment_df, metric).dropna()
    print(data2)
    # 计算均值和统计检验
    control_mean, mean2 = np.mean(control_data), np.mean(data2)
    t_stat, p_value = stats.ttest_ind(control_data, data2, equal_var=False)
    
    # 创建图形
    plt.figure(figsize=figsize)
    
    # 绘制密度图
    sns.histplot(control_data, kde=True, color='blue', label=f'Control group (mean={control_mean:.3e})', stat="density", linestyle='--' )
    sns.histplot(data2, kde=True, color='red',  label=f'Experimental group (mean={mean2:.3e})', stat="density", linewidth=0)
    # 绘制密度图
    # sns.kdeplot(data1, label=f"Control papers (mean={mean1:.3e})", fill=True)
    # sns.kdeplot(data2, label=f"Experimental groups (mean={mean2:.3e})", fill=True)
    # 在图中添加平均值
    plt.axvline(control_mean, color='blue', linestyle='--',linewidth=2)
    plt.axvline(mean2, color='red', linestyle=':',linewidth=2)
    if metric=='DI':
        plt.ylim(0,100)
        plt.xlim(-0.2,0.2)
        plt.xlabel(metric)
    if metric=='DI_jing':
        plt.ylim(0,70)
        plt.xlim(0,0.3)
        plt.xlabel('DI#')
    if metric=='DI_xing':
        plt.ylim(0,250)
        plt.xlim(0,0.1)
        plt.xlabel('DI*')
    if metric=='DI5':
        plt.xlim(-0.1,0.2)
        plt.ylim(0,180)
        plt.xlabel(r'$ \mathrm{DI}_{5} $')
    if metric=='mDI':
        plt.ylim(0,1)
        plt.xlim(-40,40)
        plt.xlabel('mDI')


    if metric=='SDI':
        plt.ylim(0,18)
        plt.xlim(-0.4,1)
        plt.xlabel(metric)
    if metric=='SDI_jing':
        plt.ylim(0,450)
        plt.xlim(0,0.1)
        plt.xlabel('SDI#')
    if metric=='SDI_xing':
        plt.ylim(0,30)
        plt.xlim(0,1)
        plt.xlabel('SDI*')
    if metric=='SDI5':
        plt.xlim(0,1)
        plt.ylim(0,30)
        plt.xlabel(r'$ \mathrm{SDI}_{5} $')
    if metric=='mSDI':
        # plt.ylim(0,1)
        plt.xlim(-20,500)
        plt.xlabel('mSDI')
    
    plt.ylabel("Density")
    
    # 添加统计信息
    plt.annotate(f"T-test p-value = {p_value:.3e}", 
                 xy=(0.55, 0.7), xycoords='axes fraction')
    
    # 添加图例
    plt.legend()
    
    # 显示图形
    plt.savefig(save_fig_path,dpi=400,bbox_inches='tight')

def compare_experimental_and_controls(name,index_name,save_fig_path):
    # 使用示例
    if name=='DI' :
        experiment_df = jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_DI_and_its_variants.jsonl')
        control_df=jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_DI_and_its_variants.jsonl')
    if name=='SDI':
        experiment_df = jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_SDI_and_its_variants.jsonl')
        control_df=jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_SDI_and_its_variants.jsonl')
    # print(experiment_df)

    plot_density_comparison(index_name,control_df, experiment_df ,save_fig_path )
if __name__ == '__main__':

    compare_experimental_and_controls('SDI','mSDI','alt_disruption/final_run_experiment/figs/compare_focal_control_mSDI.png')
    