import os
import base64
import json
import time
import datetime
import copy
from openai import OpenAI

# 初始化 API 客户端
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("BASE_URL")
)

# ================= 🔧 调试配置 =================
# 定义保存日志的路径
DEBUG_LOG_DIR = "./debug_logs"
DEBUG_LOG_FILE = os.path.join(DEBUG_LOG_DIR, "vqa_debug_log.jsonl")

# 确保目录存在
if not os.path.exists(DEBUG_LOG_DIR):
    try:
        os.makedirs(DEBUG_LOG_DIR, exist_ok=True)
    except:
        pass
# ==============================================

def encode_image_base64(image_path):
    """读取图片并转换为 Base64 字符串"""
    if not image_path or not os.path.exists(image_path):
        print(f"[VQA Warning] Image path not found: {image_path}")
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[VQA Error] Image encode failed: {e}")
        return None

def _sanitize_for_logging(messages):
    """
    清洗日志数据：如果 input 里包含超长的 base64 图片，
    在保存日志时把它替换成简短的占位符，防止日志文件爆炸。
    """
    try:
        # 深拷贝防止修改原始数据
        sanitized = copy.deepcopy(messages)
        for msg in sanitized:
            if isinstance(msg.get("content"), list):
                for content_item in msg["content"]:
                    if content_item.get("type") == "image_url":
                        url = content_item.get("image_url", {}).get("url", "")
                        if url.startswith("data:image") and len(url) > 200:
                            content_item["image_url"]["url"] = "<base64_image_data_truncated>"
        return sanitized
    except:
        return messages # 如果处理失败，原样返回

def call_judge_api(messages, model="gpt-4.1-mini", max_retries=2):
    """
    调用 OpenAI 格式的 API (GPT-4o 或 Qwen-VL)
    并保存详细的调试日志
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.5, # 判卷需要确定性
                max_tokens=2048,
                # 注意：有些模型不支持 json_object 模式，如果报错可以去掉这行
                # response_format={"type": "json_object"} 
            )
            
            content = response.choices[0].message.content
            
            # ---------------- [新增] 保存日志逻辑 ----------------
            # try:
            #     log_entry = {
            #         "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            #         "input_messages": _sanitize_for_logging(messages),
            #         "model_response": content
            #     }
            #     with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            #         f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            #     print(f"[DEBUG VQA] Log saved to {DEBUG_LOG_FILE}")
            # except Exception as log_e:
            #     print(f"[DEBUG VQA] Failed to save log: {log_e}")
            # ----------------------------------------------------

            # 清洗 markdown (有些模型会多输出 ```json ... ```)
            clean_content = content
            if "```json" in clean_content:
                clean_content = clean_content.replace("```json", "").replace("```", "").strip()
            elif "```" in clean_content:
                clean_content = clean_content.replace("```", "").strip()
            
            return json.loads(clean_content)
            
        except Exception as e:
            print(f"[VQA Warning] Attempt {attempt+1} failed: {e}")
            if attempt == max_retries:
                print(f"[VQA Error] All retries failed.")
                # 记录失败日志
                try:
                    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
                        err_entry = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "error": str(e),
                            "input_messages": _sanitize_for_logging(messages)
                        }
                        f.write(json.dumps(err_entry, ensure_ascii=False) + "\n")
                except: pass
                
                return {}
            time.sleep(1)
            
    return {}