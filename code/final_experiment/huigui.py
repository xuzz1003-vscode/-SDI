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
    experiment_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_DI_and_its_variants.jsonl')
    experiment_df_DI['label'] = 1
    control_df_DI = jsonl_DI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_DI_and_its_variants.jsonl')
    control_df_DI['label']=0

    experiment_df_SDI = jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_experimental_papers_SDI_and_its_variants.jsonl')

    control_df_SDI= jsonl_SDI_index_to_dataframe('alt_disruption/final_run_experiment/results/select_refs_control_papers_SDI_and_its_variants.jsonl')
    

    # 按年份提取数据
    experiment_DI = get_year_data(time, experiment_df_DI)
    experiment_SDI = get_year_data(time, experiment_df_SDI)
    control_DI = get_year_data(time, control_df_DI)
    control_SDI = get_year_data(time, control_df_SDI)

    # 合并数据
    focal_merge_df = pd.merge(experiment_DI, experiment_SDI, on='DOI', how='left')
    control_merge_df = pd.merge(control_DI, control_SDI, on='DOI', how='left')
    
    # 合并所有数据并清理缺失值
    all_data = pd.concat([control_merge_df, focal_merge_df])
    all_data['log_citations'] = np.log1p(all_data['citations'])  # log(1 + x)
    # 确保关键列没有缺失值
    required_cols = ['DOI', 'label'] + ['DI', 'citations']  # 添加其他必要列
    all_data = all_data.dropna(subset=required_cols)
    
    print(f"最终样本量: {len(all_data)}")
    print(f"标签分布:\n{all_data['label'].value_counts()}")
    print(f"缺失值检查:\n{all_data.isnull().sum()}")
    
    return all_data
def run_experiment(
    all_data,
    features=None,
    control_col='citations',
    n_sample=266,
    repetitions=100,
    use_control=True,
    seed=42
):
    """运行实验主函数"""
    features = features or ['DI']
    
    # 随机抽样
    sampled_datasets = random_sampling_experiment(
        all_data, n=n_sample, y_value=0, 
        repetitions=repetitions, seed=seed
    )
    
    # 收集指标
    all_metrics = {feature: [] for feature in features}

    
    for data in sampled_datasets:
        # print(data.shape)
        X = data[features + [control_col]] if use_control else data[features]
        y = data['label']
        
        for feature in features:
            if use_control:
                metrics = logistic_regression_with_control(X, y, [feature], control_col)
            else:
                metrics = logistic_regression_without_control(X, y, [feature])
            
            all_metrics[feature].append(metrics)
    
    # 计算平均指标
    mean_metrics_list = []
    for feature_name, result_list in all_metrics.items():
        mean_metrics = {
            'feature': feature_name,
            'accuracy': np.mean([r['accuracy'] for r in result_list]),
            'recall': np.mean([r['recall'] for r in result_list]),
            'f1_score': np.mean([r['f1_score'] for r in result_list]),
            'auc': np.mean([r['auc'] for r in result_list]),#不要
            'coefficient': np.mean(
                [r[feature_name] if use_control else r['coefficient'] 
                for r in result_list]
            )
        }
        if use_control:
            mean_metrics[control_col] = np.mean([r[control_col] for r in result_list])
        
        mean_metrics_list.append(mean_metrics)
    
    metrics_df = pd.DataFrame(mean_metrics_list).set_index('feature')
    
    # if output_path:
    #     metrics_df.to_csv(output_path)
    
    return metrics_df

if __name__ == '__main__':
    # 加载并预处理数据
    all_data = merge_data(10)
    
    # 运行不带控制变量的实验
    print("\n------ Without Citations ------")
    result_no_control = run_experiment(
        all_data=all_data,
        features=['DI','DI5','mDI','SDI','SDI5','mSDI'],
        use_control=False,
        repetitions=100,
        seed=42
    )
    print(result_no_control)
    
    # 运行带控制变量的实验
    print("\n------ With Citations ------")
    result_with_control = run_experiment(
        all_data=all_data,
        features=['DI','DI5','mDI','SDI','SDI5','mSDI'],
        use_control=True,
        repetitions=100,
        seed=42
    )
    print(result_with_control)