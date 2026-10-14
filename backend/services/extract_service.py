# backend/services/extract_service.py
"""
智能相亲文本键值提取服务：
1. 标准冒号键值对/JSON结构化提取
2. 启发式自然语言与口语化长文本规则增强抽取
"""
import re
import datetime

# 字段名映射：文本中的标准冒号字段名 -> 数据库字段名
FIELD_MAP = {
    '手机号码': 'phone', '手机号': 'phone', '电话': 'phone', '联系方式': 'phone', '电联': 'phone', '联系电话': 'phone',
    '姓名': 'name', '名字': 'name', '真实姓名': 'name',
    '昵称': 'nickname', '小名': 'nickname',
    '性别': 'gender',
    '年龄': 'age', '实际年龄': 'age',
    '生日': 'age', '出生日期': 'age', '出生年月': 'age', '出生年份': 'age', '出生': 'age',
    '社交账号': 'socialAccount', '微信号': 'socialAccount', '微信': 'socialAccount', 'QQ': 'socialAccount', 'qq': 'socialAccount',
    '职业': 'occupation', '工作': 'occupation', '现任': 'occupation', '从事': 'occupation', '工作单位': 'occupation',
    '收入': 'income', '年薪': 'income', '月薪': 'income', '年收入': 'income', '月收入': 'income', '待遇': 'income',
    '是否体制内': 'isPublicSector', '体制内': 'isPublicSector', '编制': 'isPublicSector',
    '身高': 'height', '净身高': 'height',
    '体重': 'weight', '净体重': 'weight',
    '发布人身份': 'publisherRole', '身份': 'publisherRole', '关系': 'publisherRole',
    '住房位置': 'housingLocation', '住房': 'housingLocation', '房产': 'housingLocation', '房子': 'housingLocation', '房车': 'housingLocation',
    '备注': 'remark', '简介': 'remark', '择偶要求': 'remark', '个人简介': 'remark', '要求': 'remark', '择偶标准': 'remark', '基本情况': 'remark',
}

ALL_FIELD_NAMES = list(FIELD_MAP.keys())

# 体制内强特征词库
PUBLIC_SECTOR_KEYWORDS = [
    '公务员', '事业编', '编制内', '在编', '区直机关', '市直机关', '街道办',
    '公安局', '财政局', '税务局', '国税', '地税', '检察院', '法院', '纪委',
    '公办学校', '公办教师', '在编教师', '中小学教师', '人民教师',
    '中心医院', '人民医院', '中医院', '妇幼保健院', '在编护士', '医生',
    '国企', '央企', '烟草', '电网', '供电局', '移动', '联通', '电信', '石油', '石化'
]

# 体制外特征词库
PRIVATE_SECTOR_KEYWORDS = [
    '私企', '民营', '自营', '个体', '创业', '自由职业', '外企', '做生意', '开店', '自媒体'
]


def extract_key_values(text):
    """
    智能从文本中提取键值对：
    优先标准模式提取，随后使用启发式规则补充缺失字段
    """
    if not text:
        return {}

    # 1. 尝试 JSON 提取
    json_result = try_parse_json(text)
    if json_result and len(json_result) >= 3:
        return _enrich_defaults(json_result, text)

    result = {}
    clean = text.strip().lstrip('{').rstrip('}')

    # 2. 传统冒号键值对提取
    for field_name in ALL_FIELD_NAMES:
        db_field = FIELD_MAP[field_name]
        if db_field in result and result[db_field]:
            continue
        other_fields = [fn for fn in ALL_FIELD_NAMES if fn != field_name]
        if other_fields:
            stop = '|'.join(re.escape(fn) for fn in other_fields)
            pattern = rf'{re.escape(field_name)}[：:=]\s*(.+?)(?=\s*(?:{stop})[：:=]|\n|\r|$)'
        else:
            pattern = rf'{re.escape(field_name)}[：:=]\s*(.+)$'

        m = re.search(pattern, clean)
        if m:
            val = m.group(1).strip().rstrip('}，,;；')
            converted = _convert_value(db_field, val)
            if converted is not None and converted != '':
                result[db_field] = converted

    # 3. 启发式自然语言模式补充（填补未提取到的字段）
    result = _apply_heuristics(clean, result)

    # 4. 默认值兜底与归一化
    return _enrich_defaults(result, clean)


def _apply_heuristics(text, current):
    """启发式正则与规则识别"""
    cur_year = datetime.datetime.now().year

    # 1. 手机号码识别 (严格匹配 11 位中国大陆手机号)
    phones = re.findall(r'(?<!\d)(1[3-9]\d{9})(?!\d)', text)
    if phones:
        current['phone'] = phones[0]
    elif current.get('phone'):
        # 清理已有 phone 字符串中的多余尾巴
        m_p = re.search(r'1[3-9]\d{9}', str(current['phone']))
        if m_p:
            current['phone'] = m_p.group(0)

    # 2. 性别识别
    if not current.get('gender') or current.get('gender') not in ('男', '女'):
        if re.search(r'(?:^|[\s，,。；;、])(?:女孩子|姑娘|女生|小姐姐|女方|妹子|闺女|女[，,\s]|[（(]女[）)])', text):
            current['gender'] = '女'
        elif re.search(r'(?:^|[\s，,。；;、])(?:男孩子|小伙子|男生|小哥哥|男方|大叔|儿子|小子|男[，,\s]|[（(]男[）)])', text):
            current['gender'] = '男'
        elif '男' in text and '女' not in text:
            current['gender'] = '男'
        elif '女' in text and '男' not in text:
            current['gender'] = '女'

    # 3. 姓名与称呼识别
    if not current.get('name'):
        m_name = re.search(r'(?:名字叫|全名|名叫|姓名[是为]?|这位是|叫)\s*([一-龥]{2,4})', text)
        if m_name:
            current['name'] = m_name.group(1).strip()
        else:
            # 常见格式：如 "，刘明亮。体制内" 或 "周婷，27岁"
            m_lead = re.search(r'(?:^|[，,。；;\n\r])([一-龥]{2,3})[，,。\s]+(?:\d{2}岁|现?\d{2}岁|1[5-9]\dcm|体制内)', text)
            if m_lead:
                candidate = m_lead.group(1).strip()
                if candidate not in ('本人', '急寻', '征婚', '推荐', '介绍', '坐标', '黄冈', '黄州', '家庭', '目前', '希望'):
                    current['name'] = candidate

    # 4. 昵称识别
    if not current.get('nickname'):
        m_nick = re.search(r'(?:大家叫我|小名叫|外号|叫我)\s*([一-龥a-zA-Z0-9]{1,6})', text)
        if m_nick:
            current['nickname'] = m_nick.group(1).strip()

    # 5. 年龄与出生年份换算
    if not current.get('age') or int(current.get('age', 0)) <= 0:
        m_age = re.search(r'(?<!\d)(\d{2})\s*岁', text)
        if m_age:
            current['age'] = int(m_age.group(1))
        else:
            m_year4 = re.search(r'(?<!\d)(19[7-9]\d|200\d)\s*年', text)
            if m_year4:
                born_year = int(m_year4.group(1))
                current['age'] = cur_year - born_year
            else:
                m_year2 = re.search(r'(?<!\d)([7-9]\d|0[0-5])\s*年', text)
                if m_year2:
                    y = int(m_year2.group(1))
                    born_year = (1900 + y) if y >= 60 else (2000 + y)
                    current['age'] = cur_year - born_year

    # 6. 身高 (cm) 识别
    if not current.get('height') or int(current.get('height', 0)) < 130 or int(current.get('height', 0)) > 230:
        # A. 1米63 / 1米75 / 1.75米
        m_meter = re.search(r'(?:身高|净身高|个子)?\s*1\s*[米点\.]\s*([4-9]\d)', text)
        if m_meter:
            current['height'] = 100 + int(m_meter.group(1))
        else:
            # B. 中文汉字数字一米七五
            cn_num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '零': 0}
            m_cn = re.search(r'一米([四五六七八九])([一二三四五六七八九零])?', text)
            if m_cn:
                tens = cn_num_map.get(m_cn.group(1), 0)
                units = cn_num_map.get(m_cn.group(2), 0) if m_cn.group(2) else 0
                current['height'] = 100 + tens * 10 + units
            else:
                # C. 150-220 之间的数字伴随 cm/厘米 或 身高关键词
                m_cm = re.search(r'(?:身高|净身高|个子|长到)\s*([12]\d{2})', text)
                if m_cm:
                    current['height'] = int(m_cm.group(1))
                else:
                    m_cm2 = re.search(r'(?<!\d)(1[4-9]\d|2[0-2]\d)\s*(?:cm|厘米)?', text)
                    if m_cm2:
                        current['height'] = int(m_cm2.group(1))

    # 7. 体重 (斤) 识别
    if not current.get('weight') or int(current.get('weight', 0)) <= 0:
        # A. 100斤 / 135斤
        m_jin = re.search(r'(?<!\d)(\d{2,3})\s*斤', text)
        if m_jin:
            current['weight'] = int(m_jin.group(1))
        else:
            # B. 72kg / 75公斤 -> 转换为斤 (乘2)
            m_kg = re.search(r'(?<!\d)(\d{2,3}(?:\.\d)?)\s*(?:kg|公斤)', text, re.IGNORECASE)
            if m_kg:
                current['weight'] = int(round(float(m_kg.group(1)) * 2))

    # 8. 体制内判断
    if 'isPublicSector' not in current:
        is_public = False
        for kw in PUBLIC_SECTOR_KEYWORDS:
            if kw in text:
                is_public = True
                break
        current['isPublicSector'] = is_public

    # 9. 发布人身份关系判断 (本人、父母、亲戚、朋友)
    if not current.get('publisherRole') or current.get('publisherRole') == '本人':
        if re.search(r'(?:阿姨|叔叔|父母|我儿子|我女儿|我家闺女|我家小子|家姑娘)', text):
            current['publisherRole'] = '父母'
        elif re.search(r'(?:邻居|亲戚|我表妹|我表弟|我姐|我妹|我堂哥|帮阿姨)', text):
            current['publisherRole'] = '亲戚'
        elif re.search(r'(?:我朋友|帮朋友|哥们|闺蜜)', text):
            current['publisherRole'] = '朋友'
        else:
            current['publisherRole'] = '本人'

    # 10. 职业识别
    if not current.get('occupation'):
        m_job = re.search(r'(?:做|在|任职|从事|当|工作是)?([一-龥]{2,10}(?:教师|老师|医生|护士|公务员|干部|警察|工程师|会计|销售|老板|经理|店长|职员|设计师|个体))', text)
        if m_job:
            current['occupation'] = m_job.group(1).strip()
        else:
            for kw in ['护士', '教师', '医生', '会计', '公务员', '事业单位', '程序员', '开店', '自营', '国企员工']:
                if kw in text:
                    current['occupation'] = kw
                    break

    # 11. 收入提取
    # 避免误抓类似 "92-96年" 的出生年范围
    if not current.get('income') or re.match(r'^[7-9]\d-[7-9]\d$', str(current.get('income', ''))):
        m_inc = re.search(r'((?:年到手|年薪|年入|年收入|月薪|月入|月到手|月收入)\s*[:：]?\s*(?:\d+[-~到至]\d+万?|\d+[kKwW]|七八千|\d+千|\d+万|\d+\+?))', text)
        if m_inc:
            current['income'] = m_inc.group(1).strip()
        else:
            m_inc2 = re.search(r'(?<!\d)(?:月入|月薪|年薪|年入)\s*(\d{4,6}\+?|\d+[-~到至]\d+万|\d+万左右|\d+万)', text)
            if m_inc2:
                current['income'] = m_inc2.group(0).strip()
            elif current.get('income') and re.match(r'^[7-9]\d-[7-9]\d$', str(current.get('income'))):
                current['income'] = ''

    # 12. 房产情况识别
    if not current.get('housingLocation'):
        m_house = re.search(r'([一-龥a-zA-Z0-9]{2,15}(?:碧桂园|公馆|万达|保利|小区|花园|城区|房一套|商品房|自建房|宿舍|有房))', text)
        if m_house:
            current['housingLocation'] = m_house.group(1).strip()
        else:
            current['housingLocation'] = '本地'

    # 13. 社交账号/微信号识别
    if not current.get('socialAccount'):
        m_wx = re.search(r'(?:微信号?|微信同号|加V|VX|vx)[:：\s]*([a-zA-Z0-9_-]{5,25})', text)
        if m_wx:
            wx_val = m_wx.group(1).strip()
            if wx_val not in ('同号', '也是这个'):
                current['socialAccount'] = wx_val
            elif current.get('phone'):
                current['socialAccount'] = current['phone']
        elif '微信同号' in text and current.get('phone'):
            current['socialAccount'] = current['phone']
    elif current.get('socialAccount') and current.get('phone') and ('同号' in str(current.get('socialAccount')) or '也是这个' in str(current.get('socialAccount'))):
        current['socialAccount'] = current['phone']

    # 14. 择偶/补充说明提取
    if not current.get('remark'):
        m_rem = re.search(r'(?:期望|择偶|要求|想找|希望找|标准)[:：\s]*([^\n\r]+)', text)
        if m_rem:
            current['remark'] = m_rem.group(1).strip()
        else:
            current['remark'] = text[:150]  # 原文前150字保底

    return current


def _enrich_defaults(result, raw_text):
    """默认值填充与合理性校验"""
    if 'housingLocation' not in result or not result['housingLocation']:
        result['housingLocation'] = '本地'
    if 'publisherRole' not in result or not result['publisherRole']:
        result['publisherRole'] = '本人'
    if 'gender' not in result or not result['gender']:
        result['gender'] = '男'
    if 'isPublicSector' not in result:
        result['isPublicSector'] = False

    # 若名字提取失败，尝试取前2个字符保底
    if not result.get('name'):
        m = re.search(r'[一-龥]{2,4}', raw_text)
        if m:
            result['name'] = m.group(0)

    # 清理各文本字段的换行和多余符号
    for k in ('name', 'nickname', 'occupation', 'income', 'housingLocation', 'socialAccount'):
        if k in result and isinstance(result[k], str):
            result[k] = result[k].strip().rstrip('，,;；。')

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
            for k, v in record.items():
                if k in ('name', 'gender', 'age', 'phone', 'height', 'weight', 'occupation', 'income', 'remark', 'socialAccount', 'isPublicSector', 'housingLocation', 'publisherRole'):
                    result[k] = v
            return result if (result.get('phone') or result.get('name') or len(result) >= 2) else None
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _convert_value(db_field, value):
    """值类型转换"""
    if not value:
        return ''
    if db_field in ('height', 'weight'):
        m = re.search(r'(\d+)', str(value))
        return int(m.group(1)) if m else 0
    if db_field == 'age':
        m = re.search(r'(\d+)', str(value))
        if not m:
            return 0
        num = int(m.group(1))
        cur_year = datetime.datetime.now().year
        if 1900 < num <= cur_year:
            return cur_year - num
        return num
    if db_field == 'isPublicSector':
        val_str = str(value).strip().lower()
        if val_str in ('是', '✅', '✔', 'true', '1', '编制', '体制内', '在编'):
            return True
        if val_str in ('否', 'false', '0', '体制外', '无编制'):
            return False
        for kw in PUBLIC_SECTOR_KEYWORDS:
            if kw in val_str:
                return True
        return False
    return str(value).strip()
