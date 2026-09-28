# backend/utils/file_cleaner.py
"""
本地上传文件清理工具，支持安全防路径穿越检测
"""
import os
import json
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def delete_notice_images(images_data):
    """
    安全删除启事关联的本地物理图片文件
    :param images_data: 可以是 list，也可以是 JSON 字符串，例如 '["/uploads/xxx.jpg"]'
    """
    if not images_data:
        return

    if isinstance(images_data, str):
        try:
            images_data = json.loads(images_data)
        except Exception:
            # 兼容逗号分隔或单路径字符串
            images_data = [img.strip() for img in images_data.split(',') if img.strip()]

    if not isinstance(images_data, list):
        return

    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    )
    upload_folder = os.path.abspath(upload_folder)

    for img_item in images_data:
        if not img_item or not isinstance(img_item, str):
            continue

        # 处理 URL，例如 /uploads/20260328_xxx.jpg 或完整 URL
        filename = os.path.basename(img_item.split('?')[0])
        if not filename:
            continue

        file_path = os.path.abspath(os.path.join(upload_folder, filename))

        # 核心安全防御：防路径穿越攻击，确保被删文件严格在 upload_folder 目录之内
        if not file_path.startswith(upload_folder + os.sep) and file_path != upload_folder:
            logger.warning(f"[Security] 拦截到潜在的路径穿越删除请求: {img_item} -> {file_path}")
            continue

        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已清理物理图片文件: {file_path}")
            except Exception as e:
                logger.error(f"删除物理图片文件失败 {file_path}: {e}")
