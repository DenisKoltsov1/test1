import aiohttp
import asyncio
import csv
import smtplib
from email.mime.text import MIMEText
from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise import run_async

# Настройки базы данных и почты
DATABASE_URL = "postgres://username:password@localhost:5432/mydatabase"
EMAIL_SETTINGS = {
    "SMTP_SERVER": "smtp.mailtrap.io",
    "SMTP_PORT": 587,
    "EMAIL": "your_email",
    "PASSWORD": "your_password"
}

# API ссылки для разных бирж
API_ENDPOINTS = {
    "binance": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    "bybit": "https://api.bybit.com/v2/public/tickers?symbol=BTCUSDT",
    "coinmarketcap": "https://api.coinmarketcap.com/v1/ticker/bitcoin/"
}

# Модель для записи данных
class PriceRecord(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=50)
    price = fields.DecimalField(max_digits=20, decimal_places=2)
    max_price = fields.DecimalField(max_digits=20, decimal_places=2)
    min_price = fields.DecimalField(max_digits=20, decimal_places=2)
    date = fields.DatetimeField(auto_now_add=True)
    difference = fields.DecimalField(max_digits=20, decimal_places=2)
    total_amount = fields.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        table = "price_records"

# Функция отправки email
async def send_email(price, difference):
    msg = MIMEText(f"Цена изменилась: {price}, разница: {difference}")
    msg['Subject'] = 'Изменение цены BTC'
    msg['From'] = EMAIL_SETTINGS['EMAIL']
    msg['To'] = 'recipient@example.com'

    with smtplib.SMTP(EMAIL_SETTINGS['SMTP_SERVER'], EMAIL_SETTINGS['SMTP_PORT']) as server:
        server.login(EMAIL_SETTINGS['EMAIL'], EMAIL_SETTINGS['PASSWORD'])
        server.sendmail(EMAIL_SETTINGS['EMAIL'], ['recipient@example.com'], msg.as_string())

# Универсальная функция для получения цен
async def fetch_price(session, url, exchange):
    async with session.get(url) as response:
        data = await response.json()

        if exchange == "binance":
            return float(data['price'])
        elif exchange == "bybit":
            return float(data['result'][0]['last_price'])
        elif exchange == "coinmarketcap":
            return float(data[0]['price_usd'])
        else:
            return None

# Основная функция отслеживания цен
async def track_prices():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_price(session, url, exchange) for exchange, url in API_ENDPOINTS.items()]
        results = await asyncio.gather(*tasks)

        # Пример: обработка данных для первой биржи (Binance)
        for exchange, price in zip(API_ENDPOINTS.keys(), results):
            difference = 0.03  

            # Запись в CSV
            with open('prices.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([f'{exchange} BTC/USDT', price, price, price, '2024-09-14', difference, 3 * price])

            # Запись в БД
            await PriceRecord.create(title=f'{exchange} BTC/USDT', price=price, max_price=price, min_price=price,
                                     difference=difference, total_amount=3 * price)

            # Отправка email при изменении цены
            if difference >= 0.03:
                await send_email(price, difference)

# Инициализация базы данных
async def init():
    await Tortoise.init(db_url=DATABASE_URL, modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

if __name__ == "__main__":
    run_async(init())
    asyncio.run(track_prices())