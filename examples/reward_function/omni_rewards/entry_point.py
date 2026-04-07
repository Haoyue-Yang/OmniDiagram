import os
import sys
import json
import logging
import re
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# ================= 🔧 路径修复 =================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 引用你的打分器
from scorer_dia2code import score_one as score_func_dia2code
from scorer_text2code import score_one as score_func_text2code
from scorer_edit import score_one as score_func_edit

logger = logging.getLogger(__name__)

# ================= 🛠️ 辅助函数 =================

def format_reward(response: str) -> float:
    pattern = re.compile(r"<think>.*?</think>\s*<answer>.*?</answer>", re.DOTALL)
    format_match = re.fullmatch(pattern, response)
    return 1.0 if format_match else 0.0

def process_single_accuracy(args):
    """
    单个样本的 Accuracy 计算逻辑 (渲染 + VQA)
    对应你要求的 accuracy_reward
    """
    # 解包参数：这里接收的是清洗后的 response
    ground_truth, response = args
    
    # 1. 确定任务类型 (默认 dia2code)
    # 注意：ground_truth 在这里就是你的 meta 数据字典
    task_type = ground_truth.get("task_type", "dia2code")
    
    try:
        if task_type == "dia2code":
            return score_func_dia2code(ground_truth, response)
        elif task_type == "text2code":
            return score_func_text2code(ground_truth, response)
        elif task_type == "edit":
            return score_func_edit(ground_truth, response)
        else:
            return score_func_dia2code(ground_truth, response)
    except Exception as e:
        # 出错打印日志，给 0 分
        print(f"[Entry Point Error] Task: {task_type}, Error: {e}")
        return 0.0

# ================= 🚀 主入口 (更新后) =================

def compute_score(
    reward_inputs: List[Dict[str, Any]], 
    format_weight: float = 0.1,
    **kwargs
) -> List[Dict[str, float]]:
    """
    Args:
        reward_inputs: 一个 Batch 的数据，包含 'response' 和 'ground_truth'
        format_weight: 格式分权重
    Returns:
        List[Dict]: [{'overall': float, 'accuracy': float, 'format': float}, ...]
    """

    # 1. 数据准备与预处理 (Qwen2.5-VL 格式清洗)
    clean_responses = []
    ground_truths = []

    for item in reward_inputs:
        # A. 提取原始 response 并进行正则清洗
        raw_response = item.get("response", "")
        # handle qwen2.5vl-32b format artifact
        clean_response = re.sub(r"\s*(<|>|/)\s*", r"\1", raw_response)
        clean_responses.append(clean_response)
        
        # B. 提取 ground_truth
        gt = item.get("ground_truth", {})

        # =========== 👇👇👇 代码修改在这个位置 👇👇👇 ===========
        # ⚠️ 新增逻辑：如果 gt 是字符串 (JSON String)，必须反序列化为 Dict
        # 因为我们在 Parquet 里把它存成了 String，这里必须还原，否则后面取 task_type 会报错
        if isinstance(gt, str):
            try:
                gt = json.loads(gt)
            except Exception as e:
                # 如果解不开，打印前50个字符看看是啥
                print(f"[Reward Error] GT JSON 解析失败: {e} | 内容片段: {gt[:50]}...")
                gt = {} # 避免后续报错，给个空字典
        # =========== 👆👆👆 代码修改结束 👆👆👆 ===========

        ground_truths.append(gt)

    # 2. 并行计算 Accuracy (耗时操作)
    # 将 (ground_truth, clean_response) 打包传给线程池
    # 保持 max_workers=4 或你服务器合适的数量
    with ThreadPoolExecutor(max_workers=4) as executor:
        accuracy_scores = list(executor.map(process_single_accuracy, zip(ground_truths, clean_responses)))

    # 3. 组装最终结果
    scores = []
    for resp, acc_score in zip(clean_responses, accuracy_scores):
        # 计算 Format Score (本地 CPU 极快，无需并行)
        fmt_score = format_reward(resp)
        
        # 计算加权总分
        overall_score = (1 - format_weight) * acc_score + format_weight * fmt_score
        
        scores.append({
            "overall": overall_score,
            "format": fmt_score,
            "accuracy": acc_score,
        })

    # ================= 🔍 简要 Debug 输出 (可选) =================
    if len(scores) > 0:
        print(f"[Reward Compute] Batch Size: {len(scores)} | "
              f"Avg Overall: {sum(s['overall'] for s in scores)/len(scores):.4f} | "
              f"Avg Acc: {sum(s['accuracy'] for s in scores)/len(scores):.4f}")
        
    print(f"\n{'='*20} DEBUG REWARD OUTPUT {'='*20}")
    print(f"第一条数据的 Ground Truth: {ground_truths[0]}")
    print(f"第一条数据的 Response (前50字符): {clean_responses[0][:50]}...")
    print(f"第一条数据的 打分结果: {scores[0]}")
    print(f"{'='*60}\n")
    
    return scores