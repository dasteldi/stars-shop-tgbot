import json
import hmac
import hashlib
from datetime import datetime
from typing import Optional, Tuple, Dict
import aiohttp
from sqlalchemy.orm import Session

from config import config
from database import Payment

class CryptoPay:
    """оплата криптоботом"""
    
    def __init__(self):
        self.api_token = config.CRYPTO_PAY_TOKEN
        self.testnet = config.CRYPTO_PAY_TESTNET
        self.base_url = "https://testnet-pay.crypt.bot/api" if self.testnet else "https://pay.crypt.bot/api"
        
    def _get_headers(self) -> Dict[str, str]:
        """получить заголовки для запросов"""
        return {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    async def get_exchange_rate(self) -> float:
        """получить текущий курс USDT/RUB"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/getExchangeRates",
                    headers=self._get_headers()
                ) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        rates = result.get("result", [])
                        for rate in rates:
                            if rate.get("source") == "USDT" and rate.get("target") == "RUB":
                                return float(rate.get("rate", 95.0))
        except Exception as e:
            print(f"Crypto Pay get_exchange_rate error: {e}")
        return 95.0
    
    async def create_usdt_invoice(
        self, 
        amount_rub: float,
        description: str,
        payload: str = "",
        expires_in: int = 1800
    ) -> Optional[Dict]:
        """Создать инвойс в USDT"""
        try:
            async with aiohttp.ClientSession() as session:
                # Получаем текущий курс
                rate = await self.get_exchange_rate()
                usdt_amount = amount_rub / rate
                
                data = {
                    "currency_type": "fiat",
                    "fiat": "RUB",
                    "accepted_assets": "USDT",
                    "amount": str(amount_rub),
                    "description": description[:1024],
                    "payload": payload,
                    "expires_in": expires_in,
                    "allow_comments": False,
                    "allow_anonymous": False,
                    "paid_btn_name": "openBot",
                    "paid_btn_url": "https://t.me/CryptoBot"
                }
                
                async with session.post(
                    f"{self.base_url}/createInvoice",
                    headers=self._get_headers(),
                    json=data
                ) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        invoice = result.get("result")
                        
                        return {
                            "invoice_id": invoice.get("invoice_id"),
                            "hash": invoice.get("hash"),
                            "bot_invoice_url": invoice.get("bot_invoice_url"),
                            "mini_app_invoice_url": invoice.get("mini_app_invoice_url"),
                            "web_app_invoice_url": invoice.get("web_app_invoice_url"),
                            "amount_rub": amount_rub,
                            "usdt_amount": usdt_amount,
                            "rate": rate,  # Добавляем курс
                            "status": invoice.get("status"),
                            "created_at": invoice.get("created_at")
                        }
                    else:
                        print(f"Crypto Pay Error: {result.get('error')}")
                        return None
                        
        except Exception as e:
            print(f"Crypto Pay create_invoice error: {e}")
            return None
    
    async def get_invoice_status(self, invoice_id: int) -> Optional[Dict]:
        """Получить статус инвойса"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "invoice_ids": str(invoice_id),
                    "count": 1
                }
                
                async with session.get(
                    f"{self.base_url}/getInvoices",
                    headers=self._get_headers(),
                    params=params
                ) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        invoices = result.get("result", {}).get("items", [])
                        if invoices:
                            return invoices[0]
                    return None
                        
        except Exception as e:
            print(f"Crypto Pay get_invoice_status error: {e}")
            return None
    
    async def check_invoice_paid(self, invoice_id: int) -> bool:
        """Проверить, оплачен ли инвойс"""
        invoice = await self.get_invoice_status(invoice_id)
        if invoice and invoice.get("status") == "paid":
            return True
        return False

# Глобальный экземпляр
crypto_pay = CryptoPay()