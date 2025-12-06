#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataAgent 配置文件

该文件包含 DataAgent 项目的核心配置参数
用于管理数据探索智能配置的各项设置
"""

import os
from pathlib import Path

# 项目基础配置
PROJECT_NAME = "DataAgent"
PROJECT_VERSION = "1.0.0"
PROJECT_DESCRIPTION = "数据探索智能配置系统"

# 路径配置
BASE_DIR = Path(__file__).parent.absolute()
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"

# 业务域配置
BUSINESS_DOMAINS = {
    "人员分析": ["HCM", "人力", "组织架构", "绩效", "职级", "薪酬"],
    "销售分析": ["营销域", "商务域", "客户", "CRM", "订单", "收入"],
    "财务分析": ["财务域", "成本", "利润", "预算", "资金"],
    "供应链分析": ["SCM", "供应链域", "采购", "库存", "物流"],
    "产品分析": ["研发域", "CPLM", "产品", "项目", "质量"],
    "运营分析": ["运营", "流程", "效率", "KPI", "指标"]
}

# 搜索优先级配置
SEARCH_PRIORITIES = {
    "README.md文档": 90,
    "FineBI/Reports/": 100,
    "FineBI/Datasets/": 80,
    "Standards/": 70,
    "Topics/": 75,
    "Lineage/": 60
}

# 数据库配置
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "3306"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dataagent")
}

# 日志配置
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": BASE_DIR / "logs" / "dataagent.log"
}

# API 配置
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("DEBUG", "False").lower() == "true"
}

def get_domain_keywords(domain_name):
    """获取指定业务域的关键词列表"""
    return BUSINESS_DOMAINS.get(domain_name, [])

def get_search_priority(path):
    """获取指定路径的搜索优先级"""
    for key, priority in SEARCH_PRIORITIES.items():
        if key in path:
            return priority
    return 50  # 默认优先级

def ensure_directories():
    """确保必要的目录存在"""
    directories = [DATA_DIR, CONFIG_DIR, BASE_DIR / "logs"]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# 初始化配置
ensure_directories()