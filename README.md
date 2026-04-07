# OmniDiagram: Advancing Unified Diagram Code Generation via Visual Interrogation Reward (ACL 2025 Main)

[![arXiv](https://img.shields.io/badge/arXiv-xxxx.xxxxx-b31b1b.svg?logo=arXiv)](https://arxiv.org/abs/xxxx.xxxxx) [![🤗 Models (HuggingFace)](https://img.shields.io/badge/Models-HuggingFace-FFD21E.svg?logo=huggingface&logoColor=yellow)](https://huggingface.co/Y36521478Y) [![🤗 Datasets (HuggingFace)](https://img.shields.io/badge/Datasets-HuggingFace-FFD21E.svg?logo=huggingface&logoColor=yellow)](https://huggingface.co/Y36521478Y)

This repository is the official implementation of [OmniDiagram: Advancing Unified Diagram Code Generation via Visual Interrogation Reward](https://arxiv.org/abs/xxxx.xxxxx).

> OmniDiagram: Advancing Unified Diagram Code Generation via Visual Interrogation Reward
>
> Haoyue Yang\*, Xuanle Zhao\*, Xuexin Liu\*, Feibang Jiang, Yao Zhu†
>
> Institute of Automation, Chinese Academy of Sciences; University of Chinese Academy of Sciences; Zhejiang University

## News

**[2025.x.x]** OmniDiagram has been accepted by **ACL 2025 Main**.

## Overview

The paradigm of programmable diagram generation is evolving rapidly, playing a crucial role in structured visualization. However, most existing studies are confined to a narrow range of task formulations and language support. In this work, we propose **OmniDiagram**, a unified framework that incorporates diverse diagram code languages and task definitions. To address the challenge of aligning code logic with visual fidelity in Reinforcement Learning (RL), we introduce a novel visual feedback strategy named **Visual Interrogation Verifies All (Viva)**. Unlike brittle syntax-based rules or pixel-level matching, Viva rewards the visual structure of rendered diagrams through a generative approach. Furthermore, we construct **M3²Diagram**, the first large-scale diagram code generation dataset, containing over 196k high-quality instances.

![main](fig/main.png)

## Models

| Model | Size | Download Link |
| ---- | ---- | ---- |
| OmniDiagram-3B (SFT) | 4B | [HuggingFace](https://huggingface.co/Y36521478Y/omnidiagram_3B_sft_2epoch) |
| OmniDiagram-3B (RL) | 4B | [HuggingFace](https://huggingface.co/Y36521478Y/omnidiagram_3B_rl) |
| OmniDiagram-7B (SFT) | 8B | [HuggingFace](https://huggingface.co/Y36521478Y/omnidiagram_7B_sft_2epoch) |
| OmniDiagram-7B (RL) | 8B | [HuggingFace](https://huggingface.co/Y36521478Y/omnidiagram_7B_rl) |

## Data

| Dataset | Download Link |
| ---- | ---- |
| M3²Diagram (SFT) | [HuggingFace](https://huggingface.co/datasets/Y36521478Y/omnidiagram_train_sft) |
| M3²Diagram (RL) | [HuggingFace](https://huggingface.co/datasets/Y36521478Y/omnidiagram_train_rl) |
| M3²Bench (Test) | [HuggingFace](https://huggingface.co/datasets/Y36521478Y/omnidiagram_test) |

## Installation

1. Clone this repo
```bash
git clone https://github.com/Haoyue-Yang/OmniDiagram.git
cd OmniDiagram
```

2. Create environment
```bash
conda create -n omnidiagram python=3.10 -y
conda activate omnidiagram
pip install --upgrade pip
pip install -e .
```

3. Additional packages required for training
```bash
pip install -e ".[train]"
pip install flash-attn --no-build-isolation
```

## Train

The whole training process consists of two stages. The base model `Qwen2.5-VL-3B-Instruct` or `Qwen2.5-VL-7B-Instruct` should be downloaded first.

For **SFT**, run
```bash
bash scripts/train/sft.sh
```

For **RL (Viva)**, run
```bash
bash scripts/train/rl_viva.sh
```

Please change the model path to your local path. See the corresponding `.sh` file for details.

Our implementation leverages [ms-swift](https://github.com/modelscope/ms-swift) and [EasyR1](https://github.com/hiyouga/EasyR1).

## Inference

Please see `inference.py` for details.

## Results

OmniDiagram consistently surpasses competitive open-source baselines across all tasks on M3²Bench and various external diagrammatic benchmarks. Please refer to our paper for detailed performance.

![results](fig/results.png)

## Contact

For any questions, you can contact [yanghaoyue2024@ia.ac.cn](mailto:yanghaoyue2024@ia.ac.cn).

## Citation

If you find this work useful, consider giving this repository a star and citing our paper as follows:
```bibtex
@inproceedings{yang2025omnidiagram,
  title={OmniDiagram: Advancing Unified Diagram Code Generation via Visual Interrogation Reward},
  author={Yang, Haoyue and Zhao, Xuanle and Liu, Xuexin and Jiang, Feibang and Zhu, Yao},
  booktitle={Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (ACL)},
  year={2025}
}
```

## Acknowledgement

The training code is based on [ms-swift](https://github.com/modelscope/ms-swift) and [EasyR1](https://github.com/hiyouga/EasyR1). Thanks for these great works and open sourcing!
