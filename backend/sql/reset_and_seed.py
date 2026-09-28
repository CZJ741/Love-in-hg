# backend/sql/reset_and_seed.py
"""
重置数据库数据并重新生成丰富的测试数据
1. 清空 notice_views, membership_orders, notices, users
2. 批量生成 100+ 条真实详尽的黄冈/湖北本地化相亲启事测试数据
3. 同时预置多位预留手机号测试账号（涵盖普通用户、会员、大会员）
"""
import os
import sys
import json
import random
from datetime import datetime, timedelta

# 加入 backend 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Notice, NoticeView, MembershipOrder

app = create_app()

FIRST_NAMES_MALE = ['伟', '强', '磊', '洋', '勇', '军', '杰', '涛', '超', '明', '浩', '鑫', '俊', '博', '鹏', '宇', '晨', '轩', '天', '宇', '凯', '飞', '翔', '毅']
FIRST_NAMES_FEMALE = ['芳', '娜', '敏', '静', '丽', '娟', '艳', '茜', '婷', '雪', '琳', '欣', '瑶', '菲', '雯', '倩', '琪', '涵', '雅', '宁', '萱', '薇', '洁']
LAST_NAMES = ['李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗', '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧', '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕']

OCCUPATIONS_PUBLIC = ['黄冈市公务员', '市直属事业单位', '重点高中教师', '公立医院医生', '三甲医院护士', '国家电网员工', '中国烟草职工', '国有商业银行客户经理', '公安交警辅警', '区财政局科员']
OCCUPATIONS_PRIVATE = ['软件工程师', '建筑造价工程师', '室内设计师', '电商运营主管', '外贸经理', '民营企业会计', '律师事务所律师', '连锁餐饮店长', '新能源汽车销售', '私营企业主', '自媒体摄影师', '机械工程师']

INCOME_OPTIONS = ['3-5万', '5-10万', '10-20万', '20-30万', '30-50万', '50万以上']

REMARKS_POOL = [
    "性格温和开朗，懂得体贴照顾人。黄州本地有全款房一套，父母均有社保退休金无负担。希望未来的TA性格阳光，三观相合，彼此尊重。",
    "工作稳定有责任心，平时喜欢打羽毛球、跑步和烘焙。希望寻找一位善良懂事、工作稳定、孝顺父母的伴侣一起奋斗。",
    "体制内工作，作息规律。黄冈本地有房有代步车。为人真诚稳重，无不良嗜好，期待遇到有缘人携手步入婚姻殿堂。",
    "热爱生活与旅行，性格独立且顾家。希望对方有上进心，懂得沟通包容，双方共同营造温馨幸福的小家庭。",
    "踏实能干，为人正直谦和。平时喜好看书、音乐和烹饪。父母为人随和善良。期待那个眼中有光、互相欣赏的TA。",
    "在武汉黄冈两地有发展，事业处于稳定上升期。生活简单充实，希望寻找三观一致、彼此有共同话题的另一半。",
    "医生职业，做事细心沉稳，对待感情认真专一。希望找到一位能相互理解、相濡以沫的人生挚友与伴侣。",
    "重点高中英语教师，性格温婉大方，知书达理。希望男方有责任担当、成熟稳重，年龄相仿。"
]

AVATAR_IMAGES_MALE = [
    ["https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&auto=format&fit=crop&q=60"]
]

AVATAR_IMAGES_FEMALE = [
    ["https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&auto=format&fit=crop&q=60"],
    ["https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&auto=format&fit=crop&q=60"]
]


def run_reset():
    with app.app_context():
        print("1. Clear tables...")
        # 按照外键/关联依赖顺序清除
        NoticeView.query.delete()
        MembershipOrder.query.delete()
        Notice.query.delete()
        User.query.delete()
        db.session.commit()
        print("Tables cleared successfully.")

        print("2. Generating preset users and notices...")

        # 生成 80 条男女各半的相亲启事
        notices_to_add = []
        used_phones = set()

        # 先预置几个方便测试直登的特色用户手机号
        preset_users = [
            {
                "phone": "13800000001",
                "name": "张建国",
                "gender": "男",
                "age": 28,
                "height": 178,
                "weight": 70,
                "occupation": "黄冈市直公务员",
                "is_public_sector": True,
                "income": "10-20万",
                "housing_location": "本地",
                "social_account": "wx_zhangjg2026",
                "membership_type": "free",
                "remark": "黄冈本地公务员，性格稳重，有房有车。期待相遇善良有爱的你。"
            },
            {
                "phone": "13800000002",
                "name": "李晓雯",
                "gender": "女",
                "age": 26,
                "height": 165,
                "weight": 48,
                "occupation": "重点高中教师",
                "is_public_sector": True,
                "income": "5-10万",
                "housing_location": "本地",
                "social_account": "teacher_wen",
                "membership_type": "member",
                "remark": "重点高中语文老师，喜欢书法和散步，知书达理。父母都是退休教师。"
            },
            {
                "phone": "13800000003",
                "name": "陈明辉",
                "gender": "男",
                "age": 31,
                "height": 182,
                "weight": 75,
                "occupation": "建筑设计主管",
                "is_public_sector": False,
                "income": "30-50万",
                "housing_location": "本地",
                "social_account": "arch_chen88",
                "membership_type": "vip",
                "remark": "年薪35w+，黄州两套房。性格随和开朗，热爱健身旅行，期待有缘女孩。"
            }
        ]

        # 写入预设用户和启事
        for p in preset_users:
            used_phones.add(p["phone"])
            user = User(
                phone=p["phone"],
                name=p["name"],
                gender=p["gender"],
                occupation=p["occupation"],
                income=p["income"],
                is_public_sector=p["is_public_sector"],
                height=p["height"],
                weight=p["weight"],
                membership_type=p["membership_type"],
                membership_expire=datetime.utcnow() + timedelta(days=365) if p["membership_type"] != 'free' else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.flush()

            imgs = AVATAR_IMAGES_MALE[0] if p["gender"] == "男" else AVATAR_IMAGES_FEMALE[0]
            notice = Notice(
                user_id=user.id,
                publisher_role="本人",
                phone=p["phone"],
                name=p["name"],
                nickname=p["name"][0] + "同学",
                gender=p["gender"],
                age=p["age"],
                social_account=p["social_account"],
                housing_location=p["housing_location"],
                occupation=p["occupation"],
                income=p["income"],
                is_public_sector=p["is_public_sector"],
                height=p["height"],
                weight=p["weight"],
                images="[]",
                remark=p["remark"],
                source="user",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(notice)

        # 批量生成 77 条丰富的真实启事数据
        genders = ['男'] * 38 + ['女'] * 39
        random.shuffle(genders)

        for i, gender in enumerate(genders):
            while True:
                prefix = random.choice(['135', '136', '137', '138', '139', '150', '158', '159', '186', '188', '198'])
                suffix = ''.join(str(random.randint(0, 9)) for _ in range(8))
                phone = prefix + suffix
                if phone not in used_phones:
                    used_phones.add(phone)
                    break

            last_name = random.choice(LAST_NAMES)
            first_name = random.choice(FIRST_NAMES_MALE if gender == '男' else FIRST_NAMES_FEMALE)
            name = last_name + first_name

            age = random.randint(23, 42)
            height = random.randint(170, 188) if gender == '男' else random.randint(155, 172)
            weight = random.randint(60, 85) if gender == '男' else random.randint(43, 62)

            is_public = random.random() < 0.35  # 35% 体制内
            occupation = random.choice(OCCUPATIONS_PUBLIC if is_public else OCCUPATIONS_PRIVATE)
            income = random.choice(INCOME_OPTIONS)
            housing = '本地' if random.random() < 0.85 else '外地'
            role = random.choice(['本人', '本人', '本人', '父母', '亲戚'])

            # 随机挑选 1~2 张精选真实男女头像相册
            if gender == '男':
                img_pool = random.choice(AVATAR_IMAGES_MALE)
            else:
                img_pool = random.choice(AVATAR_IMAGES_FEMALE)

            remark = random.choice(REMARKS_POOL)

            notice = Notice(
                user_id=0,
                publisher_role=role,
                phone=phone,
                name=name,
                nickname=last_name + ("先生" if gender == "男" else "女士"),
                gender=gender,
                age=age,
                social_account=f"wx_{phone[3:7]}_{random.randint(10,99)}",
                housing_location=housing,
                occupation=occupation,
                income=income,
                is_public_sector=is_public,
                height=height,
                weight=weight,
                images="[]",
                remark=remark,
                source="seed",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                updated_at=datetime.utcnow()
            )
            db.session.add(notice)

        db.session.commit()
        print(f"Generated 3 preset users and 80 notices successfully.")

if __name__ == '__main__':
    run_reset()
