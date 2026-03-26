import json
import os
import glob

# --- 配置区域 ---
INPUT_PATTERN = 'disease*.json'
OUTPUT_FILE = 'final_loose_elderly.json'

# 1. 筛选关键词（只要 easy_get 里有这俩字这就留）
# 注意：这就意味着 "中青年"、"老板"（虽然不会有）也会被匹配，但"中老年"肯定在里面
KEYWORDS = ["中", "老"]

# 2. 需要删除的字段 (保持之前的要求)
FIELDS_TO_REMOVE = [
    "treat", "treat_prob", "treat_period", "treat_cost", 
    "can_eat", "not_eat", "insurance", "check" 
]

def load_json_smart(filepath):
    """万能加载函数"""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            try:
                # 尝试作为标准 JSON 读取
                json_data = json.loads(content)
                if isinstance(json_data, list):
                    return json_data
                else:
                    return [json_data]
            except json.JSONDecodeError:
                # 尝试作为 JSON Lines 读取
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except:
                            pass
        return data
    except Exception as e:
        print(f"❌ 读取文件 {filepath} 失败: {e}")
        return []

def is_target_disease(disease):
    """
    宽松筛选逻辑：
    只要 easy_get 包含 '中' 或 '老' 字，就保留
    """
    easy_get = str(disease.get('easy_get', ''))
    
    # 只要满足任意一个关键词
    for kw in KEYWORDS:
        if kw in easy_get:
            return True
            
    return False

def process_item(item, new_id):
    """删除字段 + 重置ID"""
    new_item = item.copy()
    
    # 批量删除字段
    for field in FIELDS_TO_REMOVE:
        if field in new_item:
            del new_item[field]
            
    # 重置 ID (从1开始)
    new_item['id'] = str(new_id)
    return new_item

def main():
    input_files = glob.glob(INPUT_PATTERN)
    if not input_files:
        print("❌ 未找到源文件，请检查路径！")
        return

    print(f"🔎 开始执行【宽松版】筛选...")
    print(f"筛选标准：easy_get 中含有 '中' 或 '老' 即可")
    print("-" * 50)
    
    collected_diseases = []
    
    # 遍历所有文件
    for filepath in input_files:
        raw_data = load_json_smart(filepath)
        for item in raw_data:
            if is_target_disease(item):
                collected_diseases.append(item)

    print("-" * 50)
    print(f"📊 筛选结束！共找到 {len(collected_diseases)} 条数据。")

    # 清洗并保存
    final_data = []
    for i, item in enumerate(collected_diseases):
        # ID 从 1 开始重排
        clean_item = process_item(item, i + 1)
        final_data.append(clean_item)
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print(f"🎉 文件已保存至: {OUTPUT_FILE}")
    print(f"已移除字段: {FIELDS_TO_REMOVE}")

if __name__ == '__main__':
    main()