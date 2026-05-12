import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from compare_control_focal_papers_DI import jsonl_DI_index_to_dataframe, jsonl_SDI_index_to_dataframe
# from sklearn.impute import IterativeImputer

def get_year_data(time, df):
    """提取指定年份的数据并删除Year列"""
    year_data = df[df['Year'] == time].copy()
    year_data.drop('Year', axis=1, inplace=True)
    return year_data

def handle_missing_values(X, y):
    """统一处理缺失值"""
    # 获取非缺失值的索引
    valid_idx = X.notna().all(axis=1)
    X_clean = X[valid_idx].copy()
    y_clean = y[valid_idx].copy()
    
    # # 如果还有缺失值，使用多重插补
    # if X_clean.isna().any().any():
    #     imputer = IterativeImputer(random_state=42)
    #     X_clean[:] = imputer.fit_transform(X_clean)
    
    return X_clean, y_clean

def logistic_regression_with_control(X, y, feature_cols, control_col):
    """带控制变量的逻辑回归"""
    # 合并特征列
    all_cols = feature_cols + [control_col]
    X_selected = X[all_cols].copy()
    
    # 处理缺失值
    X_clean, y_clean = handle_missing_values(X_selected, y)
    # print(len(X_clean),len(y_clean))
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean)
    
    # 分割数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_clean, test_size=0.2, random_state=42
    )
    
    # 训练模型
    model = LogisticRegression(class_weight='balanced', max_iter=1000)
    model.fit(X_train, y_train)
    
    # 评估模型
    y_pred = model.predict(X_test)
    # print(y_pred)
    y_pred_prob = model.predict_proba(X_test)[:, 1]
    # print(y_pred_prob)
    
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "auc": roc_auc_score(y_test, y_pred_prob),
        **dict(zip(all_cols, model.coef_[0]))
    }

def logistic_regression_without_control(X, y, feature_cols):
    """不带控制变量的逻辑回归"""
    X_selected = X[feature_cols].copy()
    
    # 处理缺失值
    X_clean, y_clean = handle_missing_values(X_selected, y)
    # print(len(X_clean),len(y_clean))
    
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean)
    
    # 分割数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_clean, test_size=0.2, random_state=42
    )
    
    # 训练模型
    model = LogisticRegression(class_weight='balanced', max_iter=1000)
    model.fit(X_train, y_train)
    
    # 评估模型
    y_pred = model.predict(X_test)
    y_pred_prob = model.predict_proba(X_test)[:, 1]
    
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "auc": roc_auc_score(y_test, y_pred_prob),
        "coefficient": model.coef_[0][0]
    }
    # -----------------------------
    # 均值 ± 1.96 × SE
    # -----------------------------
def mean_ci_se(values, z=1.96):
    """
    均值 ± z * SE（标准误）
    """
    values = np.asarray(values)
    mean = np.mean(values)
    std = np.std(values, ddof=1)      # 样本标准差
    se = std / np.sqrt(len(values))   # 标准误
    lower = mean - z * se
    upper = mean + z * se
    return mean, lower, upper

def random_sampling_experiment(df, n, y_value, repetitions, seed):
    """随机抽样实验"""
    np.random.seed(seed)
    y_one_data = df[df['label'] == 1]
    y_zero_data = df[df['label'] == y_value]
    
    return [
        pd.concat([y_one_data, y_zero_data.sample(n=n, random_state=seed+i)])
        for i in range(repetitions)
    ]

def merge_data(time):
    """合并实验组和对照组数据"""
    # 加载数据
    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_DI_and_its_variants.jsonl')
    control_df1_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_DI_and_its_variants.jsonl')
    control_df2_DI = jsonl_DI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_DI_and_its_variants_group2.jsonl')
    experiment_df_DI['label'] = 1
    control_df1_DI['label']=0
    control_df2_DI['label']=0
    
    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/experimental_papers_SDI_and_its_variants.jsonl')
    control_df1_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_one/results/control_papers_SDI_and_its_variants.jsonl')
    control_df2_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/control_group_two_new/results/control_papers_SDI_and_its_variants_group2.jsonl')

    # 按年份提取数据
    experiment_DI = get_year_data(time, experiment_df_DI)
    experiment_SDI = get_year_data(time, experiment_df_SDI)
    control1_DI = get_year_data(time, control_df1_DI)
    control1_SDI = get_year_data(time, control_df1_SDI)
    control2_DI = get_year_data(time, control_df2_DI)
    control2_SDI = get_year_data(time, control_df2_SDI)

    # 合并数据
    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, on='DOI', how='left')
    control1_merge_df = pd.merge(control1_DI, control1_SDI, on='DOI', how='left')
    control2_merge_df = pd.merge(control2_DI, control2_SDI, on='DOI', how='left')
    
    # 合并所有数据并清理缺失值
    all_data1 = pd.concat([control1_merge_df, focal_merge_df])
    all_data1['log_citations'] = np.log1p(all_data1['citations'])  # log(1 + x)
    # 确保关键列没有缺失值
    required_cols1 = ['DOI', 'label'] + ['DI', 'citations']  # 添加其他必要列
    all_data1 = all_data1.dropna(subset=required_cols1)

    all_data2 = pd.concat([control2_merge_df, focal_merge_df])
    all_data2['log_citations'] = np.log1p(all_data2['citations'])  # log(1 + x)
    # 确保关键列没有缺失值
    required_cols2 = ['DOI', 'label'] + ['DI', 'citations']  # 添加其他必要列
    all_data2 = all_data2.dropna(subset=required_cols2)
    
    print(f"最终样本量: {len(all_data1),len(all_data1)}")
    print(f"标签分布:\n{all_data1['label'].value_counts(),all_data2['label'].value_counts()}")
    print(f"缺失值检查:\n{all_data1.isnull().sum(),all_data2.isnull().sum()}")
    
    return all_data1,all_data2
def run_experiment(
    all_data,
    features=None,
    control_col='citations',
    n_sample=266,
    repetitions=100,
    use_control=True,
    seed=42,
    z=1.96
):
    """
    运行随机抽样 + 逻辑回归实验
    输出：mean, SE, z * SE（z=1.96 对应 95% 正态近似）
    """
    features = features or ['DI']
    np.random.seed(seed)

    # =============================
    # 工具函数：mean, SE, z*SE
    # =============================
    def mean_se_z(values):
        values = np.asarray(values)
        mean = np.mean(values)
        se = np.std(values, ddof=1) / np.sqrt(len(values))
        z_se = z * se
        return mean, se, z_se

    # =============================
    # 随机抽样
    # =============================
    sampled_datasets = random_sampling_experiment(
        all_data,
        n=n_sample,
        y_value=0,
        repetitions=repetitions,
        seed=seed
    )

    # =============================
    # 收集每次实验结果
    # =============================
    all_metrics = {feature: [] for feature in features}

    for data in sampled_datasets:
        y = data['label']

        for feature in features:
            if use_control:
                X = data[[feature, control_col]]
                metrics = logistic_regression_with_control(
                    X, y, [feature], control_col
                )
            else:
                X = data[[feature]]
                metrics = logistic_regression_without_control(
                    X, y, [feature]
                )

            all_metrics[feature].append(metrics)

    # =============================
    # 统计 mean / SE / z*SE
    # =============================
    results = []

    for feature_name, result_list in all_metrics.items():

        acc_mean, acc_se, acc_zse = mean_se_z(
            [r['accuracy'] for r in result_list]
        )
        rec_mean, rec_se, rec_zse = mean_se_z(
            [r['recall'] for r in result_list]
        )
        f1_mean, f1_se, f1_zse = mean_se_z(
            [r['f1_score'] for r in result_list]
        )
        auc_mean, auc_se, auc_zse = mean_se_z(
            [r['auc'] for r in result_list]
        )

        coef_values = [
            r[feature_name] if use_control else r['coefficient']
            for r in result_list
        ]
        coef_mean, coef_se, coef_zse = mean_se_z(coef_values)

        row = {
            'feature': feature_name,

            'accuracy_mean': acc_mean,
            'accuracy_se': acc_se,
            'accuracy_z_se': acc_zse,

            'recall_mean': rec_mean,
            'recall_se': rec_se,
            'recall_z_se': rec_zse,

            'f1_mean': f1_mean,
            'f1_se': f1_se,
            'f1_z_se': f1_zse,

            'auc_mean': auc_mean,
            'auc_se': auc_se,
            'auc_z_se': auc_zse,

            'coef_mean': coef_mean,
            'coef_se': coef_se,
            'coef_z_se': coef_zse,
        }

        if use_control:
            ctrl_values = [r[control_col] for r in result_list]
            ctrl_mean, ctrl_se, ctrl_zse = mean_se_z(ctrl_values)
            row.update({
                f'{control_col}_mean': ctrl_mean,
                f'{control_col}_se': ctrl_se,
                f'{control_col}_z_se': ctrl_zse
            })

        results.append(row)

    results_df = pd.DataFrame(results).set_index('feature')
    return results_df


if __name__ == '__main__':
    # 加载并预处理数据
    all_data1,all_data2 = merge_data(10)
    
    # 运行不带控制变量的实验
    print("\n------ Without Citations ------")
    result_no_control = run_experiment(
        all_data=all_data1,
        features=['DI','DI5','mDI','SDI','SDI5','mSDI'],
        use_control=False,
        repetitions=100,
        seed=42
    )
    result_no_control.to_csv("alt_disruption/control_group_two_new/figs/control1_no_citation.csv")
    
    # 运行带控制变量的实验
    print("\n------ With Citations ------")
    result_with_control = run_experiment(
        all_data=all_data1,
        features=['DI','DI5','mDI','SDI','SDI5','mSDI'],
        use_control=True,
        repetitions=100,
        seed=42
    )
    # print(result_with_control)
    result_with_control.to_csv("alt_disruption/control_group_two_new/figs/control1_with_citation.csv")