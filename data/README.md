# data 说明

这个目录只放三套最终实验对应的**必要原始输入文件**


## 已包含的数据

### `data/final_experiment/`

- `experiment_groups_dois.csv`
  主实验实验组 DOI 列表
- `papers_2_refs_doi.json`
  论文到参考文献 DOI 的映射
- `papers_2_puby.json`
  论文到发表年份的映射

这三份是主实验 `DI/SDI` 指标计算里最核心的结构化输入。

### `data/control_group2/`

- `select_controls_papers.json`
  控制组2筛选后的论文列表
- `select_control_altmetric_counts.jsonl`
  控制组2筛选后的 Altmetric 计数输入

### `data/breakthrough_nonobel/`

- `TypologyOfBreakthroughs_dataset.xlsx`
  突破性论文数据源
- `breakthrough_papers_refs.json`
  突破性论文参考文献映射
- `breakthrough_with_controls_cited_by_counts.json`
  突破性论文与控制组的 `cited_by_count` 配对结果
- `breakthrough_with_controls_twitter_user_counts.json`
  突破性论文与控制组的 `twitter_user_count` 配对结果
- `nobel_prize_with_controls_cited_by_counts.json`
- `nobel_prize_with_controls_twitter_user_counts.json`


## 没有放进来的大文件

下面这些文件没有复制进 `github-new/`，主要是因为体积过大，或者更像中间缓存：

- `final_run_experiment/data/all_papers_social_data.jsonl`
  约 810 MB
- `control_group_two_new/data/all_papers_social_data.jsonl`
  约 847 MB
- `reviewer1/data/breakthrough_controls_new.json`
  约 86 MB
- `reviewer1/data/nobel_prize_with_controls_new.json`
  约 62 MB
