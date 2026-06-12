import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROFILE_DIR = os.path.expanduser("~") + "/whatsapp_chrome_profile"

class WhatsAppSender:
    _driver = None
    
    @classmethod
    def init(cls):
        """Инициализация Chromium и WhatsApp Web"""
        if cls._driver is not None:
            try:
                cls._driver.quit()
            except:
                pass
        
        logger.info("🚀 Запуск Chromium для WhatsApp Web...")
        
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=" + PROFILE_DIR)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--remote-allow-origins=*")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        
        # Используем системный Chromium
        service = Service(executable_path="/usr/bin/chromedriver")
        cls._driver = webdriver.Chrome(service=service, options=chrome_options)
        cls._driver.get("https://web.whatsapp.com")
        
        logger.info("⏳ Ожидание авторизации WhatsApp...")
        cls._wait_for_whatsapp_ready()
        logger.info("✅ WhatsApp Web готов к работе!")
    
    @classmethod
    def _ensure_driver(cls):
        """Проверка, что драйвер существует и активен"""
        if cls._driver is None:
            logger.warning("⚠️ Драйвер не инициализирован, пересоздаём...")
            cls.init()
            return True
        
        try:
            cls._driver.current_url
            return True
        except Exception as e:
            logger.warning(f"⚠️ Драйвер неактивен: {e}, пересоздаём...")
            cls.init()
            return True
    
    @classmethod
    def _wait_for_whatsapp_ready(cls, timeout_seconds=120):
        """Ожидание авторизации"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                time.sleep(2)
                elements = cls._driver.find_elements(By.CSS_SELECTOR, "#side, div[title='New chat'], div[aria-label='Chat list']")
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
        cls._ensure_driver()
        
        clean_phone = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
        phone_for_url = clean_phone[1:] if clean_phone.startswith('+') else clean_phone
        
        logger.info(f"📤 Отправка WhatsApp → {clean_phone}")
        
        try:
            url = f"https://web.whatsapp.com/send?phone={phone_for_url}&text={cls._encode_url(text)}"
            cls._driver.get(url)
            time.sleep(8)
            
            if cls._is_phone_not_on_whatsapp():
                logger.warning(f"❌ Номер {clean_phone} не зарегистрирован в WhatsApp")
                cls._close_error_dialog()
                cls._driver.get("https://web.whatsapp.com")
                time.sleep(2)
                return False
            
            input_box = cls._find_input_box()
            if not input_box:
                logger.warning("❌ Поле ввода не найдено")
                cls._driver.get("https://web.whatsapp.com")
                time.sleep(2)
                return False
            
            input_box.click()
            time.sleep(1)
            input_box.clear()
            input_box.send_keys(text)
            time.sleep(1)
            input_box.send_keys(Keys.ENTER)
            logger.info("✓ Сообщение отправлено")
            
            time.sleep(3)
            cls._wait_for_message_sent()
            
            cls._driver.get("https://web.whatsapp.com")
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            try:
                cls._driver.get("https://web.whatsapp.com")
                time.sleep(3)
            except:
                pass
            return False
    
    @classmethod
    def _find_input_box(cls):
        """Поиск поля ввода сообщения"""
        if cls._driver is None:
            return None
            
        selectors = [
            "div[contenteditable='true'][data-tab='10']",
            "div[contenteditable='true'][data-tab='6']",
            "div[contenteditable='true'][data-tab='97']",
            "footer div[contenteditable='true']",
            "div[role='textbox'][contenteditable='true']",
            "div[contenteditable='true']"
        ]
        
        for selector in selectors:
            try:
                wait = WebDriverWait(cls._driver, 8)
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                if element:
                    logger.info(f"✅ Поле ввода найдено")
                    return element
            except Exception:
                continue
        
        try:
            elements = cls._driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            if elements:
                logger.info("✅ Поле ввода найдено (запасной вариант)")
                return elements[-1]
        except:
            pass
        
        return None
    
    @classmethod
    def _wait_for_message_sent(cls, timeout=20):
        """Ожидание подтверждения отправки"""
        if cls._driver is None:
            return False
            
        sent_selectors = [
            "span[data-icon='msg-check']",
            "span[data-icon='msg-dblcheck']",
            "span[data-icon='msg-dblcheck-ack']",
            "div[class*='message-out']"
        ]
        
        for selector in sent_selectors:
            try:
                wait = WebDriverWait(cls._driver, timeout)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.info("✅ Подтверждение отправки получено")
                return True
            except Exception:
                continue
        
        return True
    
    @classmethod
    def _is_phone_not_on_whatsapp(cls) -> bool:
        """Проверка, есть ли номер в WhatsApp"""
        if cls._driver is None:
            return False
            
        error_texts = [
            "не пользуется WhatsApp",
            "not on WhatsApp",
            "Invalid phone number",
            "Недействительный номер телефона"
        ]
        
        for text in error_texts:
            try:
                elements = cls._driver.find_elements(By.XPATH, f"//*[contains(text(),'{text}')]")
                if elements:
                    return True
            except Exception:
                continue
        return False
    
    @classmethod
    def _close_error_dialog(cls):
        """Закрытие диалога ошибки"""
        if cls._driver is None:
            return
        try:
            buttons = cls._driver.find_elements(By.XPATH, "//div[@role='button'][contains(.,'OK') or contains(.,'Ок')]")
            if buttons:
                buttons[0].click()
        except Exception:
            pass
    
    @staticmethod
    def _encode_url(text: str) -> str:
        import urllib.parse
        return urllib.parse.quote(text)
    
    @classmethod
    def shutdown(cls):
        if cls._driver:
            logger.info("🔴 Закрываем браузер...")
            try:
                cls._driver.quit()
            except:
                pass
            cls._driver = None
