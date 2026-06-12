import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем из переменных окружения
INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID", "")
INSTANCE_TOKEN = os.environ.get("GREEN_API_TOKEN", "")
BASE_URL = f"https://api.green-api.com/waInstance{INSTANCE_ID}"


class WhatsAppSender:

    @classmethod
    def init(cls):
        """Проверка подключения к Green API"""
        if not INSTANCE_ID or not INSTANCE_TOKEN:
            raise ValueError(
                "❌ Не заданы GREEN_API_INSTANCE_ID и GREEN_API_TOKEN"
            )

        try:
            url = f"{BASE_URL}/getStateInstance/{INSTANCE_TOKEN}"
            response = requests.get(url, timeout=10)
            data = response.json()

            state = data.get("stateInstance", "unknown")
            logger.info(f"📱 Green API статус: {state}")

            if state == "authorized":
                logger.info("✅ WhatsApp авторизован и готов!")
            elif state == "notAuthorized":
                logger.warning(
                    "⚠️ WhatsApp не авторизован!\n"
                    "Перейдите в личный кабинет Green API "
                    "и отсканируйте QR-код."
                )
            else:
                logger.warning(f"⚠️ Неизвестный статус: {state}")

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Green API: {e}")
            raise

    @classmethod
    def send_message(cls, phone: str, text: str) -> bool:
        """
        Отправка сообщения через Green API
        
        Args:
            phone: номер в формате +79XXXXXXXXX
            text: текст сообщения
            
        Returns:
            True если успешно, False если ошибка
        """
        if not INSTANCE_ID or not INSTANCE_TOKEN:
            logger.error("❌ Green API не настроен")
            return False

        # Форматируем номер: убираем + и добавляем @c.us
        clean_phone = ''.join(ch for ch in phone if ch.isdigit())
        
        # Убираем ведущую 8, заменяем на 7
        if clean_phone.startswith('8') and len(clean_phone) == 11:
            clean_phone = '7' + clean_phone[1:]
        
        chat_id = f"{clean_phone}@c.us"

        logger.info(f"📤 Отправка WhatsApp → {phone} (chat_id: {chat_id})")

        try:
            url = f"{BASE_URL}/sendMessage/{INSTANCE_TOKEN}"
            
            payload = {
                "chatId": chat_id,
                "message": text
            }
            
            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            logger.info(f"📡 Ответ API: {response.status_code} — {response.text}")

            if response.status_code == 200:
                data = response.json()
                
                # Green API возвращает idMessage при успехе
                if "idMessage" in data:
                    logger.info(
                        f"✅ Сообщение отправлено! ID: {data['idMessage']}"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ Неожиданный ответ: {data}")
                    return False
            else:
                logger.error(
                    f"❌ Ошибка API: {response.status_code} — {response.text}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут запроса к Green API")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ошибка соединения с Green API")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return False

    @classmethod
    def get_status(cls) -> str:
        """Получить текущий статус подключения"""
        try:
            url = f"{BASE_URL}/getStateInstance/{INSTANCE_TOKEN}"
            response = requests.get(url, timeout=10)
            data = response.json()
            return data.get("stateInstance", "unknown")
        except Exception as e:
            return f"error: {e}"

    @classmethod
    def shutdown(cls):
        """Заглушка для совместимости с main.py"""
        logger.info("✅ WhatsApp Sender остановлен")
