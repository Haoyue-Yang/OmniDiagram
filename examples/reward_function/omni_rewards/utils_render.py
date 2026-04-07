import os
import re
import subprocess
import uuid
import shutil
import time
import logging

# ================= 🔧 调试配置 =================
# 将此路径设置为你希望保存中间渲染结果的地方
DEBUG_IMG_DIR = "./test_rl_function/debug_images"
if not os.path.exists(DEBUG_IMG_DIR):
    os.makedirs(DEBUG_IMG_DIR, exist_ok=True)

# 临时工作目录
TEMP_DIR = "./rl_render_cache"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

# ================= 🧹 代码清洗工具 =================

def clean_latex_code(text):
    """
    深度清洗 Latex 代码：去除 <think>、提取 document 环境
    """
    if not text: return ""
    
    # 1. 暴力去除 <think>...</think> (包括跨行)
    # 使用 re.DOTALL 让 . 匹配换行符
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. 尝试提取 ```latex ... ```
    match = re.search(r"```(?:latex|tex)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        # 如果提取出来的代码里有 \documentclass，那就稳了
        if "\\documentclass" in code:
            return code
    
    # 3. 如果没找到代码块，或者代码块里没头没尾，
    #    直接在全文里找 \documentclass ... \end{document}
    start_idx = text.find("\\documentclass")
    end_idx = text.rfind("\\end{document}")
    
    if start_idx != -1 and end_idx != -1:
        # 加上 \end{document} 的长度
        return text[start_idx : end_idx + 14].strip()
    
    # 4. 如果只有头没有尾（模型没写完），尝试抢救
    if start_idx != -1:
        return text[start_idx:].strip()
        
    return text.strip() # 实在没办法，返回原清洗后的文本

def extract_code_block(text):
    """
    智能提取代码块和语言类型。
    返回: (code, lang_type)
    """
    if not text:
        return None, None
        
    # 0. 预处理：先清洗掉 <think> 标签，防止干扰正则
    clean_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # === 策略 A: 显式 Markdown 标签匹配 ===
    # 1. Latex
    match = re.search(r"```(?:latex|tex)\s*([\s\S]*?)```", clean_text, re.IGNORECASE)
    if match: return clean_latex_code(match.group(1).strip()), "latex"
    
    # 2. Mermaid
    match = re.search(r"```mermaid\s*([\s\S]*?)```", clean_text, re.IGNORECASE)
    if match: return match.group(1).strip(), "mermaid"
    
    # 3. PlantUML
    match = re.search(r"```plantuml\s*([\s\S]*?)```", clean_text, re.IGNORECASE)
    if match: return match.group(1).strip(), "plantuml"
    
    # === 策略 B: 内容特征匹配 (兜底) ===
    
    # 4. Latex 特征
    if "\\documentclass" in clean_text:
        return clean_latex_code(clean_text), "latex"
        
    # 5. Mermaid 特征
    # 常见的开头: graph TD, sequenceDiagram, classDiagram
    if re.search(r"^\s*(graph\s+\w+|sequenceDiagram|classDiagram|pie|flowchart)", clean_text, re.MULTILINE):
        # 尝试提取到 ``` 或结束
        code = clean_text.strip()
        # 简单去除可能存在的 ``` 标记
        code = code.replace("```mermaid", "").replace("```", "").strip()
        return code, "mermaid"

    # 6. PlantUML 特征
    if "@startuml" in clean_text:
        start = clean_text.find("@startuml")
        end = clean_text.find("@enduml")
        if end != -1:
            return clean_text[start : end+7], "plantuml"
        return clean_text[start:], "plantuml"

    return None, None

# ================= 🎨 渲染函数 =================

def render_latex(code, unique_id):
    # 使用调试目录作为工作目录，方便查看
    work_dir = os.path.join(DEBUG_IMG_DIR, f"latex_{unique_id}")
    os.makedirs(work_dir, exist_ok=True)
    
    tex_file = os.path.join(work_dir, "main.tex")
    pdf_file = os.path.join(work_dir, "main.pdf")
    final_png_path = os.path.join(DEBUG_IMG_DIR, f"latex_{unique_id}.png")

    with open(tex_file, 'w') as f: f.write(code)
    
    try:
        # 1. Latex -> PDF
        # capture_output=True 用于捕获报错信息
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", work_dir, tex_file],
            capture_output=True, text=True, timeout=10
        )
        
        if proc.returncode != 0:
            logger.error(f"[Render Latex Error] ID: {unique_id}\nStderr: {proc.stderr}\nStdout tail: {proc.stdout[-200:]}")
            # 保存错误日志以便查看
            with open(os.path.join(work_dir, "error.log"), "w") as f:
                f.write(proc.stdout + "\n" + proc.stderr)
            # 即使报错，如果 PDF 生成了也尝试转图（有时候只是 warning）
            if not os.path.exists(pdf_file):
                return None
        
        # 2. PDF -> PNG
        if os.path.exists(pdf_file):
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", "-singlefile", pdf_file, os.path.join(work_dir, "main")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
            
            generated_png = os.path.join(work_dir, "main.png")
            if os.path.exists(generated_png):
                shutil.move(generated_png, final_png_path)
                # 只有成功时才清理，失败保留现场
                shutil.rmtree(work_dir, ignore_errors=True)
                print(f"[DEBUG] Latex Render Success: {final_png_path}")
                return final_png_path
            else:
                logger.error(f"[Render Latex Error] PDF created but PNG conversion failed for {unique_id}")
    except Exception as e:
        logger.error(f"[Render Latex Exception] {e}")
    
    return None

def render_mermaid(code, unique_id):
    mmd_file = os.path.join(DEBUG_IMG_DIR, f"mmd_{unique_id}.mmd")
    png_file = os.path.join(DEBUG_IMG_DIR, f"mmd_{unique_id}.png")
    
    with open(mmd_file, 'w') as f: f.write(code)
    
    try:
        puppeteer_config = "/tmp/puppeteer-config.json"
        
        proc = subprocess.run(
            ["mmdc", "-i", mmd_file, "-o", png_file, "-b", "transparent", "-s", "2", "-p", puppeteer_config],
            capture_output=True, text=True, timeout=30 
        )
        
        if os.path.exists(png_file):
            print(f"[DEBUG] Mermaid Render Success: {png_file}")
            return png_file
        else:
            logger.error(f"[Render Mermaid Error] ID: {unique_id}\nStderr: {proc.stderr}")
    except Exception as e:
        logger.error(f"[Render Mermaid Exception] {e}")
    
    return None

def render_plantuml(code, unique_id):
    puml_file = os.path.join(DEBUG_IMG_DIR, f"puml_{unique_id}.puml")
    png_file = os.path.join(DEBUG_IMG_DIR, f"puml_{unique_id}.png")
    
    with open(puml_file, 'w') as f: f.write(code)
    
    try:
        proc = subprocess.run(
            ["plantuml", "-tpng", puml_file], 
            capture_output=True, text=True, timeout=20
        )
        
        if os.path.exists(png_file):
            print(f"[DEBUG] PlantUML Render Success: {png_file}")
            return png_file
        else:
            logger.error(f"[Render PlantUML Error] ID: {unique_id}\nStderr: {proc.stderr}")
            
    except Exception as e:
        logger.error(f"[Render PlantUML Exception] {e}")
    
    return None

# ================= 🚀 主入口 =================

def extract_and_render(model_response, filename_id=None):
    """
    主入口：提取代码 -> 渲染 -> 返回图片路径
    filename_id: 如果提供了，就用这个名字保存图片 (例如 '0_1_7')
    """
    # 1. 尝试提取
    code, lang = extract_code_block(model_response)
    
    if not code:
        # 调试信息：打印前100个字符看看为什么没提取到
        preview = model_response[:100].replace("\n", "\\n")
        print(f"[DEBUG] Failed to extract code block. Content preview: {preview}...")
        return None
    
    # 2. 决定文件名
    if filename_id:
        unique_id = filename_id
    else:
        unique_id = str(uuid.uuid4())[:8]
    
    print(f"[DEBUG] Rendering {lang} task with ID: {unique_id}")

    # 3. 分发渲染
    if lang == "latex":
        # 再次清洗一下 Latex，确保安全
        clean_code = clean_latex_code(code)
        return render_latex(clean_code, unique_id)
        
    elif lang == "mermaid":
        return render_mermaid(code, unique_id)
        
    elif lang == "plantuml":
        return render_plantuml(code, unique_id)
    
    return None