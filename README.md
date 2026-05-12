# github

## 目录结构

```text
github-new/
├── code/
│   ├── final_experiment/
│   ├── control_group2/
│   └── breakthrough_nonobel/
├── results/
│   ├── final_experiment/
│   ├── control_group2/
│   └── breakthrough_nonobel/
├── data/
│   ├── final_experiment/
│   ├── control_group2/
│   ├── breakthrough_nonobel/
│   └── README.md
├── figs/
│   ├── final_experiment/
│   ├── control_group2/
│   └── breakthrough_nonobel/
└── tools/
```

## 结果文件

### 1. final_experiment


- `results/final_experiment/select_refs_control_papers_DI_and_its_variants.jsonl`
- `results/final_experiment/select_refs_control_papers_SDI_and_its_variants.jsonl`
- `results/final_experiment/select_refs_experimental_papers_DI_and_its_variants.jsonl`
- `results/final_experiment/select_refs_experimental_papers_SDI_and_its_variants.jsonl`

样本规模：

- 控制组1：4019 篇
- 实验组：266 篇

### 2. control_group2

- `results/control_group2/control_papers_DI_and_its_variants_group2.jsonl`
- `results/control_group2/control_papers_SDI_and_its_variants_group2.jsonl`

样本规模：

- 控制组2：3320 篇

### 3. breakthrough_nonobel

- `results/breakthrough_nonobel/control1_group_DI_and_its_variants_nonobel.jsonl`
- `results/breakthrough_nonobel/control1_group_SDI_and_its_variants_nonobel.jsonl`
- `results/breakthrough_nonobel/experimental_group_DI_and_its_variants_nonobel.jsonl`
- `results/breakthrough_nonobel/experimental_group_SDI_and_its_variants_nonobel.jsonl`

样本规模：

- 控制组：210 篇
- 实验组：48 篇

## 代码说明

### `code/final_experiment/`

保留了主实验的核心脚本：

- `compute_control_DI_and_its_variants.py`
- `compute_focal_DI_and_its_variants.py`
- `compute_sdi_and_its_varinants.py`
- `select_refs_over_10.py`

以及部分分析脚本：

- `compare_control_focal_papers_DI.py`
- `rank_top10.py`
- `trends.py`
- `huigui.py`
- `Statistics_for_index_and_corr.py`
- `ranking_density_and_trends.py`

### `code/control_group2/`

保留了控制组2对应的核心脚本：

- `compute_DI_and_its_variants.py`
- `compute_sdi_and_its_varinants.py`

以及部分分析脚本：

- `compare_control_focal_papers_DI.py`
- `rank_top10.py`
- `trends.py`
- `huigui.py`
- `Statistics_for_index_and_corr.py`
- `ranking_density_and_trends.py`

### `code/breakthrough_nonobel/`

保留了突破性论文 `nonobel` 相关的核心脚本和部分实验脚本：

- `compute_DI_and_its_variants_7.py`
- `compute_nobel_sdi_6.py`
- `compare_control_focal_papers_DI_8.py`
- `rank_top10_9.py`
- `huigui_11.py`

## 原始数据

`data/` 



