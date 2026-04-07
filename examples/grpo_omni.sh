#!/bin/bash
set -x

# ================= Environment Variables =================
export OPENAI_API_KEY="your-api-key-here"
export BASE_URL="your-api-base-url"
export PYTHONUNBUFFERED=1
export TEXMFVAR=$HOME/.texlive/texmf-var
export TEXMFCONFIG=$HOME/.texlive/texmf-config
export TEXMFHOME=$HOME/texmf

mkdir -p $TEXMFVAR $TEXMFCONFIG $TEXMFHOME

# ================= Path Configuration =================
# Your SFT model path
MODEL_PATH="path/to/your/omnidiagram-sft-model"
# Experiment name
EXP_NAME="qwen2_5_vl_3b_omni_grpo"
# Your RL data directory (parquet format with Viva questions)
DATA_DIR="path/to/your/rl_data"

# ================= Launch =================
python3 -m verl.trainer.main \
    config=examples/config.yaml \
    data.train_files=$DATA_DIR/ready \
    data.rollout_batch_size=4 \
    data.mini_rollout_batch_size=4 \
    data.format_prompt=./examples/format_prompt/r1v.jinja \
    worker.actor.model.model_path=${MODEL_PATH} \
    worker.actor.fsdp.torch_dtype=bf16 \
    worker.actor.optim.strategy=adamw_bf16 \
    worker.actor.global_batch_size=4 \
    worker.actor.micro_batch_size_per_device_for_update=1 \
    worker.actor.micro_batch_size_per_device_for_experience=1 \
    worker.rollout.max_num_batched_tokens=16384 \
    worker.rollout.gpu_memory_utilization=0.3 \
    worker.rollout.tensor_parallel_size=4 \
    worker.rollout.n=2 \
    algorithm.adv_estimator=grpo \
    algorithm.disable_kl=True \
    worker.reward.reward_function=./examples/reward_function/omni_rewards/entry_point.py:compute_score \
    trainer.experiment_name=${EXP_NAME} \
    trainer.val_before_train=False \
    trainer.project_name="EasyR1-Omni-RL" \
    trainer.nnodes=1 \
    trainer.n_gpus_per_node=4 \
    trainer.total_epochs=1 \
    trainer.save_freq=5 \
    trainer.save_limit=5 \
    trainer.save_checkpoint_path=./checkpoints/${EXP_NAME} \
    trainer.logger=['console'] \
