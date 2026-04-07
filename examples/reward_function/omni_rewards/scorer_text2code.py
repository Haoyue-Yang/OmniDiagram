import os
import sys
import json

# 【保持不变】加入路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 【保持不变】导入工具
from utils_render import extract_and_render
from utils_vqa import call_judge_api, encode_image_base64

# 【修改点 1】更新评分标准，支持 0.0-1.0 连续打分
SCORING_RUBRIC = """
**Scoring Criteria:**
Please evaluate the generated diagram against the requirement on a continuous scale from 0.0 to 1.0:

- **1.0 (Perfect)**: The image STRICTLY satisfies the condition. No issues.
- **0.7 - 0.9 (Good)**: The condition is met, but there are very minor aesthetic issues or negligible deviations.
- **0.4 - 0.6 (Fair)**: The core requirement is visible but has noticeable flaws (e.g., wrong color shade, slight misalignment, or partially correct text).
- **0.1 - 0.3 (Poor)**: Major elements are incorrect or barely recognizable, though a faint attempt is visible.
- **0.0 (Failure)**: The image clearly fails the condition, contradicts the requirement, or the feature is missing entirely.

**Output Format:**
Return ONLY a valid JSON object mapping Question IDs to Float Scores.
Example: {"1": 1.0, "2": 0.3, "3": 0.7}
"""

def score_one(data_item, model_response):
    """
    Text2Code Scorer (Checklist-based)
    """
    # 1. 渲染
    id = data_item.get("id", None)
    cand_img_path = extract_and_render(model_response, filename_id=id)
    
    if not cand_img_path or not os.path.exists(cand_img_path):
        print(f"[Scorer] Render failed for ID: {id}")
        return 0.0

    # 2. 准备数据
    checklist = data_item.get('vqa_checklist', [])
    if not checklist: 
        print(f"[DEBUG Warning] ID: {id} has empty checklist!") # <--- 加上这行
        return 0.0
    
    # Text2Code 不需要原图，只需要看生成的图是否符合 Checklist
    cand_b64 = encode_image_base64(cand_img_path)
    if not cand_b64: return 0.0

    # 3. 构造 Prompt
    questions_str = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(checklist)])
    
    # System Prompt 强调作为“验证者”的角色
    system_prompt = (
        "You are a Code Output Verifier.\n"
        "Evaluate the generated diagram strictly based on the provided requirements checklist.\n"
        f"{SCORING_RUBRIC}"
    )
    
    user_content = [
        # 展示生成的图
        {"type": "text", "text": "## Generated Diagram Image:"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cand_b64}"}},
        
        # 展示检查清单
        {"type": "text", "text": f"## Requirements Checklist:\n{questions_str}"}
    ]

    # 4. 调用 API
    try:
        res_json = call_judge_api([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ])
    except Exception as e:
        print(f"[Scorer Error] API Call failed: {e}")
        return 0.0

    # 5. 算分
    total = 0.0
    count = 0
    for i in range(len(checklist)):
        # 兼容各种 key 格式: "1", "Q1", 1
        val = res_json.get(str(i+1)) or res_json.get(f"Q{i+1}") or res_json.get(i+1)
        if val is not None:
            try:
                score = float(val)
                score = max(0.0, min(1.0, score)) # 确保 0-1
                total += score
                count += 1
            except: pass
            
    return total / count if count > 0 else 0.0