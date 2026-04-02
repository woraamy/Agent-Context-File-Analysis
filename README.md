# Replication Package for "Agent READMEs: An Empirical Study of Context Files for Agentic Coding"

[![arXiv](https://img.shields.io/badge/arXiv-2511.12884-b31b1b.svg)](https://arxiv.org/abs/2511.12884)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-AgentREADMEs-yellow?logo=huggingface)](https://huggingface.co/datasets/hao-li/AgentREADMEs)

- Paper: https://arxiv.org/abs/2511.12884
- Dataset: https://huggingface.co/datasets/hao-li/AgentREADMEs

## Repository Structure

```
├── data_collector/       # Data collection from GitHub API
│   ├── repositories/     #   Repository metadata
│   ├── commits/          #   Commit history
│   └── sections/         #   Markdown structure analysis
├── classification/       # GPT-based content classification
├── datasets/             # Processed datasets (CSV)
├── raw_datasets/         # Raw data dumps
├── hf_dataset/           # Final combined dataset (Parquet & CSV)
├── extract_hf_dataset.py # Combines platform data into unified dataset
└── upload_to_hf.py       # Uploads dataset to HuggingFace Hub
```

## Setup

```bash
pip install -r requirements.txt
```

## Citation

```bibtex
@article{agentreadmes2025,
  title={Agent READMEs: An Empirical Study of Context Files for Agentic Coding},
  author={Worawalan Chatlatanagulchai and Hao Li and Yutaro Kashiwa and Brittany Reid and Kundjanasith Thonglek and Pattara Leelaprute and Arnon Rungsawang and Bundit Manaskasemsak and Bram Adams and Ahmed E. Hassan and Hajimu Iida},
  year={2025},
  url={https://arxiv.org/abs/2511.12884}
}
```
