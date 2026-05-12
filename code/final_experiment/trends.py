import pandas as pd
import numpy as np
from compare_control_focal_papers_DI import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe, get_all_last_metrics
import json
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

def get_year_data(time, df):
    year_to_data = {year: group for year, group in df.groupby('Year')}
    data = year_to_data[time]
    del data['Year']
    return data

def merge_data(time):
    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_DI_and_its_variants.jsonl')
    experiment_df_DI['label'] = 1
    control_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_DI_and_its_variants.jsonl')
    control_df_DI['label'] = 0

    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_SDI_and_its_variants.jsonl')
    control_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_SDI_and_its_variants.jsonl')
    
    print('---------------experimental groups----------------------------------')
    experiment_DI = get_year_data(time, experiment_df_DI)
    experiment_SDI = get_year_data(time, experiment_df_SDI)
    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    
    print('---------------control groups----------------------------------')
    control_DI = get_year_data(time, control_df_DI)
    control_SDI = get_year_data(time, control_df_SDI)
    control_merge_df = pd.merge(control_DI, control_SDI, left_on='DOI', right_on='DOI', how='left')

    # print('------------------合并数据----------------------------------')
    # all_data = pd.concat([control_merge_df, focal_merge_df])
    return focal_merge_df,control_merge_df

def calculate_stats(df):
    """Calculate mean and standard error for focal papers (label=1)"""    
    # Calculate mean
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    means = df[numeric_cols].mean()
    
    # Calculate standard error (SEM)
    sems = df[numeric_cols].sem()
    
    return means, sems

def plot_dual_axis_with_errors(all_means, all_sems, index_list):
    """绘制双坐标轴带误差带的折线图"""
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'mathtext.fontset': 'stix',
        'axes.labelsize': 16,
        'axes.titlesize': 14
    })
    
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    # DI plot (left axis)
    color_di = '#FF2C00'  # 大红
    line_di = ax1.plot(
        all_means.index,
        all_means['DI'],
        label=r'$\mathrm{DI}$',
        color=color_di,
        marker='o',
        markersize=8,
        linewidth=2,
        linestyle='-'
    )
    ax1.fill_between(
        all_means.index,
        all_means['DI'] - all_sems['DI'],
        all_means['DI'] + all_sems['DI'],
        color=color_di,
        alpha=0.2
    )
    # ax1.set_ylim(-0.009,-0.001) #所有
    # ax1.set_ylim(-0.006,0.006) #核心
    ax1.set_ylim(-0.01,-0.001) #所有
    ax1.set_xlabel('Publication age', fontweight='bold')
    ax1.set_ylabel(r'$\mathrm{DI}$', fontweight='bold')
    ax1.tick_params(axis='y')
    
    # SDI plot (right axis)
    ax2 = ax1.twinx()
    color_sdi = '#648FFF'  # 蓝色
    line_sdi = ax2.plot(
        all_means.index,
        all_means['SDI'],
        label=r'$\mathrm{SDI}$',
        color=color_sdi,
        marker='s',
        markersize=8,
        linewidth=2,
        linestyle='--'
    )
    ax2.fill_between(
        all_means.index,
        all_means['SDI'] - all_sems['SDI'],
        all_means['SDI'] + all_sems['SDI'],
        color=color_sdi,
        alpha=0.2
    )
    # ax2.set_ylim(0.09,0.16)
    # ax2.set_ylim(0.42,0.58)
    ax2.set_ylim(0.06,0.13)
    ax2.set_ylabel(r'$\mathrm{SDI}$', fontweight='bold')
    ax2.tick_params(axis='y')
    
    # Combine legends
    lines = line_di + line_sdi
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right', frameon=True, framealpha=0.8)
    
    plt.tight_layout()
    plt.savefig('alt_disruption/final_run_experiment/figs/mean_index_trend_with_errors.png', dpi=300, bbox_inches='tight')

def plot_trend(focal_all_means, focal_all_sems,control_all_means, control_all_sems,name):
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'mathtext.fontset': 'stix',
        'axes.labelsize': 16,
        'axes.titlesize': 14
    })
    
    fig, ax1 = plt.subplots(figsize=(7, 5))
    
    # DI plot (left axis)
    color_di = '#d62728' # 大红
    focal_di = ax1.plot(
        focal_all_means.index,
        focal_all_means[name],
        label='Experimental groups',
        color=color_di,
        marker='+',
        markersize=10,
        linewidth=1.5,
        linestyle='-'
    )
    ax1.fill_between(
        focal_all_means.index,
        focal_all_means[name] - focal_all_sems[name],
        focal_all_means[name] + focal_all_sems[name],
        color=color_di,
        alpha=0.1
    )

    color_sdi = '#1f77b4'  # 蓝色
    control_di = ax1.plot(
        control_all_means.index,
        control_all_means[name],
        label='Control groups',
        color=color_sdi,
        marker='o',
        markersize=8,
        linewidth=1.5,
        linestyle='--'
    )
    ax1.fill_between(
        control_all_means.index,
        control_all_means[name] - control_all_sems[name],
        control_all_means[name] + control_all_sems[name],
        color=color_sdi,
        alpha=0.1
    )
    ax1.set_xlabel('Publication age')
    ax1.set_ylabel(name)
    ax1.legend()
    ax1.grid(visible=True, linestyle='--', linewidth=0.5, alpha=0.7)
    # ax1.set_ylim(-0.01,0.006)#DI
    ax1.set_ylim(0,0.6)
 
    
    plt.tight_layout()
    plt.savefig(f'alt_disruption/final_run_experiment/figs/{name}_trends.png', dpi=300, bbox_inches='tight')




if __name__ == '__main__':
    # 存储所有年份的结果
    focal_all_means = pd.DataFrame()
    focal_all_sems = pd.DataFrame()
    control_all_means = pd.DataFrame()
    control_all_sems = pd.DataFrame()
    index_list = ['DI', 'SDI']
    
    for y in range(0, 11):
        focal_merge_df,control_merge_df = merge_data(y)
        focal_year_mean, focal_year_sem = calculate_stats(focal_merge_df)
        focal_all_means[y] = focal_year_mean
        focal_all_sems[y] = focal_year_sem

        control_year_mean, control_year_sem = calculate_stats(control_merge_df)
        control_all_means[y] = control_year_mean
        control_all_sems[y] = control_year_sem
    
    
    # 转置DataFrame以便绘图
    focal_all_means = focal_all_means.T
    focal_all_sems = focal_all_sems.T
    focal_all_means.index.name = 'Year'
    focal_all_sems.index.name = 'Year'

    control_all_means = control_all_means.T
    control_all_sems = control_all_sems.T
    control_all_means.index.name = 'Year'
    control_all_sems.index.name = 'Year'
    
    # 绘制趋势图
    plot_trend(focal_all_means, focal_all_sems,control_all_means, control_all_sems,'SDI')