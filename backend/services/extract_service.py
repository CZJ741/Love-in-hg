# backend/services/extract_service.py
"""从文本中提取键值对信息"""
import re

# 字段名映射：文本中的字段名 -> 数据库字段名
FIELD_MAP = {
    '手机号码': 'phone', '手机号': 'phone', '电话': 'phone', '联系方式': 'phone',
    '姓名': 'name', '名字': 'name',
    '昵称': 'nickname',
    '性别': 'gender',
    '年龄': 'age',
    '生日': 'birthday', '出生日期': 'birthday',
    '社交账号': 'socialAccount', '微信号': 'socialAccount', '微信': 'socialAccount', 'QQ': 'socialAccount', 'qq': 'socialAccount',
    '职业': 'occupation', '工作': 'occupation',
    '收入': 'income', '年薪': 'income', '月薪': 'income',
    '是否体制内': 'isPublicSector', '体制内': 'isPublicSector',
    '身高': 'height',
    '体重': 'weight',
    '备注': 'remark', '简介': 'remark', '择偶要求': 'remark', '个人简介': 'remark',
}

ALL_FIELD_NAMES = list(FIELD_MAP.keys())


def extract_key_values(text):
    """
    从文本中提取键值对。
    支持格式：{姓名：张三} / 姓名：张三 / 姓名:张三
    """
    result = {}
    clean = text.strip().lstrip('{').rstrip('}')

    for field_name in ALL_FIELD_NAMES:
        db_field = FIELD_MAP[field_name]
        # 用其他字段名作为停止边界，防止跨字段贪婪匹配
        other_fields = [fn for fn in ALL_FIELD_NAMES if fn != field_name]
        if other_fields:
            stop = '|'.join(re.escape(fn) for fn in other_fields)
            pattern = rf'{re.escape(field_name)}[：:=]\s*(.+?)(?=\s*(?:{stop})[：:=]|\s*$)'
        else:
            pattern = rf'{re.escape(field_name)}[：:=]\s*(.+)$'
        m = re.search(pattern, clean)
        if m:
            value = m.group(1).strip().rstrip('}，,')
            result[db_field] = _convert_value(db_field, value)

    return result


def try_parse_json(text):
    """尝试解析 JSON 格式"""
    import json
    try:
        cleaned = text.strip()
        if cleaned.startswith('{') or cleaned.startswith('['):
            data = json.loads(cleaned)
            record = data[0] if isinstance(data, list) else data
            result = {}
            for cn, en in FIELD_MAP.items():
                if cn in record:
                    result[en] = record[cn]
            return result if (result.get('phone') or result.get('name') or len(result) >= 2) else None
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _convert_value(db_field, value):
    """值类型转换"""
    if db_field in ('height', 'weight', 'age'):
        m = re.search(r'(\d+)', value)
        return int(m.group(1)) if m else 0
    if db_field == 'isPublicSector':
        return value in ('是', '✅', '✔', 'true', 'True')
    if db_field == 'birthday':
        return re.sub(r'[年月]', '-', value).rstrip('日')
    return value
