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
    experiment_DI = get_year_data(time, experiment_df_DI)
    experiment_SDI = get_year_data(time, experiment_df_SDI)
    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, left_on='DOI', right_on='DOI', how='left')
    
    print('---------------control groups1----------------------------------')
    control1_DI = get_year_data(time, control_df1_DI)
    control1_SDI = get_year_data(time, control_df1_SDI)
    control1_merge_df = pd.merge(control1_DI, control1_SDI, left_on='DOI', right_on='DOI', how='left')

    print('---------------control groups2----------------------------------')
    control2_DI = get_year_data(time, control_df2_DI)
    control2_SDI = get_year_data(time, control_df2_SDI)
    control2_merge_df = pd.merge(control2_DI, control2_SDI, left_on='DOI', right_on='DOI', how='left')


    # print('------------------合并数据----------------------------------')
    # all_data = pd.concat([control_merge_df, focal_merge_df])
    return focal_merge_df,control1_merge_df,control2_merge_df

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

def plot_trend(focal_all_means, focal_all_sems,control_all_means1, control_all_sems1,control_all_means2, control_all_sems2,name):
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
        label='experimental group',
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
        control_all_means1.index,
        control_all_means1[name],
        label='control group 1',
        color=color_sdi,
        marker='o',
        markersize=6,
        linewidth=1.5,
        linestyle='--'
    )
    ax1.fill_between(
        control_all_means1.index,
        control_all_means1[name] - control_all_sems1[name],
        control_all_means1[name] + control_all_sems1[name],
        color=color_sdi,
        alpha=0.1
    )

    color_sdi = 'green'  
    control_di = ax1.plot(
        control_all_means2.index,
        control_all_means2[name],
        label='control group 2',
        color=color_sdi,
        marker='o',
        markersize=6,
        linewidth=1.5,
        linestyle='--'
    )
    ax1.fill_between(
        control_all_means2.index,
        control_all_means2[name] - control_all_sems2[name],
        control_all_means2[name] + control_all_sems2[name],
        color=color_sdi,
        alpha=0.1
    )
    ax1.set_xlabel('publication age')
    ax1.set_ylabel(name)
    ax1.legend()
    # ax1.grid(visible=True, linestyle='--', linewidth=0.5, alpha=0.7)
    # ax1.set_ylim(-0.01,0.006)#DI
    ax1.set_ylim(0,0.8)
    # ax1.set_ylim(-0.01, 0.1e-1)  # 设置 y 轴范围为 0 到 1.4e-3，0, 4e-4
    # ax1.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
 
    
    plt.tight_layout()
    plt.savefig(f'alt_disruption/control_group_two_new/figs/{name}_trends.png', dpi=300, bbox_inches='tight')




if __name__ == '__main__':
    # 存储所有年份的结果
    focal_all_means = pd.DataFrame()
    focal_all_sems = pd.DataFrame()
    control_all_means1 = pd.DataFrame()
    control_all_sems1 = pd.DataFrame()
    control_all_means2 = pd.DataFrame()
    control_all_sems2 = pd.DataFrame()
    index_list = ['DI', 'SDI']
    
    for y in range(0, 11):
        focal_merge_df,control1_merge_df,control2_merge_df = merge_data(y)
        focal_year_mean, focal_year_sem = calculate_stats(focal_merge_df)
        focal_all_means[y] = focal_year_mean
        focal_all_sems[y] = focal_year_sem

        control_year_mean1, control_year_sem1 = calculate_stats(control1_merge_df)
        control_all_means1[y] = control_year_mean1
        control_all_sems1[y] = control_year_sem1

        control_year_mean2, control_year_sem2 = calculate_stats(control2_merge_df)
        control_all_means2[y] = control_year_mean2
        control_all_sems2[y] = control_year_sem2
    
    
    
    # 转置DataFrame以便绘图
    focal_all_means = focal_all_means.T
    focal_all_sems = focal_all_sems.T
    focal_all_means.index.name = 'Year'
    focal_all_sems.index.name = 'Year'

    control_all_means1 = control_all_means1.T
    control_all_sems1 = control_all_sems1.T
    control_all_means1.index.name = 'Year'
    control_all_sems1.index.name = 'Year'

    control_all_means2 = control_all_means2.T
    control_all_sems2 = control_all_sems2.T
    control_all_means2.index.name = 'Year'
    control_all_sems2.index.name = 'Year'
    
    
    # 绘制趋势图
    plot_trend(focal_all_means, focal_all_sems,control_all_means1, control_all_sems1,control_all_means2, control_all_sems2,'SDI')
    print( focal_all_means,'\n',control_all_means1,'\n',control_all_means2)