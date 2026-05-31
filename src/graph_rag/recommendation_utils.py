import re
from typing import Any, Dict, List, Optional, Tuple


def parse_age_range(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Extract an approximate insurance age range from Chinese product text."""
    if not text:
        return None, None
    normalized = str(text).replace("周岁", "岁").replace(" ", "")
    nums = [int(n) for n in re.findall(r"(\d{1,3})(?:岁|天|个月|月)?", normalized)]
    if not nums:
        return None, None

    # "出生满30天-70岁" should be treated as min_age=0, max_age=70.
    if "出生" in normalized or "天" in normalized or "月" in normalized:
        range_match = re.search(r"(\d{1,3})(?:岁|天|个月|月)?\s*(?:-|~|至|到)\s*(\d{1,3})", normalized)
        if range_match:
            return 0, int(range_match.group(2))
        return 0, max(nums)
    range_match = re.search(r"(\d{1,3})(?:岁|天|个月|月)?\s*(?:-|~|至|到)\s*(\d{1,3})", normalized)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    if "续保" in normalized and not any(k in normalized for k in ("投保", "承保", "年龄限制")):
        return None, None
    if "以下" in normalized or "不超过" in normalized or "最高" in normalized:
        return None, max(nums)
    if "以上" in normalized or "起" in normalized:
        return min(nums), None
    if len(nums) >= 2:
        return min(nums), max(nums)
    return None, nums[0]


def parse_price_value(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    match = re.search(r"(\d+)", str(text).replace(",", ""))
    return int(match.group(1)) if match else None


def normalize_city(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    city = str(value).strip()
    for suffix in ("市", "省", "自治区", "特别行政区"):
        if city.endswith(suffix):
            city = city[: -len(suffix)]
    return city or None


def insurance_risk_tags(name: str, category: str, description: str) -> List[str]:
    text = f"{name} {category} {description}"
    tags = []
    tag_rules = {
        "适老": ["老年", "中老年", "50-80", "60", "70", "防癌"],
        "慢病友好": ["高血压", "糖尿病", "三高", "慢病", "带病"],
        "医疗保障": ["医疗", "住院", "特药", "门诊"],
        "重疾保障": ["重疾", "重大疾病", "癌症", "恶性肿瘤"],
        "长期保障": ["长期", "续保", "终身"],
    }
    for tag, keywords in tag_rules.items():
        if any(k in text for k in keywords):
            tags.append(tag)
    return tags[:4]


def score_insurance(item: Dict[str, Any], age: Optional[int], diseases: List[str], raw_query: str) -> int:
    score = 50
    name = item.get("name") or ""
    category = item.get("category") or ""
    desc = item.get("description") or item.get("desc") or ""
    min_age, max_age = item.get("min_age"), item.get("max_age")

    if age is not None:
        if min_age is not None and age < min_age:
            return -999
        if max_age is not None and age > max_age:
            return -999
        score += 25

    for disease in diseases or []:
        if disease and disease in desc:
            score += 18

    if any(k in raw_query for k in ("医疗", "住院")) and "医疗" in f"{name}{category}":
        score += 12
    if any(k in raw_query for k in ("重疾", "大病")) and any(k in f"{name}{category}{desc}" for k in ("重疾", "重大疾病", "大病")):
        score += 12
    if any(k in raw_query for k in ("防癌", "癌症")) and any(k in f"{name}{desc}" for k in ("防癌", "癌症", "恶性肿瘤")):
        score += 12
    if "适老" in item.get("risk_tags", []):
        score += 8
    if "慢病友好" in item.get("risk_tags", []):
        score += 8
    return score


def build_suitable_reason(item: Dict[str, Any], age: Optional[int], diseases: List[str]) -> str:
    bits = []
    if age is not None:
        bits.append(f"投保年龄范围与 {age} 岁条件匹配")
    matched_diseases = [d for d in diseases or [] if d and d in (item.get("description") or "")]
    if matched_diseases:
        bits.append("产品描述中出现相关健康关键词：" + "、".join(matched_diseases[:3]))
    tags = item.get("risk_tags") or []
    if tags:
        bits.append("标签：" + "、".join(tags))
    return "；".join(bits) if bits else "与当前问题关键词相近，可作为候选方案进一步核对条款。"


def score_nursing_home(item: Dict[str, Any], city: Optional[str], price_max: Optional[int]) -> int:
    score = 40
    services = item.get("services") or ""
    price = parse_price_value(item.get("price"))
    address = item.get("address") or ""
    name = item.get("name") or ""

    if city and (city in address or city in name or city in str(item.get("city") or "")):
        score += 25
    if price_max is not None and price is not None:
        if price <= price_max:
            score += 25
        else:
            return -999
    if "医养结合" in services:
        score += 15
    if "康复护理" in services:
        score += 10
    if "邻近医院" in services:
        score += 8
    return score
