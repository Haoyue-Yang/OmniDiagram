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

# 【修改点 1】更新评分标准 Prompt
# 允许使用 0.0 - 1.0 之间的任意浮点数，给出更细腻的判断
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
    Diagram2Code Scorer (Reference-Free / VQA only)
    Input: 
      - data_item: 包含 vqa_checklist, id 等
      - model_response: 模型生成的代码
    """
    # 1. 渲染 (传入 id 以便生成有意义的文件名)
    id = data_item.get("id", None)
    cand_img_path = extract_and_render(model_response, filename_id=id)
    
    if not cand_img_path or not os.path.exists(cand_img_path):
        # 渲染失败直接0分
        print(f"[Scorer] Render failed for ID: {id}")
        return 0.0

    # 2. 准备 VQA 数据
    checklist = data_item.get('vqa_checklist', [])
    if not checklist: return 0.0 

    # 【修改点 2】完全移除 GT 图片的处理逻辑
    # 只处理候选图片
    cand_b64 = encode_image_base64(cand_img_path)
    
    if not cand_b64: return 0.0

    # 3. 构造 Prompt
    questions_str = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(checklist)])
    
    # 更新 System Prompt，不再提及 "comparing against Ground Truth"
    system_prompt = (
        "You are an expert Visual Evaluator.\n"
        "Your task is to judge whether a generated diagram satisfies a specific checklist of requirements.\n"
        "Evaluate the image purely based on the text descriptions provided below.\n"
        f"{SCORING_RUBRIC}"
    )
    
    user_content = []
    
    # 只放入 候选图
    user_content.append({"type": "text", "text": "## Candidate Image (To Evaluate):"})
    user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cand_b64}"}})
    
    # 放入 Checklist
    user_content.append({"type": "text", "text": f"## Checklist Requirements:\n{questions_str}"})

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
        # 尝试读取分数
        val = res_json.get(str(i+1)) or res_json.get(f"Q{i+1}") or res_json.get(i+1)
        if val is not None:
            try:
                score = float(val)
                # 确保分数在 0.0 - 1.0 之间
                score = max(0.0, min(1.0, score))
                total += score
                count += 1
            except: pass
            
    return total / count if count > 0 else 0.0