#!/bin/bash

# ================= Path Configuration =================
# Base model: Qwen2.5-VL-3B-Instruct or Qwen2.5-VL-7B-Instruct
MODEL_PATH="Qwen/Qwen2.5-VL-3B-Instruct"
# Your SFT training dataset (jsonl format)
DATASET_PATH="path/to/your/sft_train_data.jsonl"
# Output directory for checkpoints
OUTPUT_DIR="./saves/omnidiagram-3b-sft"

# ================= SFT Training =================
PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True' \
NPROC_PER_NODE=8 \
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
MAX_PIXELS=1003520 \
swift sft \
    --model $MODEL_PATH \
    --dataset $DATASET_PATH \
    --train_type full \
    --torch_dtype bfloat16 \
    --gradient_checkpointing true \
    --vit_gradient_checkpointing true \
    --num_train_epochs 2 \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 1 \
    --split_dataset_ratio 0 \
    --learning_rate 2e-5 \
    --deepspeed zero2 \
    --freeze_vit false \
    --freeze_aligner false \
    --gradient_accumulation_steps 4 \
    --eval_steps 100000 \
    --save_steps 1000 \
    --save_total_limit 5 \
    --logging_steps 10 \
    --max_length 18432 \
    --output_dir $OUTPUT_DIR \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 8
