import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.BOT_TOKEN = 'your_token'
        
        admin_ids = os.getenv("ADMIN_IDS", "123456789")
        self.ADMIN_IDS = [int(id_str) for id_str in admin_ids.split(",")] if admin_ids else []
        
        self.CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "cryptobot_token")
        self.CRYPTO_PAY_TESTNET = os.getenv("CRYPTO_PAY_TESTNET", "false").lower() == "true"
        
        self.LZT_TOKEN = ""
        self.DATABASE_URL = "sqlite:///data/database.db"
        
        self.STAR_PRICES = {
            50: 70,    # 50 звезд за 70 рублей
            100: 140,  
            200: 280,  
            500: 700,  
            1000: 1400 
        }

config = Config()