import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROFILE_DIR = os.path.expanduser("~") + "/whatsapp_chrome_profile"

class WhatsAppSender:
    _driver = None

    @classmethod
    def init(cls):
        """Инициализация Chrome и WhatsApp Web"""
        logger.info("🚀 Запуск Chrome для WhatsApp Web...")

        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=" + PROFILE_DIR)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--remote-allow-origins=*")

        # Headless режим для сервера (раскомментировать при деплое)
        # chrome_options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        cls._driver = webdriver.Chrome(service=service, options=chrome_options)
        cls._driver.get("https://web.whatsapp.com")

        logger.info("⏳ Ожидание авторизации WhatsApp...")
        cls._wait_for_whatsapp_ready()
        logger.info("✅ WhatsApp Web готов к работе!")

    @classmethod
    def _wait_for_whatsapp_ready(cls, timeout_seconds=120):
        """Ожидание авторизации"""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                time.sleep(2)
                # Ищем главную боковую панель (признак авторизации)
                elements = cls._driver.find_elements(By.CSS_SELECTOR, "#side, div[title='New chat']")
                if elements:
                    logger.info("✅ Авторизация подтверждена!")
                    time.sleep(3)
                    return
            except Exception:
                pass

        raise Exception("❌ WhatsApp Web не авторизован за 2 минуты")

    @classmethod
    def send_message(cls, phone: str, text: str) -> bool:
        """Отправка сообщения в WhatsApp"""
        clean_phone = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
        phone_for_url = clean_phone[1:] if clean_phone.startswith('+') else clean_phone

        logger.info(f"📤 Отправка WhatsApp → {clean_phone}")

        try:
            url = f"https://web.whatsapp.com/send?phone={phone_for_url}&text={cls._encode_url(text)}"
            cls._driver.get(url)
            time.sleep(5)

            # Проверка на ошибку (номер не в WhatsApp)
            if cls._is_phone_not_on_whatsapp():
                logger.warning(f"❌ Номер {clean_phone} не зарегистрирован в WhatsApp")
                cls._close_error_dialog()
                return False

            # Поиск поля ввода
            input_box = cls._find_input_box()
            if not input_box:
                logger.warning("❌ Поле ввода не найдено")
                return False

            input_box.click()
            time.sleep(0.5)
            input_box.send_keys(Keys.ENTER)
            logger.info("↵ Сообщение отправлено")

            # Ждём подтверждения
            cls._wait_for_message_sent()

            # Возвращаемся на главную
            cls._driver.get("https://web.whatsapp.com")
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return False

    @classmethod
    def _find_input_box(cls):
        """Поиск поля ввода сообщения"""
        selectors = [
            "div[contenteditable='true'][data-tab='10']",
            "div[contenteditable='true'][data-tab='6']",
            "footer div[contenteditable='true']",
            "div[role='textbox'][contenteditable='true']"
        ]

        wait = WebDriverWait(cls._driver, 15)

        for selector in selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                logger.info(f"✅ Поле ввода найдено: {selector}")
                return element
            except Exception:
                continue

        return None

    @classmethod
    def _wait_for_message_sent(cls, timeout=15):
        """Ожидание подтверждения отправки"""
        sent_selectors = [
            "span[data-icon='msg-check']",
            "span[data-icon='msg-dblcheck']",
            "span[data-icon='msg-dblcheck-ack']"
        ]

        wait = WebDriverWait(cls._driver, timeout)

        for selector in sent_selectors:
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.info("✅ Подтверждение отправки получено")
                return True
            except Exception:
                continue

        return False

    @classmethod
    def _is_phone_not_on_whatsapp(cls) -> bool:
        """Проверка, есть ли номер в WhatsApp"""
        error_texts = [
            "не пользуется WhatsApp",
            "not on WhatsApp",
            "Invalid phone number",
            "Недействительный номер телефона"
        ]

        for text in error_texts:
            try:
                cls._driver.find_element(By.XPATH, f"//*[contains(text(),'{text}')]")
                return True
            except Exception:
                continue
        return False

    @classmethod
    def _close_error_dialog(cls):
        """Закрытие диалога ошибки"""
        try:
            btn = cls._driver.find_element(By.XPATH, "//div[@role='button'][contains(.,'OK') or contains(.,'Ок')]")
            btn.click()
        except Exception:
            pass

    @staticmethod
    def _encode_url(text: str) -> str:
        """URL-кодирование текста"""
        import urllib.parse
        return urllib.parse.quote(text)

    @classmethod
    def shutdown(cls):
        """Закрытие браузера"""
        if cls._driver:
            logger.info("🔴 Закрываем браузер...")
            cls._driver.quit()