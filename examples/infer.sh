#!/bin/bash

# ================= Path Configuration =================
# Your model path (SFT or RL checkpoint)
MODEL_PATH="path/to/your/omnidiagram-model"
# Input dataset (jsonl format)
INPUT_FILE="path/to/your/test_data.jsonl"
# Output result path
OUTPUT_FILE="path/to/your/result.json"

# ================= Inference =================
CUDA_VISIBLE_DEVICES=0,1,2,3 \
IMAGE_MAX_TOKEN_NUM=1000000 \
swift infer \
    --model "$MODEL_PATH" \
    --result_path "$OUTPUT_FILE" \
    --infer_backend vllm \
    --val_dataset "$INPUT_FILE" \
    --vllm_gpu_memory_utilization 0.8 \
    --vllm_tensor_parallel_size 4 \
    --vllm_max_model_len 20000 \
    --max_new_tokens 10000 \
    --temperature 0.1 \
    --model_type qwen2_5_vl \
    --vllm_limit_mm_per_prompt '{"image": 5, "video": 2}'
