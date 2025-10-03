from .server import db
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

class TabulatorTables(db.Model):
    __tablename__ = 'tab_tab' # Таблица, содержащая айди и названия магазинов

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='') # название магазина

class TabulatorShopRemainder(db.Model):
    __tablename__ = 'tab_shop_rem' # Таблица, содержащая данные магазина об остатках, продажах, ценах и т.п.

    id = Column(Integer, primary_key=True, autoincrement=True) 
    table_id = Column(Integer, default=0) 
    art = Column(Integer, default=0) # номер артикула
    category= Column(String, default='') # категория артикула
    remainder = Column(Float, default=0.0) # текущий остаток в магазине
    price = Column(Float, default=0.0) # закупочная цена
    priceretail = Column(Float, default=0.0) # розничная цена
    avg = Column(Float, default=0.0) # средние продажи
    nosaledays= Column(Integer, default=0) # количество дней без продаж
