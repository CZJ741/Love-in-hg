-- backend/sql/schema.sql
-- MySQL database schema for 相亲角

CREATE DATABASE IF NOT EXISTS love_hg
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE love_hg;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    openid          VARCHAR(64)  DEFAULT '' COMMENT '微信openid',
    phone           VARCHAR(11)  NOT NULL UNIQUE COMMENT '手机号码',
    name            VARCHAR(20)  DEFAULT '' COMMENT '姓名',
    gender          VARCHAR(2)   DEFAULT '' COMMENT '性别(男/女)',
    birthday        VARCHAR(10)  DEFAULT '' COMMENT '生日(YYYY-MM-DD)',
    occupation      VARCHAR(50)  DEFAULT '' COMMENT '职业',
    income          VARCHAR(20)  DEFAULT '' COMMENT '收入范围',
    is_public_sector TINYINT(1)  DEFAULT 0 COMMENT '是否体制内',
    height          INT          DEFAULT 0 COMMENT '身高(cm)',
    weight          INT          DEFAULT 0 COMMENT '体重(kg)',

    -- 会员
    membership_type        VARCHAR(10)  DEFAULT 'free' COMMENT 'free/member/vip',
    membership_expire      DATETIME     NULL COMMENT '会员到期时间',

    -- 配额
    monthly_notice_count   INT          DEFAULT 0 COMMENT '本月已查看启事数',
    daily_notice_count     INT          DEFAULT 0 COMMENT '今日已查看启事数',
    last_reset_month       VARCHAR(7)   DEFAULT '' COMMENT '上次重置月份(YYYY-MM)',
    last_reset_day         VARCHAR(10)  DEFAULT '' COMMENT '上次重置日期(YYYY-MM-DD)',

    -- 时间
    last_login_at          DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '最后登录时间',
    created_at             DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at             DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_openid (openid),
    INDEX idx_phone  (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';


-- 启事表
CREATE TABLE IF NOT EXISTS notices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT          DEFAULT 0 COMMENT '发布用户ID(0=系统导入)',
    publisher_role  VARCHAR(20)  DEFAULT '本人' COMMENT '发布人身份(本人/父母/亲戚/朋友)',
    phone           VARCHAR(11)  DEFAULT '' COMMENT '联系方式/手机号码',
    name            VARCHAR(20)  DEFAULT '' COMMENT '姓名',
    nickname        VARCHAR(50)  DEFAULT '' COMMENT '昵称',
    gender          VARCHAR(2)   DEFAULT '' COMMENT '性别',
    age             INT          DEFAULT 0  COMMENT '年龄',
    birthday        VARCHAR(20)  DEFAULT '' COMMENT '生日',
    social_account  VARCHAR(100) DEFAULT '' COMMENT '社交账号',
    housing_location VARCHAR(20) DEFAULT '本地' COMMENT '住房位置(本地/外地)',
    occupation      VARCHAR(50)  DEFAULT '' COMMENT '职业',
    income          VARCHAR(20)  DEFAULT '' COMMENT '收入',
    is_public_sector TINYINT(1)  DEFAULT 0 COMMENT '是否体制内',
    height          INT          DEFAULT 0 COMMENT '身高(cm)',
    weight          INT          DEFAULT 0 COMMENT '体重(kg)',
    images          TEXT         COMMENT '照片列表(JSON数组，最多9张)',
    source          VARCHAR(20)  DEFAULT 'user' COMMENT '来源(user/seed/import)',
    remark          TEXT         COMMENT '备注',



    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user_id (user_id),
    INDEX idx_phone   (phone),
    INDEX idx_gender  (gender),
    INDEX idx_height  (height),
    INDEX idx_is_public_sector (is_public_sector)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='启事表';


-- 启事查看记录表
CREATE TABLE IF NOT EXISTS notice_views (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT      NOT NULL COMMENT '查看者用户ID',
    notice_id   INT      NOT NULL COMMENT '启事ID',
    viewed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_id   (user_id),
    INDEX idx_notice_id (notice_id),
    UNIQUE KEY uk_user_notice (user_id, notice_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='启事查看记录';


-- 会员订单表
CREATE TABLE IF NOT EXISTS membership_orders (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    order_no        VARCHAR(32) UNIQUE COMMENT '商户订单号',
    transaction_id  VARCHAR(64) NULL COMMENT '微信支付交易单号',
    user_id         INT         NOT NULL,
    type            VARCHAR(10) NOT NULL COMMENT 'member / vip',
    amount          INT         NOT NULL COMMENT '金额(元)',
    status          VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/paid/cancelled',

    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    paid_at         DATETIME    NULL,

    INDEX idx_user_id (user_id),
    INDEX idx_order_no (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员订单表';
