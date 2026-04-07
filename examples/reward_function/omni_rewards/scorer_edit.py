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

# 【保持不变】评分标准 (0.0 - 1.0)
SCORING_RUBRIC = """
**Scoring Criteria:**
Please evaluate the image against the checklist condition on a continuous scale from 0.0 to 1.0:

- **1.0 (Perfect)**: The image STRICTLY satisfies the condition. No issues.
- **0.7 - 0.9 (Good)**: The condition is met, but there are very minor aesthetic issues or negligible deviations.
- **0.4 - 0.6 (Fair)**: The core requirement is visible but has noticeable flaws (e.g., wrong color shade, slight misalignment, or partially correct text).
- **0.1 - 0.3 (Poor)**: Major elements are incorrect or barely recognizable, though a faint attempt is visible.
- **0.0 (Failure)**: The image clearly fails the condition, contradicts the requirement, or the feature is missing entirely.

**Output Format:**
Return ONLY a valid JSON object mapping Question IDs to Float Scores.
Example: {"1": 1.0, "2": 0.3, "3": 0.8}
"""

def score_one(data_item, model_response):
    """
    Diagram Edit Scorer
    Input: Original Image + Instruction + Candidate Image + Checklist
    """
    # 1. 渲染候选图 (Candidate)
    id = data_item.get("id", None)
    cand_img_path = extract_and_render(model_response, filename_id=id)
    
    if not cand_img_path or not os.path.exists(cand_img_path):
        print(f"[Scorer] Render failed for ID: {id}")
        return 0.0

    # 2. 准备数据
    checklist = data_item.get('vqa_checklist', [])
    if not checklist: return 0.0

    instruction = data_item.get('instruction', "No instruction provided")
    
    # 【关键差异】Diagram Edit 任务通常需要读取“原图”作为题目的一部分
    # 这里 data_item['image_path'] 通常指向的是待编辑的原图 (Original Input)
    # 这不是 GT，这是题目！
    orig_img_path = data_item.get('image_path', None)
    
    cand_b64 = encode_image_base64(cand_img_path)
    orig_b64 = encode_image_base64(orig_img_path) if orig_img_path else None
    
    if not cand_b64: return 0.0
    
    # 3. 构造 Prompt
    questions_str = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(checklist)])

    # System Prompt: 强调“编辑任务”的验收
    system_prompt = (
        "You are an expert QA Auditor for Diagram Editing.\n"
        "Your task is to verify if the Candidate Image correctly implements the Edit Instruction applied to the Original Image.\n"
        f"{SCORING_RUBRIC}"
    )
    
    user_content = []
    
    # 放入 原图 (Context)
    # 如果数据里有原图，必须给模型看，否则它不知道“把红色改成蓝色”里的红色在哪
    if orig_b64:
        user_content.append({"type": "text", "text": "## Original Image (Before Edit):"})
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{orig_b64}"}})
    
    # 放入 编辑指令
    user_content.append({"type": "text", "text": f"## Edit Instruction:\n{instruction}"})
    
    # 放入 候选图 (Result)
    user_content.append({"type": "text", "text": "## Candidate Image (After Edit):"})
    user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cand_b64}"}})
    
    # 放入 Checklist
    user_content.append({"type": "text", "text": f"## Checklist to Verify:\n{questions_str}"})

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
        val = res_json.get(str(i+1)) or res_json.get(f"Q{i+1}") or res_json.get(i+1)
        if val is not None:
            try:
                score = float(val)
                score = max(0.0, min(1.0, score)) # 确保 0-1
                total += score
                count += 1
            except: pass
            
    return total / count if count > 0 else 0.0