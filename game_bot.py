import logging
import random
import os
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Базовый кулдаун в секундах (1200 секунд = 20 минут)
BASE_COOLDOWN = 1
MIN_COOLDOWN = 1
WAVE_COOLDOWN = 10800

# Базовые множители добычи
BASE_MIN_ITEMS = 1
BASE_MAX_ITEMS = 1000000
BASE_MIN_LIQUID = 100
BASE_MAX_LIQUID = 1000

# Словарь с ресурсами и их шансами
RESOURCES = {
    "Медь": 0.2,
    "Свинец": 0.2,
    "Уголь": 0.2,
    "Песок": 0.2,
    "Вода": 0.139,
    "Титан": 0.04,
    "Торий": 0.01,
    "Нефть": 0.01,
    "Кинетический сплав": 0.001
}

ITEM_RESOURCES = ["Медь", "Свинец", "Уголь", "Песок", "Титан", "Торий", "Кинетический сплав"]
LIQUID_RESOURCES = ["Вода", "Нефть"]
LIQUID_DISPLAY = ["Вода", "Нефть", "Криогенная жидкость"]

# Ресурсы для шахты
MINE_RESOURCES = {
    "Медь": 0.23,
    "Свинец": 0.23,
    "Песок": 0.23,
    "Уголь": 0.23,
    "Титан": 0.07,
    "Торий": 0.01
}

# Буры с обновлённой добычей
DRILLS = {
    "Медный бур": {
        "cost": {"Медь": 25},
        "production": 5,
        "emoji": "⚙️"
    },
    "Пневматический бур": {
        "cost": {"Медь": 35, "Графит": 10},
        "production": 20,
        "emoji": "⚙️"
    },
    "Лазерный бур": {
        "cost": {"Медь": 120, "Кремний": 40, "Титан": 20},
        "production": 120,
        "emoji": "⚙️"
    },
    "Воздушная бур. установка": {
        "cost": {"Медь": 250, "Свинец": 250, "Кремний": 120, "Титан": 100, "Торий": 50},
        "production": 600,
        "emoji": "⚙️"
    },
    "Epiroc Pit Viper 351": {
        "cost": {"Медь": 800, "Кремний": 400, "Титан": 250, "Фазовая ткань": 100},
        "production": 2000,
        "emoji": "🏗"
    },
    "Sandvik Pantera DP1600i": {
        "cost": {"Свинец": 2000, "Кремний": 1500, "Титан": 1500, "Фазовая ткань": 400, "Кинетический сплав": 400},
        "production": 9560,
        "emoji": "🏗"
    }
}

# Дроны
DRONES = {
    "Моно": {
        "research_cost": 1500,
        "buy_cost": 100,
        "production": 1,
        "research_key": "mono_researched",
        "count_key": "mono_count",
        "resources_key": "mono_resources"
    },
    "Поли": {
        "research_cost": 12500,
        "buy_cost": 1000,
        "production": 9,
        "research_key": "poly_researched",
        "count_key": "poly_count",
        "resources_key": "poly_resources"
    },
    "Мега": {
        "research_cost": 85000,
        "buy_cost": 7500,
        "production": 65,
        "research_key": "mega_researched",
        "count_key": "mega_count",
        "resources_key": "mega_resources"
    },
    "Квад": {
        "research_cost": 500000,
        "buy_cost": 45000,
        "production": 380,
        "research_key": "quad_researched",
        "count_key": "quad_count",
        "resources_key": "quad_resources"
    },
    "Окт": {
        "research_cost": 12500000,
        "buy_cost": 1000000,
        "production": 8500,
        "research_key": "oct_researched",
        "count_key": "oct_count",
        "resources_key": "oct_resources"
    }
}

# Турели
TURRETS = {
    "Двойная турель": {
        "cost": {"Медь": 35},
        "build_time": 5,
        "defense": 10
    },
    "Рассеиватель": {
        "cost": {"Медь": 85, "Свинец": 45},
        "build_time": 12,
        "defense": 30
    },
    "Град": {
        "cost": {"Медь": 40, "Графит": 17},
        "build_time": 15,
        "defense": 50
    },
    "Залп": {
        "cost": {"Медь": 100, "Графит": 80, "Титан": 50},
        "build_time": 30,
        "defense": 150
    },
    "Копейщик": {
        "cost": {"Медь": 60, "Свинец": 70, "Титан": 30, "Кремний": 60},
        "build_time": 40,
        "defense": 250
    },
    "Рябь": {
        "cost": {"Медь": 150, "Графит": 135, "Титан": 60},
        "build_time": 60,
        "defense": 275
    },
    "Циклон": {
        "cost": {"Медь": 200, "Титан": 125, "Пластан": 80},
        "build_time": 90,
        "defense": 600
    },
    "Взрыватель": {
        "cost": {"Медь": 225, "Графит": 225, "Торий": 100},
        "build_time": 120,
        "defense": 800
    },
    "Испепелитель": {
        "cost": {"Медь": 1200, "Свинец": 350, "Графит": 300, "Кремний": 325, "Кинетический сплав": 325},
        "build_time": 300,
        "defense": 5000
    },
    "Знамение": {
        "cost": {"Медь": 1000, "Метастекло": 600, "Кремний": 600, "Пластан": 200, "Кинетический сплав": 300},
        "build_time": 600,
        "defense": 10000
    }
}

ENEMY_TURRETS = {
    "Двойная турель": 10,
    "Рассеиватель": 20,
    "Обжигатель": 35,
    "Дуга": 20,
    "Град": 25,
    "Залп": 60,
    "Копейщик": 80,
    "Рябь": 100,
    "Роевик": 175,
    "Циклон": 225,
    "Параллакс": 5,
    "Взрыватель": 250,
    "Спектр": 1000,
    "Испепелитель": 1500,
    "Знамение": 2000,
    "Регенерирующий проектор": 150
}

# Юниты
UNITS = {
    # Мехи
    "Кинжал": {
        "cost": {"Кремний": 10, "Свинец": 10},
        "build_time": 10,
        "defense": 5,
        "category": "mech"
    },
    "Булава": {
        "cost": {"Кремний": 40, "Графит": 40},
        "build_time": 25,
        "defense": 35,
        "category": "mech"
    },
    "Крепость": {
        "cost": {"Кремний": 130, "Титан": 80, "Метастекло": 40},
        "build_time": 60,
        "defense": 120,
        "category": "mech"
    },
    "Скипетр": {
        "cost": {"Кремний": 850, "Титан": 750, "Пластан": 650, "Криогенная жидкость": 30000},
        "build_time": 360,
        "defense": 900,
        "category": "mech"
    },
    "Власть": {
        "cost": {"Кремний": 1000, "Пластан": 600, "Кинетический сплав": 500, "Фазовая ткань": 350, "Криогенная жидкость": 100000},
        "build_time": 1500,
        "defense": 5000,
        "category": "mech"
    },
    # Поддержка
    "Нова": {
        "cost": {"Кремний": 30, "Свинец": 20, "Титан": 20},
        "build_time": 10,
        "defense": 10,
        "category": "support"
    },
    "Пульсар": {
        "cost": {"Кремний": 40, "Графит": 40},
        "build_time": 28,
        "defense": 40,
        "category": "support"
    },
    "Квазар": {
        "cost": {"Кремний": 130, "Титан": 80, "Метастекло": 40},
        "build_time": 75,
        "defense": 140,
        "category": "support"
    },
    "Парус": {
        "cost": {"Кремний": 850, "Титан": 750, "Пластан": 650, "Криогенная жидкость": 30000},
        "build_time": 450,
        "defense": 1200,
        "category": "support"
    },
    "Ворон": {
        "cost": {"Кремний": 1000, "Пластан": 600, "Кинетический сплав": 500, "Фазовая ткань": 350, "Криогенная жидкость": 100000},
        "build_time": 1200,
        "defense": 4200,
        "category": "support"
    },
    # Пауки
    "Ползун": {
        "cost": {"Кремний": 8, "Уголь": 10},
        "build_time": 20,
        "defense": 10,
        "category": "spider"
    },
    "Атракс": {
        "cost": {"Кремний": 40, "Графит": 40},
        "build_time": 40,
        "defense": 50,
        "category": "spider"
    },
    "Спайрокт": {
        "cost": {"Кремний": 130, "Титан": 80, "Метастекло": 40},
        "build_time": 50,
        "defense": 110,
        "category": "spider"
    },
    "Аркид": {
        "cost": {"Кремний": 850, "Титан": 750, "Пластан": 650, "Криогенная жидкость": 30000},
        "build_time": 400,
        "defense": 1100,
        "category": "spider"
    },
    "Токсопид": {
        "cost": {"Кремний": 1000, "Пластан": 600, "Кинетический сплав": 500, "Фазовая ткань": 350, "Криогенная жидкость": 100000},
        "build_time": 1800,
        "defense": 5500,
        "category": "spider"
    },
    # Летучки
    "Вспышка": {
        "cost": {"Кремний": 15},
        "build_time": 8,
        "defense": 5,
        "category": "flyer"
    },
    "Горизонт": {
        "cost": {"Кремний": 40, "Графит": 40},
        "build_time": 30,
        "defense": 45,
        "category": "flyer"
    },
    "Зенит": {
        "cost": {"Кремний": 130, "Титан": 80, "Метастекло": 40},
        "build_time": 65,
        "defense": 130,
        "category": "flyer"
    },
    "Затемь": {
        "cost": {"Кремний": 850, "Титан": 750, "Пластан": 650, "Криогенная жидкость": 30000},
        "build_time": 390,
        "defense": 1000,
        "category": "flyer"
    },
    "Затмение": {
        "cost": {"Кремний": 1000, "Пластан": 600, "Кинетический сплав": 500, "Фазовая ткань": 350, "Криогенная жидкость": 100000},
        "build_time": 1320,
        "defense": 4800,
        "category": "flyer"
    }
}

# Вражеские базы (секторы)
SECTORS = {
    "65": {
        "name": "Сектор 65",
        "threat": "низкая",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Двойная турель": 2},
        "rewards": {"Медь": 200, "Графит": 100},
        "unlock": None,
        "next": ["4", "61", "258", "257", "13", "20"]
    },
    "71": {
        "name": "Сектор 71",
        "threat": "низкая",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Двойная турель": 3, "Рассеиватель": 2},
        "rewards": {"Медь": 400, "Свинец": 400},
        "unlock": None,
        "next": ["92", "96", "45", "117", "22", "39"]
    },
    "113": {
        "name": "Сектор 113",
        "threat": "низкая",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Двойная турель": 4, "Обжигатель": 1},
        "rewards": {"Кремний": 200},
        "unlock": None,
        "next": ["35", "189", "190", "2", "57", "11"]
    },
    "204": {
        "name": "Сектор 204",
        "threat": "низкая",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Рассеиватель": 3, "Град": 2},
        "rewards": {"Графит": 150, "Кремний": 50},
        "unlock": None,
        "next": ["102", "16", "17", "76", "242", "130"]
    },
    "203": {
        "name": "Сектор 203",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 2,
        "turrets": {"Двойная турель": 10, "Залп": 2},
        "rewards": {"Кремний": 300},
        "unlock": None,
        "next": ["38", "173", "179", "163", "200", "53"]
    },
    "165": {
        "name": "Сектор 165",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Обжигатель": 4, "Копейщик": 1},
        "rewards": {"Свинец": 400, "Графит": 300},
        "unlock": None,
        "next": ["44", "72", "223", "86", "87", "54"]
    },
    "206": {
        "name": "Сектор 206",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 2,
        "turrets": {"Дуга": 8, "Рассеиватель": 4},
        "rewards": {"Медь": 500, "Свинец": 500},
        "unlock": None,
        "next": ["196", "233", "56", "241", "149", "188"]
    },
    "160": {
        "name": "Сектор 160",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Залп": 4, "Град": 10},
        "rewards": {"Титан": 900},
        "unlock": None,
        "next": ["9", "180", "171", "256", "119", "18"]
    },
    "245": {
        "name": "Сектор 245",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Взрыватель": 2, "Регенерирующий проектор": 2, "Град": 8},
        "rewards": {"Пластан": 400},
        "unlock": None,
        "next": ["228", "123", "25", "236", "1", "24"]
    },
    "196": {
        "name": "Сектор 196",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 3,
        "turrets": {"Рябь": 4, "Обжигатель": 8},
        "rewards": {"Кремний": 600, "Метастекло": 600},
        "unlock": None,
        "next": None
    },
    "233": {
        "name": "Сектор 233",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Рябь": 6, "Двойная турель": 35},
        "rewards": {"Титан": 800, "Свинец": 1000},
        "unlock": None,
        "next": None
    },
    "56": {
        "name": "Сектор 56",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Копейщик": 8, "Роевик": 3, "Циклон": 2},
        "rewards": {"Кремний": 1500},
        "unlock": None,
        "next": None
    },
    "241": {
        "name": "Сектор 241",
        "threat": "высокая",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Залп": 20, "Регенерирующий проектор": 3},
        "rewards": {"Метастекло": 2000},
        "unlock": None,
        "next": None
    },
    "149": {
        "name": "Сектор 149",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 2,
        "turrets": {"Испепелитель": 1, "Копейщик": 12},
        "rewards": {"Пластан": 800, "Торий": 200},
        "unlock": None,
        "next": None
    },
    "188": {
        "name": "Сектор 188",
        "threat": "истребляющая",
        "core": "Атом",
        "cores_count": 3,
        "turrets": {"Испепелитель": 1, "Спектр": 3, "Взрыватель": 8, "Регенерирующий проектор": 4},
        "rewards": {"Пластан": 1000, "Кинетический сплав": 200},
        "unlock": None,
        "next": None
    },
    "9": {
        "name": "Сектор 9",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 1,
        "turrets": {"Дуга": 25},
        "rewards": {"Графит": 1200, "Свинец": 1200},
        "unlock": None,
        "next": None
    },
    "180": {
        "name": "Сектор 180",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Роевик": 5, "Град": 15},
        "rewards": {"Пластан": 600},
        "unlock": None,
        "next": None
    },
    "171": {
        "name": "Сектор 171",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 3,
        "turrets": {"Роевик": 8, "Дуга": 16},
        "rewards": {"Титан": 1200, "Пластан": 800},
        "unlock": None,
        "next": None
    },
    "256": {
        "name": "Сектор 256",
        "threat": "экстремальная",
        "core": "Штаб",
        "cores_count": 6,
        "turrets": {"Знамение": 1, "Рябь": 10},
        "rewards": {"Торий": 600},
        "unlock": None,
        "next": None
    },
    "119": {
        "name": "Сектор 119",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Спектр": 4},
        "rewards": {"Кремний": 1500, "Графит": 1500},
        "unlock": None,
        "next": None
    },
    "18": {
        "name": "Сектор 18",
        "threat": "истребляющая",
        "core": "Атом",
        "cores_count": 4,
        "turrets": {"Знамение": 3, "Взрыватель": 15},
        "rewards": {"Титан": 2000, "Пластан": 1000, "Торий": 1200},
        "unlock": None,
        "next": None
    },
    "228": {
        "name": "Сектор 228",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 4,
        "turrets": {"Копейщик": 12, "Рассеиватель": 20},
        "rewards": {"Медь": 3000, "Свинец": 3000},
        "unlock": None,
        "next": None
    },
    "123": {
        "name": "Сектор 123",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 3,
        "turrets": {"Дуга": 100},
        "rewards": {"Графит": 2500},
        "unlock": None,
        "next": None
    },
    "25": {
        "name": "Сектор 25",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 2,
        "turrets": {"Испепелитель": 2, "Роевик": 12},
        "rewards": {"Кремний": 1500, "Метастекло": 1500},
        "unlock": None,
        "next": None
    },
    "236": {
        "name": "Сектор 236",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 2,
        "turrets": {"Спектр": 6, "Циклон": 6},
        "rewards": {"Кинетический сплав": 400},
        "unlock": None,
        "next": None
    },
    "1": {
        "name": "Сектор 1",
        "threat": "истребляющая",
        "core": "Атом",
        "cores_count": 5,
        "turrets": {"Испепелитель": 4, "Спектр": 6, "Роевик": 10, "Циклон": 8, "Взрыватель": 8, "Копейщик": 16},
        "rewards": {"Торий": 2000, "Кремний": 4000},
        "unlock": None,
        "next": None
    },
    "24": {
        "name": "Сектор 24",
        "threat": "истребляющая",
        "core": "Атом",
        "cores_count": 8,
        "turrets": {"Знамение": 15, "Спектр": 30, "Регенерирующий проектор": 30},
        "rewards": {"Кремний": 5000, "Пластан": 3000, "Торий": 5000, "Кинетический сплав": 2000, "Фазовая ткань": 2000},
        "unlock": None,
        "next": None
    },
    "4": {
        "name": "Сектор 4",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Копейщик": 2, "Двойная турель": 15},
        "rewards": {"Метастекло": 300},
        "unlock": None,
        "next": None
    },
    "61": {
        "name": "Сектор 61",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Дуга": 8, "Обжигатель": 3},
        "rewards": {"Метастекло": 150, "Кремний": 150},
        "unlock": None,
        "next": None
    },
    "258": {
        "name": "Сектор 258",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Рябь": 4, "Залп": 8},
        "rewards": {"Медь": 800, "Свинец": 800},
        "unlock": None,
        "next": None
    },
    "257": {
        "name": "Сектор 257",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Дуга": 15, "Залп": 5, "Регенерирующий проектор": 1},
        "rewards": {"Кремний": 600},
        "unlock": None,
        "next": None
    },
    "13": {
        "name": "Сектор 13",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Копейщик": 5, "Рябь": 5},
        "rewards": {"Медь": 2000},
        "unlock": None,
        "next": None
    },
    "20": {
        "name": "Сектор 20",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Роевик": 3, "Обжигатель": 8},
        "rewards": {"Свинец": 2000},
        "unlock": None,
        "next": None
    },
    "92": {
        "name": "Сектор 92",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Рябь": 4},
        "rewards": {"Кремний": 300, "Графит": 300},
        "unlock": None,
        "next": None
    },
    "96": {
        "name": "Сектор 96",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Копейщик": 4, "Залп": 4},
        "rewards": {"Титан": 300},
        "unlock": None,
        "next": None
    },
    "45": {
        "name": "Сектор 45",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Циклон": 3, "Рассеиватель": 15},
        "rewards": {"Графит": 600},
        "unlock": None,
        "next": None
    },
    "117": {
        "name": "Сектор 117",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Роевик": 4, "Копейщик": 2, "Залп": 4, "Двойная турель": 15},
        "rewards": {"Кремний": 800, "Свинец": 800},
        "unlock": None,
        "next": None
    },
    "22": {
        "name": "Сектор 22",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Рябь": 6, "Залп": 6, "Регенерирующий проектор": 1},
        "rewards": {"Кремний": 500, "Титан": 500},
        "unlock": None,
        "next": None
    },
    "39": {
        "name": "Сектор 39",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Спектр": 1, "Циклон": 4, "Роевик": 4},
        "rewards": {"Титан": 1000, "Метастекло": 800},
        "unlock": None,
        "next": None
    },
    "35": {
        "name": "Сектор 35",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 3,
        "turrets": {"Залп": 6, "Рябь": 1},
        "rewards": {"Свинец": 1000, "Графит": 500},
        "unlock": None,
        "next": None
    },
    "189": {
        "name": "Сектор 189",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Роевик": 2},
        "rewards": {"Кремний": 800},
        "unlock": None,
        "next": None
    },
    "190": {
        "name": "Сектор 190",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 3,
        "turrets": {"Копейщик": 6, "Дуга": 12, "Рассеиватель": 8},
        "rewards": {"Графит": 1000},
        "unlock": None,
        "next": None
    },
    "2": {
        "name": "Сектор 2",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Циклон": 2, "Залп": 6, "Обжигатель": 4},
        "rewards": {"Кремний": 600, "Графит": 600},
        "unlock": None,
        "next": None
    },
    "57": {
        "name": "Сектор 57",
        "threat": "высокая",
        "core": "Осколок",
        "cores_count": 5,
        "turrets": {"Рябь": 10, "Регенерирующий проектор": 2, "Параллакс": 8},
        "rewards": {"Медь": 1000, "Метастекло": 600},
        "unlock": None,
        "next": None
    },
    "11": {
        "name": "Сектор 11",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Роевик": 5},
        "rewards": {"Титан": 700, "Пластан": 100},
        "unlock": None,
        "next": None
    },
    "102": {
        "name": "Сектор 102",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 2,
        "turrets": {"Рябь": 2, "Обжигатель": 6},
        "rewards": {"Титан": 600},
        "unlock": None,
        "next": None
    },
    "16": {
        "name": "Сектор 16",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 2,
        "turrets": {"Дуга": 12, "Двойная турель": 12},
        "rewards": {"Свинец": 3000},
        "unlock": None,
        "next": None
    },
    "17": {
        "name": "Сектор 17",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 4,
        "turrets": {"Роевик": 4, "Копейщик": 4},
        "rewards": {"Титан": 1000},
        "unlock": None,
        "next": None
    },
    "76": {
        "name": "Сектор 76",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Спектр": 1},
        "rewards": {"Метастекло": 500, "Графит": 500},
        "unlock": None,
        "next": None
    },
    "242": {
        "name": "Сектор 242",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Залп": 6, "Рябь": 2, "Двойная турель": 20, "Рассеиватель": 4, "Регенерирующий проектор": 1},
        "rewards": {"Медь": 1500, "Пластан": 200},
        "unlock": None,
        "next": None
    },
    "130": {
        "name": "Сектор 130",
        "threat": "экстремальная",
        "core": "Штаб",
        "cores_count": 6,
        "turrets": {"Роевик": 15, "Регенерирующий проектор": 3},
        "rewards": {"Титан": 1200, "Кремний": 1000},
        "unlock": None,
        "next": None
    },
    "38": {
        "name": "Сектор 38",
        "threat": "средняя",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Рябь": 6},
        "rewards": {"Графит": 1000},
        "unlock": None,
        "next": None
    },
    "173": {
        "name": "Сектор 173",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Циклон": 2, "Град": 12},
        "rewards": {"Метастекло": 600, "Кремний": 800},
        "unlock": None,
        "next": None
    },
    "179": {
        "name": "Сектор 179",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 1,
        "turrets": {"Копейщик": 10, "Регенерирующий проектор": 1},
        "rewards": {"Пластан": 200},
        "unlock": None,
        "next": None
    },
    "163": {
        "name": "Сектор 163",
        "threat": "высокая",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Взрыватель": 3},
        "rewards": {"Медь": 1500, "Графит": 1000},
        "unlock": None,
        "next": None
    },
    "200": {
        "name": "Сектор 200",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 2,
        "turrets": {"Спектр": 2, "Взрыватель": 4},
        "rewards": {"Кремний": 1500, "Титан": 1500},
        "unlock": None,
        "next": None
    },
    "53": {
        "name": "Сектор 53",
        "threat": "экстремальная",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Испепелитель": 2},
        "rewards": {"Кремний": 1000, "Пластан": 600},
        "unlock": None,
        "next": None
    },
    "44": {
        "name": "Сектор 44",
        "threat": "средняя",
        "core": "Осколок",
        "cores_count": 2,
        "turrets": {"Циклон": 1, "Регенерирующий проектор": 2},
        "rewards": {"Метастекло": 800},
        "unlock": None,
        "next": None
    },
    "72": {
        "name": "Сектор 72",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 2,
        "turrets": {"Копейщик": 10, "Рябь": 5, "Залп": 10},
        "rewards": {"Фазовая ткань": 100},
        "unlock": None,
        "next": None
    },
    "223": {
        "name": "Сектор 223",
        "threat": "высокая",
        "core": "Штаб",
        "cores_count": 3,
        "turrets": {"Взрыватель": 2, "Рассеиватель": 30, "Регенерирующий проектор": 1},
        "rewards": {"Кремний": 1500},
        "unlock": None,
        "next": None
    },
    "86": {
        "name": "Сектор 86",
        "threat": "высокая",
        "core": "Атом",
        "cores_count": 1,
        "turrets": {"Циклон": 6},
        "rewards": {"Графит": 1700},
        "unlock": None,
        "next": None
    },
    "87": {
        "name": "Сектор 87",
        "threat": "экстремальная",
        "core": "Штаб",
        "cores_count": 4,
        "turrets": {"Испепелитель": 1, "Взрыватель": 4, "Роевик": 6, "Регенерирующий проектор": 3},
        "rewards": {"Кремний": 2000, "Титан": 2000, "Пластан": 600},
        "unlock": None,
        "next": None
    },
    "54": {
        "name": "Сектор 54",
        "threat": "истребляющая",
        "core": "Атом",
        "cores_count": 2,
        "turrets": {"Знамение": 2, "Циклон": 12, "Регенерирующий проектор": 6},
        "rewards": {"Кремний": 3000, "Торий": 1000},
        "unlock": None,
        "next": None
    }
}

# Вражеские юниты и их урон
ENEMY_UNITS = {
    "Кинжал": 5,
    "Булава": 20,
    "Крепость": 100,
    "Скипетр": 750,
    "Власть": 5000,
    "Нова": 10,
    "Пульсар": 20,
    "Квазар": 120,
    "Парус": 1000,
    "Ворон": 4000,
    "Ползун": 15,
    "Атракс": 30,
    "Спайрокт": 100,
    "Аркид": 1200,
    "Токсопид": 6000,
    "Вспышка": 5,
    "Горизонт": 25,
    "Зенит": 120,
    "Затемь": 800,
    "Затмение": 4500
}

# Состав волн
WAVES = {
    1: [("Кинжал", 1)],
    5: [("Кинжал", 1)],
    6: [("Вспышка", 3)],
    10: [("Вспышка", 3)],
    11: [("Кинжал", 2), ("Нова", 1)],
    15: [("Кинжал", 2), ("Нова", 1)],
    16: [("Булава", 3)],
    19: [("Булава", 3)],
    20: [("Спайрокт", 1)],
    21: [("Пульсар", 3), ("Кинжал", 5)],
    25: [("Пульсар", 3), ("Кинжал", 5)],
    26: [("Вспышка", 10), ("Горизонт", 3)],
    30: [("Вспышка", 10), ("Горизонт", 3)],
    31: [("Пульсар", 5), ("Нова", 10)],
    35: [("Пульсар", 5), ("Нова", 10)],
    36: [("Булава", 3), ("Кинжал", 10), ("Ползун", 5)],
    39: [("Булава", 3), ("Кинжал", 10), ("Ползун", 5)],
    40: [("Крепость", 3)],
    41: [("Атракс", 3), ("Горизонт", 5), ("Ползун", 10)],
    45: [("Атракс", 3), ("Горизонт", 5), ("Ползун", 10)],
    46: [("Кинжал", 15), ("Вспышка", 20), ("Булава", 5)],
    50: [("Кинжал", 15), ("Вспышка", 20), ("Булава", 5)],
    51: [("Кинжал", 25), ("Зенит", 1), ("Пульсар", 10)],
    55: [("Кинжал", 25), ("Зенит", 1), ("Пульсар", 10)],
    56: [("Квазар", 3), ("Крепость", 3), ("Вспышка", 30)],
    59: [("Квазар", 3), ("Крепость", 3), ("Вспышка", 30)],
    60: [("Скипетр", 1)],
    61: [("Квазар", 5), ("Горизонт", 15), ("Кинжал", 30), ("Нова", 20)],
    65: [("Квазар", 5), ("Горизонт", 15), ("Кинжал", 30), ("Нова", 20)],
    66: [("Крепость", 5), ("Ползун", 30), ("Атракс", 10)],
    69: [("Крепость", 5), ("Ползун", 30), ("Атракс", 10)],
    70: [("Зенит", 5), ("Спайрокт", 5)],
    75: [("Зенит", 5), ("Спайрокт", 5)],
    76: [("Квазар", 10), ("Пульсар", 20)],
    79: [("Квазар", 10), ("Пульсар", 20)],
    80: [("Парус", 2)],
    81: [("Крепость", 10), ("Зенит", 10)],
    85: [("Крепость", 10), ("Зенит", 10)],
    86: [("Квазар", 15)],
    90: [("Квазар", 15)],
    91: [("Спайрокт", 10), ("Атракс", 30)],
    95: [("Спайрокт", 10), ("Атракс", 30)],
    96: [("Скипетр", 1), ("Квазар", 5)],
    99: [("Скипетр", 1), ("Квазар", 5)],
    100: [("Власть", 1)],
    101: [("Зенит", 15)],
    110: [("Зенит", 15)],
    111: [("Скипетр", 1), ("Крепость", 15)],
    120: [("Скипетр", 1), ("Крепость", 15)],
    121: [("Спайрокт", 25)],
    130: [("Спайрокт", 25)],
    131: [("Парус", 1), ("Квазар", 10)],
    140: [("Парус", 1), ("Квазар", 10)],
    141: [("Затемь", 3)],
    149: [("Затемь", 3)],
    150: [("Затмение", 1)],
    151: [("Крепость", 25), ("Зенит", 25)],
    170: [("Крепость", 25), ("Зенит", 25)],
    171: [("Аркид", 1), ("Квазар", 15)],
    190: [("Аркид", 1), ("Квазар", 15)],
    191: [("Скипетр", 3), ("Спайрокт", 20)],
    199: [("Скипетр", 3), ("Спайрокт", 20)],
    200: [("Токсопид", 1)],
    201: [("Парус", 3), ("Квазар", 25)],
    220: [("Парус", 3), ("Квазар", 25)],
    221: [("Скипетр", 3), ("Зенит", 25)],
    240: [("Скипетр", 3), ("Зенит", 25)],
    241: [("Аркид", 5)],
    249: [("Аркид", 5)],
    250: [("Ворон", 1), ("Парус", 3)],
    251: [("Скипетр", 5)],
    299: [("Скипетр", 5)],
    300: [("Власть", 3)],
    301: [("Затемь", 5)],
    349: [("Затемь", 5)],
    350: [("Затмение", 3)],
    351: [("Аркид", 5)],
    399: [("Аркид", 5)],
    400: [("Токсопид", 3)],
    401: [("Парус", 5)],
    449: [("Парус", 5)],
    450: [("Ворон", 3)],
    451: [("Затмение", 2), ("Скипетр", 10)],
    460: [("Затмение", 2), ("Скипетр", 10)],
    461: [("Ворон", 3), ("Аркид", 10)],
    470: [("Ворон", 3), ("Аркид", 10)],
    471: [("Токсопид", 2), ("Парус", 10)],
    480: [("Токсопид", 2), ("Парус", 10)],
    481: [("Власть", 3), ("Затемь", 10)],
    490: [("Власть", 3), ("Затемь", 10)],
    491: [("Токсопид", 5), ("Скипетр", 5), ("Парус", 5)],
    499: [("Токсопид", 5), ("Скипетр", 5), ("Парус", 5)],
}

def get_max_units_per_type(core):
    if core == 'Осколок':
        return 8
    elif core == 'Штаб':
        return 16
    else:
        return 24

def get_wave_composition(wave):
    for w in sorted(WAVES.keys()):
        if wave <= w:
            return WAVES[w]
    return WAVES[499]

def get_wave_damage(wave):
    composition = get_wave_composition(wave)
    total_damage = 0
    for unit_name, count in composition:
        total_damage += ENEMY_UNITS.get(unit_name, 0) * count
    return total_damage

# Шансы для ежедневного подарка
COIN_CHANCES = [
    (40, 500), (30, 1000), (15, 2000), (7, 5000), (5, 10000),
    (2, 25000), (0.8, 100000), (0.15, 500000), (0.04, 2500000), (0.01, 10000000)
]

ARTIFACT_CHANCES = [
    (40, 0), (30, 1), (15, 2), (7, 3), (5, 5),
    (2, 10), (0.8, 25), (0.15, 100), (0.04, 500), (0.01, 2000)
]

UNIQUE_ITEMS = {
    "Сломанный медный бур": 50,
    "Конвейер": 50,
    "Помпа": 25,
    "Силовой узел": 25,
    "Генератор внутреннего сгорания": 15,
    "Кремниевая плавильня": 10,
    "Паровой генератор": 10,
    "Пластановый компрессор": 7,
    "Радиоизотопный термоэлектрический генератор": 5,
    "Фазовый ткач": 5,
    "Умножающий реконструктор": 2,
    "Ториевый реактор": 2,
    "Сверхприводный проектор": 1,
    "Малый логический процессор": 1,
    "Силовой проектор": 0.5,
    "Импульсный реактор": 0.5,
    "Экспоненциальный реконструктор": 0.2,
    "Логический процессор": 0.1,
    "Тетративный реконструктор": 0.05,
    "Большой логический процессор": 0.01
}

UNIQUE_ITEMS_LIST = {
    "Сломанный медный бур": {"emoji": "⚫️ ", "rarity": "Обычный"},
    "Конвейер": {"emoji": "⚫️ ", "rarity": "Обычный"},
    "Помпа": {"emoji": "⚫️ ", "rarity": "Обычный"},
    "Силовой узел": {"emoji": "⚫️ ", "rarity": "Обычный"},
    "Генератор внутреннего сгорания": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Кремниевая плавильня": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Паровой генератор": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Пластановый компрессор": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Радиоизотопный термоэлектрический генератор": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Фазовый ткач": {"emoji": "🔵 ", "rarity": "Редкий"},
    "Умножающий реконструктор": {"emoji": "🟣 ", "rarity": "Эпический"},
    "Ториевый реактор": {"emoji": "🟣 ", "rarity": "Эпический"},
    "Сверхприводный проектор": {"emoji": "🟣 ", "rarity": "Эпический"},
    "Малый логический процессор": {"emoji": "🟣 ", "rarity": "Эпический"},
    "Силовой проектор": {"emoji": "🟡 ", "rarity": "Легендарный"},
    "Импульсный реактор": {"emoji": "🟡 ", "rarity": "Легендарный"},
    "Экспоненциальный реконструктор": {"emoji": "🟡 ", "rarity": "Легендарный"},
    "Логический процессор": {"emoji": "🟡 ", "rarity": "Легендарный"},
    "Тетративный реконструктор": {"emoji": "🌌 ", "rarity": "Божественный"},
    "Большой логический процессор": {"emoji": "🌌 ", "rarity": "Божественный"}
}

INSULTS_RESPONSES = [
    "Жалкий кукидрочер",
    "Сделай сальто с окна",
    "Включи газовую плиту и закрой окна",
    "Бог тебя не простит..."
]

def get_random_resource():
    rand = random.random()
    cumulative = 0
    for resource, chance in RESOURCES.items():
        cumulative += chance
        if rand <= cumulative:
            return resource
    return "Медь"

def get_mine_resource():
    rand = random.random()
    cumulative = 0
    for resource, chance in MINE_RESOURCES.items():
        cumulative += chance
        if rand <= cumulative:
            return resource
    return "Медь"

def get_random_value(chances):
    rand = random.random() * 100
    cumulative = 0
    for chance, value in chances:
        cumulative += chance
        if rand <= cumulative:
            return value
    return chances[-1][1]

def get_unique_items():
    obtained = []
    for item, chance in UNIQUE_ITEMS.items():
        if random.random() * 100 <= chance:
            obtained.append(item)
    return obtained

def get_turret_gift():
    if random.random() * 100 <= 20:
        turrets = ["Двойная турель", "Рассеиватель", "Град", "Копейщик"]
        turret = random.choice(turrets)
        amount = random.randint(1, 4)
        return turret, amount
    return None, 0

def get_resource_amount(resource, user_data=None):
    if resource in ITEM_RESOURCES:
        if user_data and 'mining_multiplier' in user_data:
            max_amount = int(BASE_MAX_ITEMS * user_data['mining_multiplier'])
            min_amount = int(BASE_MIN_ITEMS * user_data['mining_multiplier'])
            return random.randint(min_amount, max_amount)
        return random.randint(BASE_MIN_ITEMS, BASE_MAX_ITEMS)
    elif resource in LIQUID_RESOURCES:
        if user_data and 'mining_multiplier' in user_data:
            max_amount = int(BASE_MAX_LIQUID * user_data['mining_multiplier'])
            min_amount = int(BASE_MIN_LIQUID * user_data['mining_multiplier'])
            return random.randint(min_amount, max_amount)
        return random.randint(BASE_MIN_LIQUID, BASE_MAX_LIQUID)
    return 1

def get_upgrade_cost(level):
    return 1 * (2 ** (level)) if level > 0 else 1

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def safe_edit_message(query, text=None, reply_markup=None, parse_mode=None):
    try:
        if text is not None:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception:
        pass

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "Привет! Я - Mindustry Копатель Бот.⛏️ \n\n"
        "Eсли хочешь узнать список команд, используй /help"
    )

async def craft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    craft_text = (
        "🛠 *Крафтинг станция*\n\n"
        "Графит - 2шт Уголь (0,01🔮/4🪙)\n"
        "Метастекло - 1шт Песок, 1шт Свинец (0,02🔮/4🪙)\n"
        "Кремний - 2шт Песок, 1шт Уголь (0,05🔮/5🪙)\n"
        "Споровый стручок - 200мл Вода (0,01🔮/5🪙)\n"
        "Пластан - 2шт Титан, 100мл Нефть (0,2🔮/25🪙)\n"
        "Кинетический сплав - 3шт Медь, 4шт Свинец, 2шт Титан, 3шт Кремний (1🔮/50🪙)\n"
        "Фазовая ткань - 4шт Торий, 10шт Песок (0,5🔮/100🪙)\n"
        "Пиротит - 2шт Свинец, 2шт Песок, 1шт Уголь (0,05🔮/10🪙)\n"
        "Взрывчатая смесь - 1шт Пиротит, 1шт Споровый стручок (0,2🔮/30🪙)\n"
        "Нефть (100 мл) - 500мл Вода, 2шт Песок (5🪙)\n"
        "Криогенная жидкость (100 мл) - 100мл Вода, 1шт Титан (10🪙)\n\n"
        "Графит - graphite\n"
        "Метастекло - metaglass\n"
        "Кремний - silicon\n"
        "Споровый стручок - sporepod\n"
        "Пластан - plastanium\n"
        "Кинетический сплав - surgealloy\n"
        "Фазовая ткань - phasefabric\n"
        "Пиротит - pyratite\n"
        "Взрывчатая смесь - blastcompound\n"
        "Нефть - oil\n"
        "Криогенная жидкость - cryofluid\n\n"
        "Выбери ресурс в нужном количестве, чтобы скрафтить\n"
        "Пример: 10 кинетического сплава - /craftsurgealloy 10"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shop_text = (
        "🔮 *Магазин Токсопида* 🕷\n\n"
        "Обменивай свои добытые и скрафченные ресурсы на 🔮Артефакты или 🪙Монеты, чтобы покупать на них улучшения и добывать еще больше ресурсов!\n\n"
        "1 Артефакт🔮 = 1000 Монет🪙\n\n"
        "/buyartifact 1 - купить 1 артефакт\n"
        "/exchangephasefabricartifact 1 - обменять 2 Фазовой ткани на 1 Артефакт\n"
        "/exchangesilicon 5 - обменять 5 Кремния на 25 монет"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def drawings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if 'active_drawing' in context.bot_data and user_id in context.bot_data['active_drawing']:
        active = context.bot_data['active_drawing'][user_id]
        elapsed = time.time() - active['start_time']
        remaining = int((active['build_time'] * active['count']) - elapsed)
        if remaining < 0:
            remaining = 0
        
        type_emoji = "🤖" if active.get('is_unit', False) else "🔫"
        
        text = f"📜 *Активный чертеж:*\n\n"
        text += f"{type_emoji} {active['name']}\n"
        text += f"Количество: {active['count']} шт.\n"
        text += f"💥 Вооружение (общ): {active['defense'] * active['count']} Единиц\n"
        text += f"⏳️ Оставшееся время: {remaining} сек"
        
        keyboard = []
        if remaining > 0:
            coins_cost = remaining * 1000
            artifacts_cost = remaining
            keyboard.append([InlineKeyboardButton(f"⏱️ Ускорить ({coins_cost}🪙 )", callback_data=f"speedup_coins_{remaining}")])
            keyboard.append([InlineKeyboardButton(f"⏱️ Ускорить ({artifacts_cost}🔮 )", callback_data=f"speedup_artifacts_{remaining}")])
        keyboard.append([InlineKeyboardButton("❌ Отменить чертеж", callback_data="drawing_cancel")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
        
        if update.callback_query:
            await safe_edit_message(update.callback_query, text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    if 'drawings' not in context.bot_data:
        context.bot_data['drawings'] = {}
    
    if user_id not in context.bot_data['drawings']:
        context.bot_data['drawings'][user_id] = []
    
    drawings = context.bot_data['drawings'][user_id]
    
    if not drawings:
        await update.message.reply_text(
            f"📜 *Список чертежей игрока {user_name}:*\n\nЧертежи отсутствуют, чтобы создать новый чертеж, загляни в /sector",
            parse_mode='Markdown'
        )
        return
    
    text = f"📜 *Список чертежей игрока {user_name}:*\n\n"
    keyboard = []
    row = []
    
    for i, drawing in enumerate(drawings, 1):
        type_emoji = "🤖" if drawing.get('is_unit', False) else "🔫"
        text += f"*Чертеж #{i}*\n{type_emoji} {drawing['name']}\nКоличество: {drawing['count']} шт.\n💥 Вооружение (общ): {drawing['defense'] * drawing['count']} Единиц\n⏳️ Время создания (общ): {drawing['build_time'] * drawing['count']} сек\n\n"
        
        button = InlineKeyboardButton(f"{drawing['name']} {drawing['count']}шт. (5🔮)", callback_data=f"drawing_start_{i-1}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])

    text += "Выберите чертеж, который хотите выполнить:"
    
    if update.callback_query:
        await safe_edit_message(update.callback_query, text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ========== СЕКТОР ==========

async def sector_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟡 Моя база", callback_data="sector_my_base")],
        [InlineKeyboardButton("🔴 Вражеские базы", callback_data="sector_enemy_bases")],
        [InlineKeyboardButton("🛠 Создать турель/юнита", callback_data="sector_build")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚔️ *Сектор*\n\n"
        "Улучшай защиту своей базы, делай атаки на вражеские сектора чтобы получать ресурсы и разблокировать новые турели/юниты!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def sector_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔫 Турели", callback_data="sector_turret_build")],
        [InlineKeyboardButton("🤖 Юниты", callback_data="sector_unit_build")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="sector_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Выберите категорию:", reply_markup=reply_markup)

async def sector_turret_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    row = []
    turrets_list = list(TURRETS.keys())
    for i, turret_name in enumerate(turrets_list):
        button = InlineKeyboardButton(turret_name, callback_data=f"turret_select_{i}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="sector_build")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Выберите турель, которую хотите поместить в чертежи:", reply_markup=reply_markup)

# ========== ЮНИТЫ ==========

async def sector_unit_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    row = []
    
    categories = [
        ("🤖 Мехи", "unit_category_mech"),
        ("🚨 Поддержка", "unit_category_support"),
        ("🕷 Пауки", "unit_category_spider"),
        ("✈️ Летучки", "unit_category_flyer")
    ]
    
    for name, callback in categories:
        row.append(InlineKeyboardButton(name, callback_data=callback))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="sector_build")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Выберите категорию юнитов:", reply_markup=reply_markup)

async def unit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    category = data.replace("unit_category_", "")
    
    units_list = [name for name, info in UNITS.items() if info['category'] == category]
    
    keyboard = []
    row = []
    for unit_name in units_list:
        button = InlineKeyboardButton(unit_name, callback_data=f"unit_select_{unit_name}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️  Назад", callback_data="sector_unit_build")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, f"Выберите юнита из категории:", reply_markup=reply_markup)

async def unit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    name = query.data.replace("unit_select_", "")
    unit = UNITS[name]
    user_id = update.effective_user.id
    
    # Проверяем и создаем данные если нет
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 100, 'artifacts': 0}
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    cost = ", ".join(f"{a} {r}" for r, a in unit['cost'].items())
    text = f"{name}\n💸  {cost}\n⏳ {unit['build_time']} сек\n💥  {unit['defense']} атаки"
    inv = context.bot_data['all_inventories'][user_id]
    
    core = context.bot_data['sector'][user_id].get('core', 'Осколок')
    max_per_type = get_max_units_per_type(core)
    current_units = context.bot_data['sector'][user_id].get('units', {}).get(name, 0)
    available_slots = max_per_type - current_units
    
    # Кнопки количества (уменьшенные - 2 колонки)
    keyboard = []
    row = []
    for a in [1, 2, 4, 8, 16, 24]:
        can = all(inv.get(r, 0) >= c * a for r, c in unit['cost'].items())
        if a > available_slots:
            can = False
        button = InlineKeyboardButton(f"{a} {'✅' if can else '❌'}", callback_data=f"unit_buy_{name}_{a}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️  Назад", callback_data=f"unit_category_{unit['category']}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def unit_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    name = parts[2]
    amount = int(parts[3])
    unit = UNITS[name]
    user_id = update.effective_user.id
    
    # Проверяем и создаем данные если нет
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 100, 'artifacts': 0}
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    inv = context.bot_data['all_inventories'][user_id]
    
    # Проверка ресурсов
    for r, c in unit['cost'].items():
        if inv.get(r, 0) < c * amount:
            # Недостаточно ресурсов - показываем кнопку Назад
            keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"unit_select_{name}")]]
            await query.edit_message_text("❌ Недостаточно ресурсов!", reply_markup=InlineKeyboardMarkup(keyboard))
            return
    
    # Проверка лимита
    core = context.bot_data['sector'][user_id].get('core', 'Осколок')
    max_per_type = get_max_units_per_type(core)
    current_units = context.bot_data['sector'][user_id].get('units', {}).get(name, 0)
    available_slots = max_per_type - current_units
    
    if amount > available_slots:
        keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"unit_select_{name}")]]
        await query.edit_message_text(f"❌ Не хватает места! Можно еще {available_slots} шт. {name}", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Проверка лимита чертежей
    if 'drawings' not in context.bot_data:
        context.bot_data['drawings'] = {}
    if user_id not in context.bot_data['drawings']:
        context.bot_data['drawings'][user_id] = []
    
    if len(context.bot_data['drawings'][user_id]) >= 10:
        keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"unit_select_{name}")]]
        await query.edit_message_text("❌ У вас уже максимальное количество чертежей 10/10!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Списываем ресурсы
    for r, c in unit['cost'].items():
        inv[r] -= c * amount
        if inv[r] == 0:
            del inv[r]
    
    # Добавляем в чертежи
    context.bot_data['drawings'][user_id].append({'name': name, 'count': amount, 'defense': unit['defense'], 'build_time': unit['build_time'], 'is_unit': True})
    
    # Кнопка Назад к выбору количества
    keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"unit_select_{name}")]]
    await query.edit_message_text(f"✅ {name} в количестве {amount} шт. помещена в ваши чертежи!", reply_markup=InlineKeyboardMarkup(keyboard))

async def sector_turret_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    turret_index = int(data.split("_")[2])
    
    turrets_list = list(TURRETS.keys())
    if turret_index < 0 or turret_index >= len(turrets_list):
        await safe_edit_message(query, "❌ Ошибка: турель не найдена!")
        return
    
    turret_name = turrets_list[turret_index]
    turret = TURRETS[turret_name]
    
    cost_text = ""
    for resource, amount in turret['cost'].items():
        cost_text += f"{amount} {resource}, "
    cost_text = cost_text[:-2]
    
    text = f"🔫 *{turret_name}*\n\n"
    text += f"💸 Стоимость производства (1 Шт.): {cost_text}\n"
    text += f"⏳️ Время производства (1 Шт.): {turret['build_time']} Секунд\n"
    text += f"💥 Вооружение базы (1 Шт.): {turret['defense']} Единиц"
    
    user_id = update.effective_user.id
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    keyboard = []
    row = []
    for amount in [1, 2, 5, 10, 25, 100]:
        can_buy = True
        for resource, cost in turret['cost'].items():
            if inventory.get(resource, 0) < cost * amount:
                can_buy = False
                break
        status = "✅" if can_buy else "❌"
        button = InlineKeyboardButton(f"{amount} {status}", callback_data=f"turret_buy_{turret_index}_{amount}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="sector_turret_build")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, text, parse_mode='Markdown', reply_markup=reply_markup)

async def sector_turret_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    data = query.data
    parts = data.split("_")
    turret_index = int(parts[2])
    amount = int(parts[3])
    
    turrets_list = list(TURRETS.keys())
    if turret_index < 0 or turret_index >= len(turrets_list):
        await safe_edit_message(query, "❌ Ошибка: турель не найдена!")
        return
    
    turret_name = turrets_list[turret_index]
    turret = TURRETS[turret_name]
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    # Проверка ресурсов
    for resource, cost in turret['cost'].items():
        if inventory.get(resource, 0) < cost * amount:
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_turret_build")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await safe_edit_message(query, "❌ Недостаточно ресурсов!", reply_markup=reply_markup)
            return
    
    # Проверка лимита чертежей
    if 'drawings' not in context.bot_data:
        context.bot_data['drawings'] = {}
    if user_id not in context.bot_data['drawings']:
        context.bot_data['drawings'][user_id] = []
    
    if len(context.bot_data['drawings'][user_id]) >= 10:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_build")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message(query, "❌ У вас уже максимальное количество чертежей 10/10!", reply_markup=reply_markup)
        return
    
    # Списываем ресурсы
    for resource, cost in turret['cost'].items():
        inventory[resource] -= cost * amount
        if inventory[resource] == 0:
            del inventory[resource]
    
    context.bot_data['drawings'][user_id].append({
        'name': turret_name,
        'count': amount,
        'defense': turret['defense'],
        'build_time': turret['build_time'],
        'is_unit': False
    })
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_turret_build")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, f"✅ {turret_name} в количестве {amount} шт. помещена в ваши чертежи!", reply_markup=reply_markup)

async def drawing_start(update: Update, context: ContextTypes.DEFAULT_TYPE, drawing_index):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    
    if 'active_drawing' in context.bot_data and user_id in context.bot_data['active_drawing']:
        await safe_edit_message(query, "❌ У вас уже есть активный чертеж! Дождитесь его завершения или отмените.")
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    if inventory.get('artifacts', 0) < 5:
        await safe_edit_message(query, "❌ Недостаточно артефактов для начала выполнения чертежа!")
        return
    
    if 'drawings' not in context.bot_data:
        context.bot_data['drawings'] = {}
    if user_id not in context.bot_data['drawings']:
        context.bot_data['drawings'][user_id] = []
    
    drawings = context.bot_data['drawings'][user_id]
    
    if drawing_index >= len(drawings):
        await drawings_command(update, context)
        return
    
    drawing = drawings[drawing_index]
    
    # Проверка лимита юнитов на базе (если это юнит)
    if drawing.get('is_unit', False):
        if 'sector' not in context.bot_data or user_id not in context.bot_data['sector']:
            core = 'Осколок'
        else:
            core = context.bot_data['sector'][user_id].get('core', 'Осколок')
        
        max_per_type = get_max_units_per_type(core)
        current_units = context.bot_data['sector'][user_id].get('units', {}).get(drawing['name'], 0)
        available_slots = max_per_type - current_units
        
        if drawing['count'] > available_slots:
            await safe_edit_message(query, f"❌ Недостаточно места на базе! (Максимум {max_per_type} шт. {drawing['name']}, у вас {current_units})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drawings_back")]]))
            return
    
    inventory['artifacts'] -= 5
    
    if 'active_drawing' not in context.bot_data:
        context.bot_data['active_drawing'] = {}
    
    context.bot_data['active_drawing'][user_id] = {
        'index': drawing_index,
        'name': drawing['name'],
        'count': drawing['count'],
        'defense': drawing['defense'],
        'build_time': drawing['build_time'],
        'start_time': time.time(),
        'is_unit': drawing.get('is_unit', False)
    }
    
    asyncio.create_task(complete_drawing(update, context, user_id, user_name, username))
    
    await drawings_command(update, context)

async def speedup_drawing(update: Update, context: ContextTypes.DEFAULT_TYPE, currency, seconds):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if 'active_drawing' not in context.bot_data or user_id not in context.bot_data['active_drawing']:
        await safe_edit_message(query, "❌ Нет активного чертежа!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drawings_back")]]))
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    active = context.bot_data['active_drawing'][user_id]
    elapsed = time.time() - active['start_time']
    remaining = int((active['build_time'] * active['count']) - elapsed)
    
    if remaining <= 0:
        await complete_drawing_now(update, context, user_id)
        return
    
    if seconds > remaining:
        seconds = remaining
    
    if currency == "coins":
        cost = seconds * 1000
        if inventory.get('coins', 0) < cost:
            await safe_edit_message(query, f"❌ Недостаточно монет! Нужно {cost}🪙", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drawings_back")]]))
            return
        inventory['coins'] -= cost
    else:
        cost = seconds
        if inventory.get('artifacts', 0) < cost:
            await safe_edit_message(query, f"❌ Недостаточно артефактов! Нужно {cost}🔮", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drawings_back")]]))
            return
        inventory['artifacts'] -= cost
    
    active['start_time'] = time.time() - (active['build_time'] * active['count'] - remaining + seconds)
    
    new_elapsed = time.time() - active['start_time']
    if new_elapsed >= active['build_time'] * active['count']:
        await complete_drawing_now(update, context, user_id)
    else:
        await drawings_command(update, context)

async def complete_drawing_now(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    if 'active_drawing' not in context.bot_data or user_id not in context.bot_data['active_drawing']:
        return
    
    active = context.bot_data['active_drawing'][user_id]
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    name = active['name']
    count = active['count']
    defense_per_item = active['defense']
    is_unit = active.get('is_unit', False)
    
    if is_unit:
        sector_data['units'][name] = sector_data['units'].get(name, 0) + count
    else:
        sector_data['turrets'][name] = sector_data['turrets'].get(name, 0) + count
    
    sector_data['weapons'] += defense_per_item * count
    
    if 'drawings' in context.bot_data and user_id in context.bot_data['drawings']:
        drawings = context.bot_data['drawings'][user_id]
        index_to_remove = active['index']
        if 0 <= index_to_remove < len(drawings):
            drawings.pop(index_to_remove)
    
    del context.bot_data['active_drawing'][user_id]
    
    await drawings_command(update, context)

async def complete_drawing(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, user_name, username):
    await asyncio.sleep(1)
    
    while True:
        if 'active_drawing' not in context.bot_data or user_id not in context.bot_data['active_drawing']:
            return
        
        active = context.bot_data['active_drawing'][user_id]
        elapsed = time.time() - active['start_time']
        total_time = active['build_time'] * active['count']
        
        if elapsed >= total_time:
            if 'sector' not in context.bot_data:
                context.bot_data['sector'] = {}
            if user_id not in context.bot_data['sector']:
                context.bot_data['sector'][user_id] = {
                    'core': 'Осколок',
                    'weapons': 0,
                    'turrets': {},
                    'units': {},
                    'wave': 1,
                    'last_attack_time': time.time(),
                    'last_wave_damage': 0,
                    'last_wave_composition': None,
                    'captured_sectors': []
                }
            
            sector_data = context.bot_data['sector'][user_id]
            name = active['name']
            count = active['count']
            defense_per_item = active['defense']
            is_unit = active.get('is_unit', False)
            
            if is_unit:
                sector_data['units'][name] = sector_data['units'].get(name, 0) + count
            else:
                sector_data['turrets'][name] = sector_data['turrets'].get(name, 0) + count
            
            sector_data['weapons'] += defense_per_item * count
            
            if 'drawings' in context.bot_data and user_id in context.bot_data['drawings']:
                drawings = context.bot_data['drawings'][user_id]
                index_to_remove = active['index']
                if 0 <= index_to_remove < len(drawings):
                    drawings.pop(index_to_remove)
            
            del context.bot_data['active_drawing'][user_id]
            
            type_text = "юниты" if is_unit else "турели"
            if username:
                message_text = f"@{username}, ✅ Чертеж завершен! {name} в количестве {count} шт. добавлены на базу!"
            else:
                message_text = f"✅ Чертеж завершен! {name} в количестве {count} шт. добавлены на базу!"
            
            try:
                await update.effective_user.send_message(message_text)
            except:
                pass
            break
        
        await asyncio.sleep(5)

async def drawing_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if 'active_drawing' in context.bot_data and user_id in context.bot_data['active_drawing']:
        del context.bot_data['active_drawing'][user_id]
    
    await drawings_command(update, context)

async def drawings_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await drawings_command(update, context)

async def sector_my_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    current_time = time.time()
    
    while current_time - sector_data.get('last_attack_time', current_time) >= WAVE_COOLDOWN:
        sector_data['last_attack_time'] = sector_data.get('last_attack_time', current_time) + WAVE_COOLDOWN
        
        wave_composition = get_wave_composition(sector_data['wave'])
        wave_damage = get_wave_damage(sector_data['wave'])
        
        sector_data['last_wave_composition'] = wave_composition
        sector_data['last_wave_damage'] = wave_damage
        sector_data['weapons'] = sector_data.get('weapons', 0) - wave_damage
        sector_data['wave'] += 1
    
    weapons = sector_data['weapons']
    
    # Определяем уровень и звание
    if weapons < 1000:
        rank = "◽️ Начинающий (Lv. 1)"
    elif weapons < 2500:
        rank = "◻️ Осваивающийся (Lv. 2)"
    elif weapons < 10000:
        rank = "◾️ Любитель (Lv. 3)"
    elif weapons < 50000:
        rank = "◼️ Продвинутый (Lv. 4)"
    elif weapons < 150000:
        rank = "🔶 ️Эксперт (Lv. 5)"
    elif weapons < 2000000:
        rank = "🔷 ️Мастер (Lv. 6)"
    elif weapons < 30000000:
        rank = "🔺 ️Легенда (Lv. 7)"
    else:
        rank = "💠  Бог (Lv. 8)"
    
    base_text = f"🌐 *База игрока {user_name}:*\n\n"
    base_text += f"{rank}\n"
    base_text += f"🛡 Ядро: {sector_data['core']}\n"
    
    weapons_display = f"{weapons}"
    if weapons < 0:
        weapons_display += " ❗️ "
    base_text += f"💥 Вооружение базы: {weapons_display}\n\n"
    
    if sector_data.get('turrets'):
        base_text += "🔫  *Турели:*\n"
        for turret, count in sector_data['turrets'].items():
            defense = TURRETS.get(turret, {}).get('defense', 10)
            base_text += f"{turret} - {count} шт. 🛡{defense * count} Защиты\n"
        base_text += "\n"
    
    if sector_data.get('units'):
        base_text += "🤖  *Юниты:*\n"
        for unit, count in sector_data['units'].items():
            defense = UNITS.get(unit, {}).get('defense', 5)
            base_text += f"{unit} - {count} шт. ⚔️ {defense * count} Атаки\n"
        base_text += "\n"
    
    base_text += "📊  *Статус:*\n"
    base_text += "🔴  База подвергается атаке, уничтожьте вражеские базы, чтобы предотвратить волны\n"
    remaining = WAVE_COOLDOWN - (current_time - sector_data['last_attack_time'])
    if remaining < 0:
        remaining = 0
    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)
    seconds = int(remaining % 60)
    base_text += f"⚔️  Следующая волна через: {hours} ч {minutes} мин {seconds} сек\n"
    
    if sector_data.get('last_wave_composition'):
        wave_num = sector_data['wave'] - 1
        base_text += f"\n💀  *База была подвержена атаке!*\n"
        base_text += f"Волна: {wave_num}\n"
        base_text += "Враг отправил на вас: "
        unit_parts = []
        for unit_name, count in sector_data['last_wave_composition']:
            unit_parts.append(f"{unit_name} {count}шт")
        base_text += ", ".join(unit_parts) + "\n"
        
        damage = sector_data['last_wave_damage']
        damage_display = f"{damage}"
        if sector_data['weapons'] < 0:
            damage_display += " ❗️ "
        base_text += f"💥  База стала уязвимее на {damage_display} Единиц!"
    
    keyboard = []
    
    if sector_data['core'] == 'Осколок':
        keyboard.append([InlineKeyboardButton("🛡 Построить ядро Штаб", callback_data="sector_foundation")])
    elif sector_data['core'] == 'Штаб':
        keyboard.append([InlineKeyboardButton("🛡 Построить ядро Атом", callback_data="sector_nucleus")])
    
    keyboard.append([InlineKeyboardButton("⬅️  Назад", callback_data="sector_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, base_text, parse_mode='Markdown', reply_markup=reply_markup)

# ========== ЯДРО ШТАБ ==========

async def sector_foundation(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    
    if sector_data['core'] != 'Осколок':
        await sector_my_base(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Построить", callback_data="sector_foundation_build")],
        [InlineKeyboardButton("❌ Отменить", callback_data="sector_my_base")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Построить ядро Штаб за 4000 Медь, 4000 Свинец, 1500 Кремний?", reply_markup=reply_markup)

async def sector_foundation_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    if inventory.get('Медь', 0) < 4000 or inventory.get('Свинец', 0) < 4000 or inventory.get('Кремний', 0) < 1500:
        await safe_edit_message(query, "❌ Недостаточно ресурсов для улучшения ядра!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="sector_my_base")]]))
        return
    
    inventory['Медь'] -= 4000
    inventory['Свинец'] -= 4000
    inventory['Кремний'] -= 1500
    
    if inventory['Медь'] == 0: del inventory['Медь']
    if inventory['Свинец'] == 0: del inventory['Свинец']
    if inventory['Кремний'] == 0: del inventory['Кремний']
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    sector_data['core'] = 'Штаб'
    sector_data['weapons'] += 3000
    
    await safe_edit_message(query, "✅ Ядро улучшено до Штаба! +3000 к вооружению базы!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="sector_my_base")]]))

# ========== ЯДРО АТОМ ==========

async def sector_nucleus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    
    if sector_data['core'] != 'Штаб':
        await sector_my_base(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Построить", callback_data="sector_nucleus_build")],
        [InlineKeyboardButton("❌ Отменить", callback_data="sector_my_base")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Построить ядро Атом за 12000 Медь, 12000 Свинец, 8000 Кремний, 4500 Торий, 500 Кинетический сплав?", reply_markup=reply_markup)

async def sector_nucleus_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    if (inventory.get('Медь', 0) < 12000 or inventory.get('Свинец', 0) < 12000 or 
        inventory.get('Кремний', 0) < 8000 or inventory.get('Торий', 0) < 4500 or 
        inventory.get('Кинетический сплав', 0) < 500):
        await safe_edit_message(query, "❌ Недостаточно ресурсов для улучшения ядра!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="sector_my_base")]]))
        return
    
    inventory['Медь'] -= 12000
    inventory['Свинец'] -= 12000
    inventory['Кремний'] -= 8000
    inventory['Торий'] -= 4500
    inventory['Кинетический сплав'] -= 500
    
    if inventory['Медь'] == 0: del inventory['Медь']
    if inventory['Свинец'] == 0: del inventory['Свинец']
    if inventory['Кремний'] == 0: del inventory['Кремний']
    if inventory['Торий'] == 0: del inventory['Торий']
    if inventory['Кинетический сплав'] == 0: del inventory['Кинетический сплав']
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    sector_data = context.bot_data['sector'][user_id]
    sector_data['core'] = 'Атом'
    sector_data['weapons'] += 10000
    
    await safe_edit_message(query, "✅ Ядро улучшено до Атома! +10000 к вооружению базы!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="sector_my_base")]]))

async def sector_enemy_bases_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "🔴 *Вражеские базы*\n\nСкоро здесь появятся вражеские сектора для атаки!", parse_mode='Markdown', reply_markup=reply_markup)

async def sector_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🟡 Моя база", callback_data="sector_my_base")],
        [InlineKeyboardButton("🔴 Вражеские базы", callback_data="sector_enemy_bases")],
        [InlineKeyboardButton("🛠 Создать турель/юнита", callback_data="sector_build")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "⚔️ *Сектор*\n\nУлучшай защиту своей базы, делай атаки на вражеские сектора чтобы получать ресурсы и разблокировать новые турели/юниты!", parse_mode='Markdown', reply_markup=reply_markup)

async def sector_attack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sector_id = query.data.replace("sector_attack_", "")
    await sector_attack(update, context, sector_id)

async def sector_attack_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sector_id = query.data.replace("sector_attack_confirm_", "")
    await sector_attack_confirm(update, context, sector_id)

async def sector_attack_unit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    sector_id = parts[3]
    unit_name = parts[4]
    await sector_attack_unit(update, context, sector_id, unit_name)

async def sector_attack_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    sector_id = parts[3]
    unit_name = parts[4]
    amount = parts[5]
    await sector_attack_amount(update, context, sector_id, unit_name, amount)

async def sector_enemy_bases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    captured = context.bot_data['sector'].get(user_id, {}).get('captured_sectors', [])
    
    keyboard = []
    
    sectors_list = [("65", "низкая"), ("71", "низкая"), ("113", "низкая"), ("204", "низкая"), ("203", "средняя"), ("165", "средняя"), ("206", "средняя"), ("160", "средняя"), ("245", "высокая")]
    
    for sector_id, threat in sectors_list:
        if sector_id in captured:
            keyboard.append([InlineKeyboardButton(f"🟡 Сектор {sector_id} (ЗАХВАЧЕН)", callback_data=f"attack_{sector_id}")])
        else:
            keyboard.append([InlineKeyboardButton(f"🔴 Сектор {sector_id} (Угроза: {threat})", callback_data=f"attack_{sector_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️  Назад", callback_data="sector_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "🚀 Высадиться на сектор:", reply_markup=reply_markup)

async def sector_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    sector_id = query.data.replace("attack_", "")
    
    sector = SECTORS.get(sector_id)
    if not sector:
        await safe_edit_message(query, "❌ Сектор не найден!")
        return
    
    captured = context.bot_data['sector'].get(user_id, {}).get('captured_sectors', [])
    
    # Если сектор уже захвачен - показываем сообщение как при победе (без награды)
    if sector_id in captured:
        # Получаем сохранённую информацию о юнитах
        sector_data = context.bot_data['sector'].get(user_id, {})
        captured_units = sector_data.get('captured_units', {}).get(sector_id, {})
        unit_name = captured_units.get('unit_name', 'неизвестный юнит')
        amount = captured_units.get('amount', '?')
        
        text = f"🟡   {sector['name']}\n✅ Сектор захвачен\n\n🩸 Уничтоженные юниты: {unit_name} {amount}."
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_enemy_bases")]]
        
        # Добавляем кнопку "Дальше" если есть следующие сектора
        if sector.get('next'):
            keyboard.append([InlineKeyboardButton("➡️ Дальше", callback_data=f"next_{sector_id}")])
        
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Если сектор не захвачен
    text = f"🔴 {sector['name']}\n"
    text += f"💀 Угроза: {sector['threat']}\n"
    text += f"🛡 Вражеские ядра: {sector['core']} {sector['cores_count']}\n"
    text += f"🔫 Вражеская оборона:\n"
    for turret_name, count in sector['turrets'].items():
        text += f"• {turret_name} {count} шт.\n"
    text += "\nВыберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атаковать", callback_data=f"confirm_{sector_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="sector_enemy_bases")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, text, reply_markup=reply_markup)

async def sector_attack_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    sector_id = query.data.replace("confirm_", "")
    
    if 'sector' not in context.bot_data or user_id not in context.bot_data['sector']:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"attack_{sector_id}")]]
        await safe_edit_message(query, "❌ Один в поле не воин. У вас нету юнитов для атаки.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    sector_data = context.bot_data['sector'][user_id]
    units = sector_data.get('units', {})
    
    available_units = [(name, count) for name, count in units.items() if count > 0]
    
    if not available_units:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"attack_{sector_id}")]]
        await safe_edit_message(query, "❌ Один в поле не воин. У вас нету юнитов для атаки.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    keyboard = []
    row = []
    for unit_name, count in available_units:
        button = InlineKeyboardButton(f"{unit_name} ({count})", callback_data=f"unit_{sector_id}_{unit_name}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, "⚔️ Выберите юнита, которым будете атаковать сектор:", reply_markup=reply_markup)

async def sector_attack_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("unit_", "")
    parts = data.split("_")
    sector_id = parts[0]
    unit_name = parts[1]
    
    user_id = update.effective_user.id
    sector_data = context.bot_data['sector'][user_id]
    unit_count = sector_data.get('units', {}).get(unit_name, 0)
    
    keyboard = []
    row = []
    for amount in [1, 2, 4, 8, 16, 24]:
        if amount <= unit_count:
            button = InlineKeyboardButton(f"{amount} ✅", callback_data=f"amount_{sector_id}_{unit_name}_{amount}")
        else:
            button = InlineKeyboardButton(f"{amount} ❌", callback_data=f"error_{sector_id}_{unit_name}_{amount}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Отправить всех✅", callback_data=f"amount_{sector_id}_{unit_name}_all")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, f"Выберите количество\n\nУ вас: {unit_count} {unit_name}", reply_markup=reply_markup)

async def sector_next_bases(update: Update, context: ContextTypes.DEFAULT_TYPE, sector_id):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    sector = SECTORS.get(sector_id)
    if not sector or not sector.get('next'):
        await safe_edit_message(query, "❌ Дальнейших секторов нет!")
        return
    
    captured = context.bot_data['sector'].get(user_id, {}).get('captured_sectors', [])
    
    keyboard = []
    for next_id in sector['next']:
        next_sector = SECTORS.get(next_id)
        if next_sector:
            status = "🟡 " if next_id in captured else "🔴 "
            keyboard.append([InlineKeyboardButton(f"{status} {next_sector['name']} (Угроза: {next_sector['threat']})", callback_data=f"attack_{next_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️  Назад", callback_data=f"attack_{sector_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, f"🚀 Высадиться на сектор (после {sector['name']}):", reply_markup=reply_markup)

async def sector_attack_amount_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("error_", "")
    parts = data.split("_")
    sector_id = parts[0]
    unit_name = parts[1]
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"unit_{sector_id}_{unit_name}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "❌ У вас нету столько юнитов на базе!", reply_markup=reply_markup)

async def sector_attack_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("amount_", "")
    parts = data.split("_")
    sector_id = parts[0]
    unit_name = parts[1]
    amount = parts[2]
    
    user_id = update.effective_user.id
    sector = SECTORS.get(sector_id)
    sector_data = context.bot_data['sector'][user_id]
    units = sector_data.get('units', {})
    unit_count = units.get(unit_name, 0)
    
    if amount == "all":
        amount = unit_count
    else:
        amount = int(amount)
    
    if amount > unit_count:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"unit_{sector_id}_{unit_name}")]]
        await safe_edit_message(query, "❌ У вас нету столько юнитов на базе!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Считаем защиту сектора
    defense = 0
    for turret_name, count in sector['turrets'].items():
        defense += ENEMY_TURRETS.get(turret_name, 0) * count
    
    unit_attack = UNITS.get(unit_name, {}).get('defense', 0)
    total_attack = unit_attack * amount
    
    # Списываем юнитов
    units[unit_name] -= amount
    if units[unit_name] == 0:
        del units[unit_name]
    sector_data['weapons'] = sector_data.get('weapons', 0) - total_attack
    
    if total_attack >= defense:
        # Победа
        if sector_id not in sector_data.get('captured_sectors', []):
            sector_data.setdefault('captured_sectors', []).append(sector_id)
            
            if 'all_inventories' not in context.bot_data:
                context.bot_data['all_inventories'] = {}
            if user_id not in context.bot_data['all_inventories']:
                context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
            inventory = context.bot_data['all_inventories'][user_id]
            
            reward_text = ""
            for resource, amount_reward in sector['rewards'].items():
                inventory[resource] = inventory.get(resource, 0) + amount_reward
                reward_text += f"{resource} {amount_reward}, "
            reward_text = reward_text[:-2]
            
            unlock_text = ""
            if sector.get('unlock'):
                unlock_text = f"\n✨️  Награда: 🔓{sector['unlock']} разблокирован!"
            
            text = f"🟡  {sector['name']}\n✅ Сектор захвачен{unlock_text}\n\n💰 Награда: {reward_text}\n\n🩸  Уничтоженные юниты: {unit_name} {amount}."
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="sector_enemy_bases")]]
            if sector.get('next'):
                keyboard.append([InlineKeyboardButton("➡️ Вперед", callback_data=f"attack_{sector['next']}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query, text, reply_markup=reply_markup)
        else:
            await safe_edit_message(query, f"🟡 {sector['name']}\n✅ Сектор уже захвачен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Назад", callback_data="sector_enemy_bases")]]))
    else:
        # Поражение
        text = f"🔴 {sector['name']}\n💀  АТАКА ПРОВАЛЕНА!\nОборона врага оказалась сильнее, чем мы думали...\n\n🩸 Уничтоженные юниты: {unit_name} {amount}."
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"attack_{sector_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, text, reply_markup=reply_markup)

async def update_drone_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time()
        }
    
    drones_data = context.bot_data['drones'][user_id]
    current_time = time.time()
    last_update = drones_data.get('last_update', current_time)
    elapsed_seconds = current_time - last_update
    
    if elapsed_seconds > 0 and elapsed_seconds <= 86400:
        if 'all_inventories' in context.bot_data and user_id in context.bot_data['all_inventories']:
            inventory = context.bot_data['all_inventories'][user_id]
            for drone_name, drone_info in DRONES.items():
                resources_key = drone_info['resources_key']
                resources = drones_data.get(resources_key, {})
                production = drone_info['production']
                for resource, count in resources.items():
                    if count > 0:
                        amount = int((production * count / 3600) * elapsed_seconds)
                        amount = min(amount, 1000000)
                        if amount > 0:
                            inventory[resource] = inventory.get(resource, 0) + amount
    
    drones_data['last_update'] = current_time

async def drones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_drone_resources(update, context)
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    coins = inventory.get('coins', 0)
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time()
        }
    
    drones_data = context.bot_data['drones'][user_id]
    
    keyboard = []
    for drone_name, drone_info in DRONES.items():
        research_key = drone_info['research_key']
        if not drones_data.get(research_key, False):
            keyboard.append([InlineKeyboardButton(f"🔍 Исследовать дрон {drone_name} ({drone_info['research_cost']}🪙 )", callback_data=f"drone_research_{drone_name}")])
        else:
            keyboard.append([InlineKeyboardButton(f"🛒 Купить {drone_name} ({drone_info['buy_cost']}🪙 )", callback_data=f"drone_buy_{drone_name}")])
    keyboard.append([InlineKeyboardButton("📊 Статистика дронов", callback_data="drone_stats")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    
    text = f"🕹 *Дронстанция*\n\nИсследуйте и используйте дроны чтобы добывать недостающие ресурсы!\n\nПроизводительность дронов:\n🕹Моно - 1Рес/Ч\n🕹Поли - 9Рес/Ч\n🕹Мега - 65Рес/Ч\n🕹Квад - 380Рес/Ч\n🕹Окт - 8500Рес/Ч\n\n🪙 Монеты: {coins}."
    
    if update.callback_query:
        await safe_edit_message(update.callback_query, text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def drone_research(update: Update, context: ContextTypes.DEFAULT_TYPE, drone_name):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    coins = inventory.get('coins', 0)
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time()
        }
    
    drones_data = context.bot_data['drones'][user_id]
    drone_info = DRONES[drone_name]
    research_key = drone_info['research_key']
    research_cost = drone_info['research_cost']
    
    if not drones_data.get(research_key, False):
        if coins < research_cost:
            await safe_edit_message(query, f"❌ Недостаточно монет для исследования дрона {drone_name}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drone_back")]]))
            return
        inventory['coins'] -= research_cost
        drones_data[research_key] = True
        await drones_command(update, context)

async def drone_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, drone_name):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    coins = inventory.get('coins', 0)
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time(), 'pending_drone': None
        }
    
    drones_data = context.bot_data['drones'][user_id]
    drone_info = DRONES[drone_name]
    research_key = drone_info['research_key']
    buy_cost = drone_info['buy_cost']
    
    if not drones_data.get(research_key, False):
        await safe_edit_message(query, f"❌ Сначала исследуйте дрона {drone_name}!")
        return
    if coins < buy_cost:
        await safe_edit_message(query, f"❌ Недостаточно монет для покупки дрона {drone_name}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="drone_back")]]))
        return
    
    drones_data['pending_drone'] = drone_name
    drones_data['pending_cost'] = buy_cost
    
    keyboard = [
        [InlineKeyboardButton("Медь", callback_data=f"drone_resource_{drone_name}_Медь")],
        [InlineKeyboardButton("Свинец", callback_data=f"drone_resource_{drone_name}_Свинец")],
        [InlineKeyboardButton("Уголь", callback_data=f"drone_resource_{drone_name}_Уголь")],
        [InlineKeyboardButton("Песок", callback_data=f"drone_resource_{drone_name}_Песок")],
        [InlineKeyboardButton("Титан", callback_data=f"drone_resource_{drone_name}_Титан")],
        [InlineKeyboardButton("Торий", callback_data=f"drone_resource_{drone_name}_Торий")],
        [InlineKeyboardButton("❌ Отменить", callback_data="drone_buy_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, f"Выберите ресурс, который будет добывать дрон {drone_name}\n\nВыбирайте с умом, позже это нельзя будет изменить!", reply_markup=reply_markup)

async def drone_buy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time(), 'pending_drone': None
        }
    
    drones_data = context.bot_data['drones'][user_id]
    drones_data['pending_drone'] = None
    await drones_command(update, context)

async def drone_set_resource(update: Update, context: ContextTypes.DEFAULT_TYPE, drone_name, resource):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time(), 'pending_drone': None
        }
    
    drones_data = context.bot_data['drones'][user_id]
    if drones_data.get('pending_drone') != drone_name:
        await drones_command(update, context)
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    pending_cost = drones_data.get('pending_cost', 0)
    inventory['coins'] -= pending_cost
    
    drone_info = DRONES[drone_name]
    resources_key = drone_info['resources_key']
    count_key = drone_info['count_key']
    resources = drones_data.get(resources_key, {})
    resources[resource] = resources.get(resource, 0) + 1
    drones_data[resources_key] = resources
    drones_data[count_key] = drones_data.get(count_key, 0) + 1
    drones_data['pending_drone'] = None
    drones_data['pending_cost'] = None
    
    await drones_command(update, context)

async def drone_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    await update_drone_resources(update, context)
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time()
        }
    
    drones_data = context.bot_data['drones'][user_id]
    stats_text = f"🕹 *Дроны игрока {user_name}:*\n\n"
    resource_production = {"Медь": 0, "Свинец": 0, "Уголь": 0, "Песок": 0, "Титан": 0, "Торий": 0}
    
    for drone_name, drone_info in DRONES.items():
        count_key = drone_info['count_key']
        resources_key = drone_info['resources_key']
        resources = drones_data.get(resources_key, {})
        total_count = drones_data.get(count_key, 0)
        production = drone_info['production']
        stats_text += f"{drone_name} - {total_count}\n"
        for resource, count in resources.items():
            resource_production[resource] += production * count
    
    stats_text += f"\n⛏️ *Добывающиеся дронами ресурсы:*\n"
    stats_text += f"Медь: {resource_production['Медь']}/ч\n"
    stats_text += f"Свинец: {resource_production['Свинец']}/ч\n"
    stats_text += f"Уголь: {resource_production['Уголь']}/ч\n"
    stats_text += f"Песок: {resource_production['Песок']}/ч\n"
    stats_text += f"Титан: {resource_production['Титан']}/ч\n"
    stats_text += f"Торий: {resource_production['Торий']}/ч\n\n"
    stats_text += f"Ресурсы автоматически перемещаются в твой инвентарь!"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="drone_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, stats_text, parse_mode='Markdown', reply_markup=reply_markup)

async def drone_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'drones' not in context.bot_data:
        context.bot_data['drones'] = {}
    if user_id not in context.bot_data['drones']:
        context.bot_data['drones'][user_id] = {
            'mono_researched': False, 'poly_researched': False, 'mega_researched': False, 'quad_researched': False, 'oct_researched': False,
            'mono_count': 0, 'poly_count': 0, 'mega_count': 0, 'quad_count': 0, 'oct_count': 0,
            'mono_resources': {}, 'poly_resources': {}, 'mega_resources': {}, 'quad_resources': {}, 'oct_resources': {},
            'last_update': time.time(), 'pending_drone': None
        }
    
    drones_data = context.bot_data['drones'][user_id]
    drones_data['pending_drone'] = None
    await drones_command(update, context)

# ========== ШАХТА ==========

async def mineshaft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'mines' not in context.bot_data:
        context.bot_data['mines'] = {}
    if user_id not in context.bot_data['mines']:
        context.bot_data['mines'][user_id] = {'drills': {}, 'stored': {}, 'last_update': time.time()}
    
    keyboard = [
        [InlineKeyboardButton("🛠 Построить бур", callback_data="mine_build_menu")],
        [InlineKeyboardButton("🏔 Моя шахта", callback_data="mine_info")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏔 *Шахта*\n\nЗарабатывай пассивные ресурсы во время АФК при помощи буров!\n\nСтоимость строительства буров:\n⚙️Медный бур (25 Медь) 5Рес/Ч\n⚙️Пневматический бур (35 Медь, 10 Графит) 20Рес/Ч\n⚙️Лазерный бур (120 Медь, 40 Кремний, 20 Титан) 120Рес/ч\n⚙️Воздушная бур. установка (250 Медь, 250 Свинец, 120 Кремний, 100 Титан, 50 Торий) 600 Рес/Ч\n🏗Epiroc Pit Viper 351 (800 Медь, 400 Кремний, 250 Титан, 100 Фазовая ткань) 2000Рес/Ч\n🏗Sandvik Pantera DP1600i (2000 Свинец, 1500 Кремний, 1500 Титан, 400 Фазовая ткань, 400 Кинетический сплав) 9560Рес/Ч",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def mine_build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    keyboard = []
    for drill_name, drill_info in DRILLS.items():
        can_build = True
        for resource, cost in drill_info["cost"].items():
            if inventory.get(resource, 0) < cost:
                can_build = False
                break
        status = "✅" if can_build else "❌"
        keyboard.append([InlineKeyboardButton(f"{drill_info['emoji']} {drill_name} {status}", callback_data=f"mine_build_{drill_name}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="mine_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "Выбери бур, который хочешь построить:", reply_markup=reply_markup)

async def mine_build_drill(update: Update, context: ContextTypes.DEFAULT_TYPE, drill_name):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if drill_name not in DRILLS:
        return
    drill_info = DRILLS[drill_name]
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    inventory = context.bot_data['all_inventories'][user_id]
    
    missing_resources = []
    for resource, cost in drill_info["cost"].items():
        if inventory.get(resource, 0) < cost:
            missing_resources.append(f"{resource} ({inventory.get(resource, 0)}/{cost})")
    
    if missing_resources:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="mine_build_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_message(query, f"❌ Недостаточно ресурсов для постройки бура!\n\nНе хватает:\n" + "\n".join(missing_resources), reply_markup=reply_markup)
        return
    
    for resource, cost in drill_info["cost"].items():
        inventory[resource] -= cost
        if inventory[resource] == 0:
            del inventory[resource]
    
    if 'mines' not in context.bot_data:
        context.bot_data['mines'] = {}
    if user_id not in context.bot_data['mines']:
        context.bot_data['mines'][user_id] = {'drills': {}, 'stored': {}, 'last_update': time.time()}
    
    if 'last_update' not in context.bot_data['mines'][user_id]:
        context.bot_data['mines'][user_id]['last_update'] = time.time()
    
    if drill_name not in context.bot_data['mines'][user_id]['drills']:
        context.bot_data['mines'][user_id]['drills'][drill_name] = 0
    
    context.bot_data['mines'][user_id]['drills'][drill_name] += 1
    await mine_build_menu(update, context)

async def mine_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if 'mines' not in context.bot_data:
        context.bot_data['mines'] = {}
    if user_id not in context.bot_data['mines']:
        context.bot_data['mines'][user_id] = {'drills': {}, 'stored': {}, 'last_update': time.time()}
    
    mine_data = context.bot_data['mines'][user_id]
    drills = mine_data.get('drills', {})
    current_time = time.time()
    last_update = mine_data.get('last_update', current_time)
    elapsed_seconds = current_time - last_update
    
    if elapsed_seconds > 0 and elapsed_seconds <= 86400:
        total_production_per_hour = 0
        for drill_name, count in drills.items():
            if drill_name in DRILLS:
                total_production_per_hour += DRILLS[drill_name]["production"] * count
        
        if total_production_per_hour > 0:
            total_production_per_second = total_production_per_hour / 3600
            total_resources = int(total_production_per_second * elapsed_seconds)
            total_resources = min(total_resources, 1000000000)
            if total_resources > 0:
                if 'stored' not in mine_data:
                    mine_data['stored'] = {}
                for _ in range(total_resources):
                    resource = get_mine_resource()
                    mine_data['stored'][resource] = mine_data['stored'].get(resource, 0) + 1
    
    mine_data['last_update'] = current_time
    
    total_production = 0
    for drill_name, count in drills.items():
        if drill_name in DRILLS:
            total_production += DRILLS[drill_name]["production"] * count
    stored = mine_data.get('stored', {})
    
    # Проверяем вооружение в секторе
    sector_weapons = 0
    if 'sector' in context.bot_data and user_id in context.bot_data['sector']:
        sector_weapons = context.bot_data['sector'][user_id].get('weapons', 0)
    
    # Если вооружение в минусе, уменьшаем доход в 2 раза
    if sector_weapons < 0:
        total_production = total_production // 2
        production_text = f"📈 *Доход ресурсов:* {total_production}/Ч (-50%)❗️\n💥 Ваше вооружение зашло в минус, доход от шахты уменьшен в 2 раза. загляните в /sector"
    else:
        production_text = f"📈 *Доход ресурсов:* {total_production}/Ч"
    
    info_text = f"🏔 *Буры игрока {user_name}:*\n\n"
    if not drills:
        info_text += "Нет построенных буров!\n"
    else:
        for drill_name, count in drills.items():
            info_text += f"{DRILLS[drill_name]['emoji']} {drill_name}: {count} шт.\n"
    info_text += f"\n{production_text}\n\n📦 *Накоплено ресурсов:*\n"
    for resource in ["Медь", "Свинец", "Уголь", "Песок", "Титан", "Торий"]:
        amount = stored.get(resource, 0)
        info_text += f"{resource}: {amount} шт.\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 Собрать ресурсы", callback_data="mine_collect")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="mine_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, info_text, parse_mode='Markdown', reply_markup=reply_markup)

async def mine_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if 'mines' not in context.bot_data:
        context.bot_data['mines'] = {}
    if user_id not in context.bot_data['mines']:
        context.bot_data['mines'][user_id] = {'drills': {}, 'stored': {}, 'last_update': time.time()}
    
    mine_data = context.bot_data['mines'][user_id]
    stored = mine_data.get('stored', {})
    
    if not stored:
        await mine_info(update, context)
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    for resource, amount in stored.items():
        inventory[resource] = inventory.get(resource, 0) + amount
    mine_data['stored'] = {}
    await mine_info(update, context)

async def mine_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🛠 Построить бур", callback_data="mine_build_menu")],
        [InlineKeyboardButton("🏔 Моя шахта", callback_data="mine_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, "🏔 *Шахта*\n\nЗарабатывай пассивные ресурсы во время АФК при помощи буров!\n\nСтоимость строительства буров:\n⚙️Медный бур (25 Медь) 5Рес/Ч\n⚙️Пневматический бур (35 Медь, 10 Графит) 20Рес/Ч\n⚙️Лазерный бур (120 Медь, 40 Кремний, 20 Титан) 120Рес/ч\n⚙️Воздушная бур. установка (250 Медь, 250 Свинец, 120 Кремний, 100 Титан, 50 Торий) 600 Рес/Ч\n🏗Epiroc Pit Viper 351 (800 Медь, 400 Кремний, 250 Титан, 100 Фазовая ткань) 2000Рес/Ч\n🏗Sandvik Pantera DP1600i (2000 Свинец, 1500 Кремний, 1500 Титан, 400 Фазовая ткань, 400 Кинетический сплав) 9560Рес/Ч", parse_mode='Markdown', reply_markup=reply_markup)

# ========== КОПАНИЕ ==========

async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'upgrades' not in context.bot_data:
        context.bot_data['upgrades'] = {}
    if user_id not in context.bot_data['upgrades']:
        context.bot_data['upgrades'][user_id] = {
            'mining_multiplier': 1.0,
            'cooldown_reduction': 0,
            'mining_level': 0,
            'cooldown_level': 0
        }
    
    upgrades = context.bot_data['upgrades'][user_id]
    current_cooldown = max(MIN_COOLDOWN, BASE_COOLDOWN - upgrades['cooldown_reduction'] * 15)
    
    if 'cooldowns' not in context.bot_data:
        context.bot_data['cooldowns'] = {}
    
    current_time = time.time()
    last_use = context.bot_data['cooldowns'].get(user_id, 0)
    time_passed = current_time - last_use
    
    if time_passed < current_cooldown:
        remaining = int(current_cooldown - time_passed)
        
        if remaining >= 3600:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            time_text = f"{hours} ч {minutes} мин {seconds} сек"
        elif remaining >= 60:
            minutes = remaining // 60
            seconds = remaining % 60
            time_text = f"{minutes} мин {seconds} сек"
        else:
            time_text = f"{remaining} сек"
        
        await update.message.reply_text(
            f"❌ Ты уже недавно копал ресурсы!\n\n"
            f"Возвращайся через {time_text}."
        )
        return
    
    context.bot_data['cooldowns'][user_id] = current_time

    # Увеличиваем счетчик копаний (только если успешно скопал)
    if 'mine_count' not in context.bot_data:
        context.bot_data['mine_count'] = {}
    if user_id not in context.bot_data['mine_count']:
        context.bot_data['mine_count'][user_id] = 0
    context.bot_data['mine_count'][user_id] += 1
    
    resource = get_random_resource()
    amount = get_resource_amount(resource, upgrades)
    
    if resource == "Кинетический сплав":
        result_text = f"💥  *НЕВЕРОЯТНАЯ УДАЧА!*\n\nТы обнаружил заброшенную шахту и нашел контейнер с {amount} шт. Кинетическим сплавом! Мои поздравления!"
        
        if 'all_inventories' not in context.bot_data:
            context.bot_data['all_inventories'] = {}
        if user_id not in context.bot_data['all_inventories']:
            context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
        if resource not in context.bot_data['all_inventories'][user_id]:
            context.bot_data['all_inventories'][user_id][resource] = 0
        context.bot_data['all_inventories'][user_id][resource] += amount
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        return
    
    mining_messages = [
        "⛏️  Вы ударили киркой по земле и добыли",
        "⛏️  Вы поставили бур и добыли",
        "⛏️  Исследуя местность, вы обнаружили и добыли"
    ]
    
    selected_message = random.choice(mining_messages)
    
    if resource in ITEM_RESOURCES:
        unit = "шт"
    else:
        unit = "мл"
    
    result_text = f"{selected_message} {resource} {amount} {unit}!"
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    if resource not in context.bot_data['all_inventories'][user_id]:
        context.bot_data['all_inventories'][user_id][resource] = 0
    context.bot_data['all_inventories'][user_id][resource] += amount
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    
    coins = inventory.get('coins', 0)
    artifacts = inventory.get('artifacts', 0)
    
    inventory_text = f"📦 Инвентарь игрока {user_name}:\n\n"
    inventory_text += f"🔮 Артефакты: {artifacts} шт.\n"
    inventory_text += f"🪙 Монеты: {coins} шт.\n\n"
    
    other_items = {k: v for k, v in inventory.items() if k not in ['coins', 'artifacts']}
    
    if not other_items:
        inventory_text += "Других ресурсов нет!"
    else:
        for resource, amount in other_items.items():
            if resource in LIQUID_DISPLAY:
                inventory_text += f"• {resource}: {amount} мл\n"
            else:
                inventory_text += f"• {resource}: {amount} шт.\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== УЛУЧШЕНИЯ ==========

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    artifacts = inventory.get('artifacts', 0)
    
    if 'upgrades' not in context.bot_data:
        context.bot_data['upgrades'] = {}
    if user_id not in context.bot_data['upgrades']:
        context.bot_data['upgrades'][user_id] = {
            'mining_multiplier': 1.0,
            'cooldown_reduction': 0,
            'mining_level': 0,
            'cooldown_level': 0
        }
    
    upgrades = context.bot_data['upgrades'][user_id]
    mining_cost = get_upgrade_cost(upgrades['mining_level'])
    cooldown_cost = get_upgrade_cost(upgrades['cooldown_level'])
    
    keyboard = [
        [InlineKeyboardButton(f"🔝 Производство x1.5 ({mining_cost}🔮)", callback_data=f"upgrade_mining_{mining_cost}")],
        [InlineKeyboardButton(f"⏱️ Кулдаун -15с ({cooldown_cost}🔮)", callback_data=f"upgrade_cooldown_{cooldown_cost}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🔝 *Улучшение добычи*\n\n• Используй 🔮 Артефакты чтобы увеличивать доход копания в х1.5 раза каждый раз\n• Используй 🔮 Артефакты чтобы сокращать кулдаун копания на 15 секунд каждый раз\n\nВаши артефакты: {artifacts}"
    
    if update.callback_query:
        await safe_edit_message(update.callback_query, text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "upgrade_back":
        await upgrade_command(update, context)
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    artifacts = inventory.get('artifacts', 0)
    
    if 'upgrades' not in context.bot_data:
        context.bot_data['upgrades'] = {}
    if user_id not in context.bot_data['upgrades']:
        context.bot_data['upgrades'][user_id] = {
            'mining_multiplier': 1.0,
            'cooldown_reduction': 0,
            'mining_level': 0,
            'cooldown_level': 0
        }
    
    upgrades = context.bot_data['upgrades'][user_id]
    
    if data.startswith("upgrade_mining_"):
        cost = int(data.split("_")[2])
        
        if artifacts < cost:
            await safe_edit_message(query, f"❌ Недостаточно артефактов! Нужно {cost}🔮, у вас {artifacts}🔮\n\nВаши артефакты: {artifacts}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="upgrade_back")]]))
            return
        
        inventory['artifacts'] -= cost
        upgrades['mining_level'] += 1
        upgrades['mining_multiplier'] *= 1.5
        
        await safe_edit_message(query, f"✅ Улучшение куплено за {cost}🔮 Артефактов!\n\n🔝 Производство увеличено в 1.5 раза!\nТекущий множитель: x{upgrades['mining_multiplier']:.1f}\n\nВаши артефакты: {inventory['artifacts']}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="upgrade_back")]]))
        
    elif data.startswith("upgrade_cooldown_"):
        cost = int(data.split("_")[2])
        current_cooldown = max(MIN_COOLDOWN, BASE_COOLDOWN - upgrades['cooldown_reduction'] * 15)
        
        if current_cooldown <= MIN_COOLDOWN:
            await safe_edit_message(query, f"❌ Кулдаун уже достиг минимального значения {MIN_COOLDOWN} секунд!\n\nВаши артефакты: {artifacts}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="upgrade_back")]]))
            return
        
        if artifacts < cost:
            await safe_edit_message(query, f"❌ Недостаточно артефактов! Нужно {cost}🔮, у вас {artifacts}🔮\n\nВаши артефакты: {artifacts}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="upgrade_back")]]))
            return
        
        inventory['artifacts'] -= cost
        upgrades['cooldown_level'] += 1
        upgrades['cooldown_reduction'] += 1
        
        new_cooldown = max(MIN_COOLDOWN, BASE_COOLDOWN - upgrades['cooldown_reduction'] * 15)
        
        await safe_edit_message(query, f"✅ Улучшение куплено за {cost}🔮 Артефактов!\n\n⏱️ Кулдаун уменьшен на 15 секунд!\nТекущий кулдаун: {new_cooldown} сек\n\nВаши артефакты: {inventory['artifacts']}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="upgrade_back")]]))

# ========== ЕЖЕДНЕВНЫЙ ПОДАРОК ==========

async def daygift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'last_gift' not in context.bot_data:
        context.bot_data['last_gift'] = {}
    
    last_time = context.bot_data['last_gift'].get(user_id, 0)
    current_time = time.time()
    
    if current_time - last_time < 86400:
        remaining = int(86400 - (current_time - last_time))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        await update.message.reply_text(f"❌ Ты уже получал ежедневный подарок!\n\nСледующий подарок будет доступен через {hours} ч {minutes} мин {seconds} сек.")
        return
    
    context.bot_data['last_gift'][user_id] = current_time
    
    coins = get_random_value(COIN_CHANCES)
    artifacts = get_random_value(ARTIFACT_CHANCES)
    unique_items = get_unique_items()
    turret, turret_amount = get_turret_gift()
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    inventory['coins'] = inventory.get('coins', 0) + coins
    inventory['artifacts'] = inventory.get('artifacts', 0) + artifacts
    
    if turret:
        if 'sector' not in context.bot_data:
            context.bot_data['sector'] = {}
        if user_id not in context.bot_data['sector']:
            context.bot_data['sector'][user_id] = {
                'core': 'Осколок',
                'weapons': 0,
                'turrets': {},
                'units': {},
                'wave': 1,
                'last_attack_time': time.time(),
                'last_wave_damage': 0,
                'last_wave_composition': None,
                'captured_sectors': []
            }
        
        sector_data = context.bot_data['sector'][user_id]
        sector_data['turrets'][turret] = sector_data['turrets'].get(turret, 0) + turret_amount
        defense = TURRETS[turret]['defense']
        sector_data['weapons'] += defense * turret_amount
    
    gift_text = f"🎁 *Ежедневный подарок открыт!*\n\nВы получили:\n🪙 Монеты: {coins}\n🔮 Артефакты: {artifacts}"
    
    if turret:
        gift_text += f"\n🔫 {turret} {turret_amount} шт."

    if unique_items:
        gift_text += "\n\n⚙️  *Уникальные предметы:*"
        for item in unique_items:
            item_data = UNIQUE_ITEMS_LIST.get(item, {"emoji": "⚙️ ", "rarity": "Обычный"})
            gift_text += f"\n{item_data['emoji']} {item} - {item_data['rarity']}"
    
        if 'unique_items' not in context.bot_data:
            context.bot_data['unique_items'] = {}
        if user_id not in context.bot_data['unique_items']:
            context.bot_data['unique_items'][user_id] = []
    
        for item in unique_items:
            if item not in context.bot_data['unique_items'][user_id]:
                context.bot_data['unique_items'][user_id].append(item)
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== ОБМЕНЫ И КРАФТ ==========

CRAFT_RECIPES = {
    "graphite": {"name": "Графит", "type": "item", "amount_per_craft": 1, "resources": {"Уголь": 2}},
    "metaglass": {"name": "Метастекло", "type": "item", "amount_per_craft": 1, "resources": {"Песок": 1, "Свинец": 1}},
    "silicon": {"name": "Кремний", "type": "item", "amount_per_craft": 1, "resources": {"Песок": 2, "Уголь": 1}},
    "sporepod": {"name": "Споровый стручок", "type": "item", "amount_per_craft": 1, "resources": {"Вода": 200}},
    "plastanium": {"name": "Пластан", "type": "item", "amount_per_craft": 1, "resources": {"Титан": 2, "Нефть": 100}},
    "surgealloy": {"name": "Кинетический сплав", "type": "item", "amount_per_craft": 1, "resources": {"Медь": 3, "Свинец": 4, "Титан": 2, "Кремний": 3}},
    "phasefabric": {"name": "Фазовая ткань", "type": "item", "amount_per_craft": 1, "resources": {"Торий": 4, "Песок": 10}},
    "pyratite": {"name": "Пиротит", "type": "item", "amount_per_craft": 1, "resources": {"Свинец": 2, "Песок": 2, "Уголь": 1}},
    "blastcompound": {"name": "Взрывчатая смесь", "type": "item", "amount_per_craft": 1, "resources": {"Пиротит": 1, "Споровый стручок": 1}},
    "oil": {"name": "Нефть", "type": "liquid", "amount_per_craft": 100, "resources": {"Вода": 500, "Песок": 2}},
    "cryofluid": {"name": "Криогенная жидкость", "type": "liquid", "amount_per_craft": 100, "resources": {"Вода": 100, "Титан": 1}}
}

ARTIFACT_EXCHANGE = {
    "Графит": 100, "Метастекло": 50, "Кремний": 20, "Споровый стручок": 100,
    "Пластан": 5, "Кинетический сплав": 1, "Фазовая ткань": 2, "Пиротит": 20, "Взрывчатая смесь": 5
}

COIN_EXCHANGE = {
    "Медь": 1, "Свинец": 1, "Песок": 1, "Уголь": 1, "Вода": 0.01, "Нефть": 0.05,
    "Криогенная жидкость": 0.1, "Титан": 2, "Торий": 5, "Графит": 4, "Метастекло": 4,
    "Кремний": 5, "Споровый стручок": 5, "Пластан": 25, "Кинетический сплав": 50,
    "Фазовая ткань": 100, "Пиротит": 10, "Взрывчатая смесь": 30
}

async def buy_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE, amount_str):
    user_id = update.effective_user.id
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    
    if amount_str == "all":
        amount = inventory.get('coins', 0) // 1000
        if amount == 0:
            await update.message.reply_text("❌ Недостаточно монет!")
            return
    else:
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Выбери нужное количество артефактов\nПример: /buyartifact 1")
            return
    
    total_cost = amount * 1000
    if inventory.get('coins', 0) < total_cost:
        await update.message.reply_text("❌ Недостаточно монет!")
        return
    
    inventory['coins'] -= total_cost
    inventory['artifacts'] = inventory.get('artifacts', 0) + amount
    await update.message.reply_text(f"✅ Вы купили 🔮 Артефакты в количестве {amount} шт!")

async def exchange_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE, resource_name, amount_str):
    user_id = update.effective_user.id
    
    if resource_name not in ARTIFACT_EXCHANGE:
        await update.message.reply_text("Этот ресурс нельзя обменять на артефакты!")
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    required_per_artifact = ARTIFACT_EXCHANGE[resource_name]
    
    if resource_name not in inventory:
        await update.message.reply_text("❌ Недостаточно ресурсов!")
        return
    
    if amount_str == "all":
        amount = inventory[resource_name] // required_per_artifact
        if amount == 0:
            await update.message.reply_text("❌ Недостаточно ресурсов!")
            return
    else:
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"Выбери нужное количество для обмена\nПример: /exchange{resource_name}artifact 1")
            return
    
    required_total = required_per_artifact * amount
    if inventory[resource_name] < required_total:
        await update.message.reply_text("❌ Недостаточно ресурсов!")
        return
    
    inventory[resource_name] -= required_total
    if inventory[resource_name] == 0:
        del inventory[resource_name]
    
    inventory['artifacts'] = inventory.get('artifacts', 0) + amount
    await update.message.reply_text(f"✅ Вы обменяли {required_total} {resource_name} на {amount} 🔮 Артефактов!")

async def exchange_coins(update: Update, context: ContextTypes.DEFAULT_TYPE, resource_name, amount_str):
    user_id = update.effective_user.id
    
    if resource_name not in COIN_EXCHANGE:
        await update.message.reply_text("Этот ресурс нельзя обменять на монеты!")
        return
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    coin_value = COIN_EXCHANGE[resource_name]
    
    if resource_name not in inventory:
        await update.message.reply_text("❌ Недостаточно ресурсов!")
        return
    
    if amount_str == "all":
        amount = inventory[resource_name]
        if resource_name in LIQUID_DISPLAY and resource_name not in ITEM_RESOURCES:
            amount = int(amount)
        if amount == 0:
            await update.message.reply_text("❌ Недостаточно ресурсов!")
            return
    else:
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"Выбери нужное количество для обмена\nПример: /exchange{resource_name} 5")
            return
    
    if inventory[resource_name] < amount:
        await update.message.reply_text("❌ Недостаточно ресурсов!")
        return
    
    if coin_value < 1:
        coins_earned = int(amount * coin_value)
    else:
        coins_earned = amount * coin_value
    
    inventory[resource_name] -= amount
    if inventory[resource_name] == 0:
        del inventory[resource_name]
    
    inventory['coins'] = inventory.get('coins', 0) + coins_earned
    await update.message.reply_text(f"✅ Вы обменяли {amount} {resource_name} на {coins_earned} 🪙 Монет!")

async def craft_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_key, amount_str):
    user_id = update.effective_user.id
    
    if item_key not in CRAFT_RECIPES:
        await update.message.reply_text("Неизвестный предмет для крафта!")
        return
    
    recipe = CRAFT_RECIPES[item_key]
    item_name = recipe["name"]
    item_type = recipe["type"]
    amount_per_craft = recipe["amount_per_craft"]
    required_resources = recipe["resources"]
    
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 0, 'artifacts': 0}
    
    inventory = context.bot_data['all_inventories'][user_id]
    
    if amount_str == "all":
        max_amount = float('inf')
        for resource, amount_needed in required_resources.items():
            if resource in inventory:
                available = inventory[resource]
                possible = available // amount_needed
                max_amount = min(max_amount, possible)
            else:
                max_amount = 0
                break
        
        if max_amount == 0:
            await update.message.reply_text("❌ Недостаточно ресурсов!")
            return
        amount = max_amount
    else:
        try:
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"Выбери нужное количество ресурсов\nПример: /craft{item_key} 10")
            return
    
    for resource, amount_needed in required_resources.items():
        required_total = amount_needed * amount
        if inventory.get(resource, 0) < required_total:
            await update.message.reply_text("❌ Недостаточно ресурсов!")
            return
    
    for resource, amount_needed in required_resources.items():
        required_total = amount_needed * amount
        inventory[resource] -= required_total
        if inventory[resource] == 0:
            del inventory[resource]
    
    crafted_amount = amount * amount_per_craft
    inventory[item_name] = inventory.get(item_name, 0) + crafted_amount
    
    unit = "мл" if item_type == "liquid" else "шт"
    await update.message.reply_text(f"✅ Вы скрафтили {item_name} в количестве {crafted_amount} {unit}!")

async def handle_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это текстовое сообщение и бот добавлен в чат
    if not update.message or not update.message.text:
        return
    
    # Отправляем приветственное сообщение с клавиатурой
    await update.message.reply_text(
        "🤖  Игровой бот Mindustry запущен!\n"
        "Используйте команды или кнопки ниже для игры.\n\n"
        "⚠️  Для работы бота в группе, напишите /start в личные сообщения бота, чтобы создать профиль."
    )

async def start_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start в группах"""
    await update.message.reply_text(
        "🤖  Игровой бот Mindustry!\n\n"
        "Для игры используйте кнопки ниже.\n"
        "⚠️  Для создания профиля напишите /start в ЛИЧНЫЕ сообщения боту."
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Собираем всех игроков и их вооружение
    players = []
    
    if 'sector' in context.bot_data:
        for uid, data in context.bot_data['sector'].items():
            weapons = data.get('weapons', 0)
            # Получаем имя игрока (пытаемся из чата, если нет - из данных)
            name = "Игрок"
            try:
                user = await context.bot.get_chat(uid)
                name = user.first_name if user.first_name else f"Игрок_{uid}"
            except:
                name = f"Игрок_{uid}"
            players.append((uid, name, weapons))
    
    # Сортируем по вооружению (по убыванию)
    players.sort(key=lambda x: x[2], reverse=True)
    
    # Берем топ-30
    top_players = players[:30]
    
    # Функция определения уровня
    def get_rank(weapons):
        if weapons < 1000:
            return "◽️  Начинающий (Lv. 1)"
        elif weapons < 2500:
            return "◻️  Осваивающийся (Lv. 2)"
        elif weapons < 10000:
            return "◾️  Любитель (Lv. 3)"
        elif weapons < 50000:
            return "◼️  Продвинутый (Lv. 4)"
        elif weapons < 150000:
            return "🔶 ️ Эксперт (Lv. 5)"
        elif weapons < 2000000:
            return "🔷 ️ Мастер (Lv. 6)"
        elif weapons < 30000000:
            return "🔺 ️ Легенда (Lv. 7)"
        else:
            return "💠  Бог (Lv. 8)"
    
    # Формируем текст
    if not top_players:
        await update.message.reply_text("🏆 Пока нет игроков в лидерборде!")
        return
    
    text = "🎖 **ТОП ЛУЧШИХ ИГРОКОВ ЗА ВСЕ ВРЕМЯ** 🎖\n\n"
    
    medals = ["🥇 ", "🥈 ", "🥉 "]
    for i, (uid, name, weapons) in enumerate(top_players, 1):
        if i <= 3:
            medal = medals[i-1]
            text += f"#{i}{medal} **{name}**\n"
        else:
            text += f"#{i} **{name}**\n"
        text += f"💥  Вооружение: {weapons}\n"
        text += f"{get_rank(weapons)}\n\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def mindustrymining_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Поддержка как для обычных команд, так и для callback (кнопка "Назад")
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_message = query.edit_message_text
    else:
        send_message = update.message.reply_text
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Создаем профиль если нет
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 100, 'artifacts': 0}
    
    text = f"Главное Меню ⛏️ \n\n👋  Привет, {user_name}! Выбери раздел:"
    
    keyboard = [
        [InlineKeyboardButton("⛏️  Копать", callback_data="menu_mine"), InlineKeyboardButton("📦 Инвентарь", callback_data="menu_inventory")],
        [InlineKeyboardButton("🔝  Улучшения", callback_data="menu_upgrade")],
        [InlineKeyboardButton("🛠 Крафтинг", callback_data="menu_craft"), InlineKeyboardButton("🔮  Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton("🏔 Шахта", callback_data="menu_mineshaft")],
        [InlineKeyboardButton("🕹 Дроны", callback_data="menu_drones"), InlineKeyboardButton("🎁  Ежед. Подарок", callback_data="menu_daygift")],
        [InlineKeyboardButton("⚔️  Сектор", callback_data="menu_sector")],
        [InlineKeyboardButton("📜  Чертежи", callback_data="menu_drawings"), InlineKeyboardButton("👤  Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🏆 Лидерборд", callback_data="menu_top")],
        [InlineKeyboardButton("❓️  Как играть?", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_message(text, reply_markup=reply_markup)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("menu_", "")
    
    # Обработка возврата в главное меню
    if action == "back":
        await mindustrymining_command(update, context)
        return
    
    # Создаем временные объекты для вызова команд
    class FakeMessage:
        def __init__(self, chat_id, bot):
            self.chat_id = chat_id
            self.bot = bot
        
        async def reply_text(self, text, parse_mode=None, reply_markup=None):
            await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    class FakeUpdate:
        def __init__(self, message, effective_user, effective_chat):
            self.message = message
            self.effective_user = effective_user
            self.effective_chat = effective_chat
            self.callback_query = None
    
    fake_message = FakeMessage(update.effective_chat.id, context.bot)
    fake_update = FakeUpdate(fake_message, update.effective_user, update.effective_chat)
    
    # Вызываем команду
    if action == "mine":
        await mine(fake_update, context)
    elif action == "inventory":
        await inventory_command(fake_update, context)
    elif action == "upgrade":
        await upgrade_command(fake_update, context)
    elif action == "craft":
        await craft_command(fake_update, context)
    elif action == "shop":
        await shop_command(fake_update, context)
    elif action == "mineshaft":
        await mineshaft_command(fake_update, context)
    elif action == "drones":
        await drones_command(fake_update, context)
    elif action == "daygift":
        await daygift_command(fake_update, context)
    elif action == "sector":
        await sector_command(fake_update, context)
    elif action == "drawings":
        await drawings_command(fake_update, context)
    elif action == "profile":
        await profile_command(fake_update, context)
    elif action == "top":
        await leaderboard_command(fake_update, context)
    elif action == "help":
        await help_command(fake_update, context)

async def safe_edit_message_group(query, text=None, reply_markup=None, parse_mode=None):
    try:
        if text is not None:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое сообщение
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            pass

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Проверяем и создаем данные если нет
    if 'all_inventories' not in context.bot_data:
        context.bot_data['all_inventories'] = {}
    if user_id not in context.bot_data['all_inventories']:
        context.bot_data['all_inventories'][user_id] = {'coins': 100, 'artifacts': 0}
    
    if 'sector' not in context.bot_data:
        context.bot_data['sector'] = {}
    if user_id not in context.bot_data['sector']:
        context.bot_data['sector'][user_id] = {
            'core': 'Осколок',
            'weapons': 0,
            'turrets': {},
            'units': {},
            'wave': 1,
            'last_attack_time': time.time(),
            'last_wave_damage': 0,
            'last_wave_composition': None,
            'captured_sectors': []
        }
    
    if 'mine_count' not in context.bot_data:
        context.bot_data['mine_count'] = {}
    if user_id not in context.bot_data['mine_count']:
        context.bot_data['mine_count'][user_id] = 0
    
    # Получаем данные
    inventory = context.bot_data['all_inventories'][user_id]
    sector_data = context.bot_data['sector'][user_id]
    mine_count = context.bot_data['mine_count'][user_id]
    
    weapons = sector_data.get('weapons', 0)
    coins = inventory.get('coins', 0)
    artifacts = inventory.get('artifacts', 0)
    
    # Определяем уровень
    if weapons < 1000:
        rank = "◽️  Начинающий (Lv. 1)"
    elif weapons < 2500:
        rank = "◻️  Осваивающийся (Lv. 2)"
    elif weapons < 10000:
        rank = "◾️  Любитель (Lv. 3)"
    elif weapons < 50000:
        rank = "◼️  Продвинутый (Lv. 4)"
    elif weapons < 150000:
        rank = "🔶 ️ Эксперт (Lv. 5)"
    elif weapons < 2000000:
        rank = "🔷 ️ Мастер (Lv. 6)"
    elif weapons < 30000000:
        rank = "🔺 ️ Легенда (Lv. 7)"
    else:
        rank = "💠  Бог (Lv. 8)"
    
    text = f"👤  {user_name}\n"
    text += f"{rank}\n"
    text += f"💥  Вооружение: {weapons}\n"
    text += f"🔮  Артефакты: {artifacts}\n"
    text += f"🪙  Монеты: {coins}\n"
    text += f"⛏️  Количество копаний: {mine_count}"
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Уникальные предметы", callback_data=f"profile_items_{user_id}")],
        [InlineKeyboardButton("🖼 GIF", callback_data=f"profile_gif_{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await safe_edit_message(update.callback_query, text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def profile_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    owner_id = int(data[2])
    
    if query.from_user.id != owner_id:
        await query.answer("❌ Это не ваш профиль!", show_alert=True)
        return
    
    # Получаем уникальные предметы игрока
    player_items = context.bot_data.get('unique_items', {}).get(owner_id, [])
    
    if not player_items:
        text = f"⚙️  Уникальные предметы игрока:\n\nНет уникальных предметов! Получайте их в ежедневном подарке /daygift"
    else:
        text = f"⚙️  Уникальные предметы игрока:\n\n"
        for item in player_items:
            item_data = UNIQUE_ITEMS_LIST.get(item, {"emoji": "⚙️ ", "rarity": "Обычный"})
            text += f"{item_data['emoji']} {item} - {item_data['rarity']}\n"
    
    keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"profile_back_{owner_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def profile_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    owner_id = int(data[2])
    
    if query.from_user.id != owner_id:
        await query.answer("❌ Это не ваш профиль!", show_alert=True)
        return
    
    text = "Скоро..."
    keyboard = [[InlineKeyboardButton("⬅️  Назад", callback_data=f"profile_back_{owner_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def profile_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await profile_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "⛏️  **Mindustry Копатель - полный гайд** ⛏️ \n\n"
        
        "/mine - ⛏️  Основная команда бота. Копай каждые 20 минут, получай один из восьми случайных ресурсов в случайном количестве - Медь/Свинец/Уголь/Песок/Титан/Торий/Вода/Нефть\n\n"
        
        "/inventory - 📦 Показывает количество артефактов, монет, добытых и скрафченных ресурсов игрока\n\n"
        
        "/craft - 🛠 Показывает рецепты крафтовых ресурсов, их курс обмена на монеты/артефакты а также команды для их крафта\n\n"
        
        "/shop - 🔮  Показывает курс обмена монет на артефакты а также команды для обмена ресурсов на артефакты/монеты\n\n"
        
        "/upgrade - 🔝  Команда для увеличения дохода а также сокращения кулдауна копания в /mine за артефакты\n\n"
        
        "/mineshaft - 🏔 Шахта с созданием буром за ресурсы. Буры автоматически добывают ресурсы, а чтобы поместить накопленное в инвентарь, нужно нажать на кнопку Собрать\n\n"
        
        "/drones - 🕹 Команда для исследования и покупки дронов за монеты. Дроны позволяют добывать ресурсы, которые выбирает игрок (чтобы поместить ресурсы в инвентарь нужно зайти в статистику дронов)\n\n"
        
        "/daygift - 🎁  Ежедневный подарок каждые 24 часа с выпадением случайного количества монет и артефактов а также выпадением уникальных предметов и турелей\n\n"
        
        "/sector - ⚔️  Самая большая команда. Показывает базу игрока с его вооружением, текущем уровнем, ядром, турелями, юнитами, статусом базы, последней атаки на базу, а также вражескими секторами для нападения. За прохождение секторов игрок получает монеты и разблокирует новые турели/юниты, а за полное прохождение секторов атака на его базу прекращается. Также в этой команде покупаются чертежи доступных турелей/юнитов за ресурсы\n\n"
        
        "/drawings - 📜  Показывает полный список чертежей игрока с их выполнением и ускорением за монеты/артефакты\n\n"
        
        "/top - 🏆 Показывает топ 30 лучших игроков за все время\n\n"
        
        "/profile - 👤  Показывает профиль игрока с его уровнем, вооружением базы, артефактами, монетами, количеством копаний за все время, а также его уникальными предметами, полученными в /daygift\n\n"
        
        "❓️  **Что такое 🔮  Артефакты?**\n"
        "🔮  Артефакты - Валюта которая в основном используется в /upgrade для улучшения добычи копания. Также используется для выполнения и ускорения чертежей.\n"
        "-Получить можно путем обмена крафтовых ресурсов или в /daygift\n\n"
        
        "❓️  **Что такое 🪙  Монеты?**\n"
        "🪙  Монеты - Валюта в основном для исследования и покупки дронов в /drones. Также используется для ускорения чертежей и для обмена на артефакты.\n"
        "-Получить можно путем обмена крафтовых и добываемых ресурсов или в /daygift\n\n"
        
        "❓️  **Что такое 💥  Вооружение?**\n"
        "💥  Вооружение - Это совокупность защиты и атаки всех имеющихся на базе игрока турелей и юнитов. Основная цель игры. Определяет место игрока в лидерборде. Вооружение может снижаться после атаки вражеских юнитов. При отрицательном вооружении игрок получает санкции на добычу."
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

def get_back_button():
    return [[InlineKeyboardButton("⬅️  Назад", callback_data="back_to_menu")]]

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await mindustrymining_command(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start)) 
    app.add_handler(CommandHandler("mine", mine))
    app.add_handler(CommandHandler("inventory", inventory_command))
    app.add_handler(CommandHandler("craft", craft_command))
    app.add_handler(CommandHandler("shop", shop_command))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(CommandHandler("mineshaft", mineshaft_command))
    app.add_handler(CommandHandler("drones", drones_command))
    app.add_handler(CommandHandler("daygift", daygift_command))
    app.add_handler(CommandHandler("sector", sector_command))
    app.add_handler(CommandHandler("drawings", drawings_command))
    app.add_handler(CommandHandler("top", leaderboard_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Команды обмена и крафта
    app.add_handler(CommandHandler("buyartifact", lambda u, c: buy_artifact(u, c, c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangecopper", lambda u, c: exchange_coins(u, c, "Медь", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangelead", lambda u, c: exchange_coins(u, c, "Свинец", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesand", lambda u, c: exchange_coins(u, c, "Песок", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangecoal", lambda u, c: exchange_coins(u, c, "Уголь", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangewater", lambda u, c: exchange_coins(u, c, "Вода", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangeoil", lambda u, c: exchange_coins(u, c, "Нефть", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangecryofluid", lambda u, c: exchange_coins(u, c, "Криогенная жидкость", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangetitanium", lambda u, c: exchange_coins(u, c, "Титан", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangethorium", lambda u, c: exchange_coins(u, c, "Торий", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangegraphite", lambda u, c: exchange_coins(u, c, "Графит", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangemetaglass", lambda u, c: exchange_coins(u, c, "Метастекло", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesilicon", lambda u, c: exchange_coins(u, c, "Кремний", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesporepod", lambda u, c: exchange_coins(u, c, "Споровый стручок", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangeplastanium", lambda u, c: exchange_coins(u, c, "Пластан", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesurgealloy", lambda u, c: exchange_coins(u, c, "Кинетический сплав", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangephasefabric", lambda u, c: exchange_coins(u, c, "Фазовая ткань", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangepyratite", lambda u, c: exchange_coins(u, c, "Пиротит", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangeblastcompound", lambda u, c: exchange_coins(u, c, "Взрывчатая смесь", c.args[0] if c.args else "0")))
    
    app.add_handler(CommandHandler("exchangegraphiteartifact", lambda u, c: exchange_artifact(u, c, "Графит", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangemetaglassartifact", lambda u, c: exchange_artifact(u, c, "Метастекло", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesiliconartifact", lambda u, c: exchange_artifact(u, c, "Кремний", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesporepodartifact", lambda u, c: exchange_artifact(u, c, "Споровый стручок", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangeplastaniumartifact", lambda u, c: exchange_artifact(u, c, "Пластан", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangesurgealloyartifact", lambda u, c: exchange_artifact(u, c, "Кинетический сплав", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangephasefabricartifact", lambda u, c: exchange_artifact(u, c, "Фазовая ткань", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangepyratiteartifact", lambda u, c: exchange_artifact(u, c, "Пиротит", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("exchangeblastcompoundartifact", lambda u, c: exchange_artifact(u, c, "Взрывчатая смесь", c.args[0] if c.args else "0")))
    
    app.add_handler(CommandHandler("craftgraphite", lambda u, c: craft_item(u, c, "graphite", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftmetaglass", lambda u, c: craft_item(u, c, "metaglass", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftsilicon", lambda u, c: craft_item(u, c, "silicon", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftsporepod", lambda u, c: craft_item(u, c, "sporepod", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftplastanium", lambda u, c: craft_item(u, c, "plastanium", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftsurgealloy", lambda u, c: craft_item(u, c, "surgealloy", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftphasefabric", lambda u, c: craft_item(u, c, "phasefabric", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftpyratite", lambda u, c: craft_item(u, c, "pyratite", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftblastcompound", lambda u, c: craft_item(u, c, "blastcompound", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftoil", lambda u, c: craft_item(u, c, "oil", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("craftcryofluid", lambda u, c: craft_item(u, c, "cryofluid", c.args[0] if c.args else "0")))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("mindustrymining", mindustrymining_command))
    
    # Callback обработчики с group=0
    app.add_handler(CallbackQueryHandler(sector_my_base, pattern="^sector_my_base$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_enemy_bases, pattern="^sector_enemy_bases$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_build, pattern="^sector_build$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_back, pattern="^sector_back$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_foundation, pattern="^sector_foundation$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_foundation_build, pattern="^sector_foundation_build$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_nucleus, pattern="^sector_nucleus$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_nucleus_build, pattern="^sector_nucleus_build$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_unit_build, pattern="^sector_unit_build$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_turret_build, pattern="^sector_turret_build$"), group=0)
    app.add_handler(CallbackQueryHandler(sector_turret_info, pattern="^turret_select_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_turret_buy, pattern="^turret_buy_"), group=0)
    app.add_handler(CallbackQueryHandler(unit_category, pattern="^unit_category_"), group=0)
    app.add_handler(CallbackQueryHandler(unit_info, pattern="^unit_select_"), group=0)
    app.add_handler(CallbackQueryHandler(unit_buy, pattern="^unit_buy_"), group=0)
    app.add_handler(CallbackQueryHandler(lambda u, c: sector_next_bases(u, c, u.callback_query.data.replace("next_", "")), pattern="^next_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_attack, pattern="^attack_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_attack_confirm, pattern="^confirm_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_attack_unit, pattern="^unit_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_attack_amount, pattern="^amount_"), group=0)
    app.add_handler(CallbackQueryHandler(sector_attack_amount_error, pattern="^error_"), group=0)
    app.add_handler(CallbackQueryHandler(lambda u, c: drawing_start(u, c, int(u.callback_query.data.replace("drawing_start_", ""))), pattern="^drawing_start_"), group=0)
    app.add_handler(CallbackQueryHandler(drawing_cancel, pattern="^drawing_cancel$"), group=0)
    app.add_handler(CallbackQueryHandler(lambda u, c: speedup_drawing(u, c, "coins", int(u.callback_query.data.split("_")[2])), pattern="^speedup_coins_"), group=0)
    app.add_handler(CallbackQueryHandler(lambda u, c: speedup_drawing(u, c, "artifacts", int(u.callback_query.data.split("_")[2])), pattern="^speedup_artifacts_"), group=0)
    app.add_handler(CallbackQueryHandler(drawings_back, pattern="^drawings_back$"), group=0)
    app.add_handler(CallbackQueryHandler(mine_build_menu, pattern="^mine_build_menu$"), group=0)
    app.add_handler(CallbackQueryHandler(mine_info, pattern="^mine_info$"), group=0)
    app.add_handler(CallbackQueryHandler(mine_collect, pattern="^mine_collect$"), group=0)
    app.add_handler(CallbackQueryHandler(mine_back, pattern="^mine_back$"), group=0)
    app.add_handler(CallbackQueryHandler(lambda u, c: mine_build_drill(u, c, u.callback_query.data.replace("mine_build_", "")), pattern="^mine_build_"), group=0)
    app.add_handler(CallbackQueryHandler(upgrade_callback, pattern="^upgrade_"), group=0)
    app.add_handler(CallbackQueryHandler(drone_back, pattern="^drone_back$"), group=0)
    app.add_handler(CallbackQueryHandler(drone_stats, pattern="^drone_stats$"), group=0)
    app.add_handler(CallbackQueryHandler(drone_buy_cancel, pattern="^drone_buy_cancel$"), group=0)
    app.add_handler(CallbackQueryHandler(profile_items, pattern="^profile_items_"), group=0)
    app.add_handler(CallbackQueryHandler(profile_gif, pattern="^profile_gif_"), group=0)
    app.add_handler(CallbackQueryHandler(profile_back, pattern="^profile_back_"), group=0)
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"), group=0)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"), group=0)
    
    for drone_name in DRONES.keys():
        app.add_handler(CallbackQueryHandler(lambda u, c, dn=drone_name: drone_research(u, c, dn), pattern=f"^drone_research_{drone_name}$"), group=0)
        app.add_handler(CallbackQueryHandler(lambda u, c, dn=drone_name: drone_buy(u, c, dn), pattern=f"^drone_buy_{drone_name}$"), group=0)
        app.add_handler(CallbackQueryHandler(lambda u, c, dn=drone_name: drone_set_resource(u, c, dn, u.callback_query.data.split("_")[3]), pattern=f"^drone_resource_{drone_name}_"), group=0)
    
    print("🤖  Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
