# backend/routes/admin.py
"""管理接口：文本提取导入 + 种子数据导入"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, Notice
from config import Config
from services.extract_service import extract_key_values, try_parse_json

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/extractAndImport', methods=['POST'])
def extract_and_import():
    """
    从长文本中提取键值对并入库。
    支持格式: {姓名：张三} / 姓名：张三 / 姓名:张三
    """
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify(code=400, msg='请提供有效的文本内容'), 400

    # 先尝试 JSON
    extracted = try_parse_json(text)
    if not extracted or not any(extracted.values()):
        extracted = extract_key_values(text)

    if not extracted.get('phone') and not extracted.get('name'):
        return jsonify(code=400, msg='未能从文本中提取到有效信息，请检查格式。支持: {姓名：张三} 或 姓名：张三', extracted={}), 400

    # 检查手机号是否已存在
    if extracted.get('phone'):
        existing = Notice.query.filter_by(phone=extracted['phone']).first()
        if existing:
            return jsonify(code=409, msg=f'手机号 {extracted["phone"]} 已存在', extracted=extracted), 409

    # 入库
    notice = Notice(
        user_id=0,
        phone=extracted.get('phone', ''),
        name=extracted.get('name', ''),
        nickname=extracted.get('nickname', ''),
        gender=extracted.get('gender', ''),
        birthday=extracted.get('birthday', ''),
        occupation=extracted.get('occupation', ''),
        income=extracted.get('income', ''),
        is_public_sector=bool(extracted.get('isPublicSector', False)),
        height=int(extracted.get('height', 0) or 0),
        weight=int(extracted.get('weight', 0) or 0),
        remark=extracted.get('remark', ''),
        source='import',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(notice)
    db.session.commit()

    return jsonify(code=0, msg='数据导入成功', data={
        'id': str(notice.id),
        'extracted': extracted
    })


@admin_bp.route('/initData', methods=['POST'])
def init_data():
    """批量导入种子数据（100条）"""
    data = request.get_json() or {}
    password = data.get('password', '')

    if password != Config.INIT_DATA_PASSWORD:
        return jsonify(code=403, msg='无权限'), 403

    import os
    import random

    seed_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'seed_notices.json')

    try:
        with open(seed_path, 'r', encoding='utf-8') as f:
            seeds = json.load(f)
    except FileNotFoundError:
        return jsonify(code=500, msg='种子数据文件不存在: sql/seed_notices.json'), 500

    success, skip, errors = 0, 0, []

    for item in seeds:
        try:
            existing = Notice.query.filter_by(phone=item.get('phone', '')).first()
            if existing:
                skip += 1
                continue

            notice = Notice(
                user_id=0,
                phone=item.get('phone', ''),
                name=item.get('name', ''),
                nickname=item.get('nickname', ''),
                gender=item.get('gender', ''),
                birthday=item.get('birthday', ''),
                occupation=item.get('occupation', ''),
                income=item.get('income', ''),
                is_public_sector=item.get('isPublicSector', False),
                height=item.get('height', 0),
                weight=item.get('weight', 0),
                remark=item.get('remark', ''),
                source='seed',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(notice)
            success += 1
        except Exception as e:
            errors.append({'phone': item.get('phone'), 'error': str(e)})

    db.session.commit()

    return jsonify(code=0, msg=f'导入完成: 成功{success}, 跳过{skip}, 失败{len(errors)}',
                   data={'successCount': success, 'skipCount': skip, 'errorCount': len(errors)})
