import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pdf_phone_extractor import extract_phones_from_pdf
from phone_record import PhoneRecord
from whatsapp_sender import WhatsAppSender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8827507215:AAGCzPvre3sPFu4wcfR80EMANm-gAgRONlQ")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "1636373767"))

class ProfileBot:
    def __init__(self):
        self.phone_records = []  # список PhoneRecord
        self.selected_phone = None  # выбранный номер для отправки

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return

        await update.message.reply_text(
            "✅ Бот готов. Отправляйте PDF-файлы с профилями.\n\n"
            "Команды:\n"
            "/numbers - список номеров\n"
            "/send - отправить сообщение выбранному номеру из PDF\n"
            "/sendmanual - отправить сообщение на любой номер"
        )

    async def numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id != ADMIN_CHAT_ID:
            return

        if not self.phone_records:
            await update.message.reply_text("Список номеров пока пуст.")
            return

        lines = ["📋 Список всех номеров:\n"]
        for i, record in enumerate(self.phone_records):
            lines.append(f"{i+1}. {record.phone}")

        await update.message.reply_text("\n".join(lines))

    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id != ADMIN_CHAT_ID:
            return

        if not self.phone_records:
            await update.message.reply_text("❌ Список номеров пуст. Сначала отправьте PDF.")
            return

        keyboard = []
        for record in self.phone_records:
            keyboard.append([InlineKeyboardButton(record.phone, callback_data=f"send_{record.phone}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📱 Выберите номер для отправки сообщения:", reply_markup=reply_markup)

    async def send_manual(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id != ADMIN_CHAT_ID:
            return

        self.selected_phone = "MANUAL_MODE"
        await update.message.reply_text(
            "✏️ Введите номер телефона в формате +79XXXXXXXXX и текст сообщения через пробел.\n\n"
            "Пример: +79123456789 Привет, это тестовое сообщение"
        )

    # Добавить в класс ProfileBot:

async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса WhatsApp"""
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_CHAT_ID:
        return
    
    status = WhatsAppSender.get_status()
    
    status_messages = {
        "authorized": "✅ WhatsApp подключён и готов",
        "notAuthorized": "❌ WhatsApp не авторизован (нужен QR-код)",
        "blocked": "🚫 Аккаунт заблокирован",
        "sleepMode": "😴 Режим сна (норма)",
        "starting": "⏳ Запускается...",
    }
    
    text = status_messages.get(status, f"❓ Статус: {status}")
    await update.message.reply_text(f"📱 Статус WhatsApp:\n{text}")


# В функции main() добавить обработчик:
# application.add_handler(CommandHandler("status", bot.status))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        if chat_id != ADMIN_CHAT_ID:
            return

        data = query.data
        if data.startswith("send_"):
            phone = data[5:]
            self.selected_phone = phone
            await query.edit_message_text(f"✏️ Введите текст сообщения для отправки на номер {phone}:")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ У вас нет доступа.")
            return

        # Обработка PDF
        if update.message.document and update.message.document.mime_type == "application/pdf":
            await self.process_pdf(update, context)
            return

        # Обработка текста (если выбран номер)
        if update.message.text and self.selected_phone:
            text = update.message.text

            if self.selected_phone == "MANUAL_MODE":
                await self.send_manual_sms(update, context, text)
            else:
                await self.send_sms_to_selected(update, context, text)

            self.selected_phone = None

    async def process_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        document = update.message.document
        file_name = document.file_name

        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        temp_path = f"/tmp/{file_name}"
        await file.download_to_drive(temp_path)

        try:
            phones = extract_phones_from_pdf(temp_path)

            if not phones:
                await update.message.reply_text("⚠️ В PDF не найдено номеров телефона.")
            else:
                for phone in phones:
                    record = PhoneRecord(
                        phone,
                        file_name,
                        update.message.from_user.username or "unknown",
                        update.message.from_user.first_name or "unknown"
                    )
                    self.phone_records.append(record)
                    logger.info(f"✅ Найден номер: {phone}")

                await update.message.reply_text(
                    f"✅ Успешно извлечено {len(phones)} номеров из файла {file_name}.\n\n"
                    "Используйте /send для отправки сообщений выбранному номеру."
                )
        except Exception as e:
            logger.error(f"Ошибка обработки PDF: {e}")
            await update.message.reply_text(f"❌ Ошибка при обработке PDF: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def send_sms_to_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        chat_id = update.effective_chat.id
        phone = self.selected_phone

        if not phone:
            await update.message.reply_text("❌ Ошибка: номер не выбран.")
            return

        await update.message.reply_text(f"⏳ Отправка WhatsApp на {phone}...")

        success = WhatsAppSender.send_message(phone, message_text)

        if success:
            await update.message.reply_text(f"✅ Сообщение отправлено в WhatsApp на {phone}")
        else:
            await update.message.reply_text(
                f"❌ Ошибка отправки в WhatsApp на {phone}\n\n"
                "Возможные причины:\n"
                "- У получателя нет WhatsApp\n"
                "- Неверный номер\n"
                "- Бот не подключён к WhatsApp"
            )

    async def send_manual_sms(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
        chat_id = update.effective_chat.id

        parts = user_input.split(' ', 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Неверный формат. Используйте: +79XXXXXXXXX Текст")
            return

        phone = parts[0].strip()
        message = parts[1].strip()

        import re
        if not re.match(r'\+7\d{10}', phone):
            await update.message.reply_text("❌ Неверный формат номера. Используйте +79XXXXXXXXX")
            return

        if not message:
            await update.message.reply_text("❌ Текст сообщения не может быть пустым")
            return

        await update.message.reply_text(f"⏳ Отправка WhatsApp на {phone}...")

        success = WhatsAppSender.send_message(phone, message)

        if success:
            await update.message.reply_text(f"✅ Сообщение успешно отправлено в WhatsApp на {phone}")
        else:
            await update.message.reply_text(f"❌ Ошибка отправки WhatsApp на {phone}")

def main():
    # Инициализация WhatsApp
    try:
        WhatsAppSender.init()
    except Exception as e:
        logger.error(f"Ошибка инициализации WhatsApp: {e}")
        logger.warning("Продолжаем без WhatsApp...")

    # Создаём бота
    bot = ProfileBot()
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("numbers", bot.numbers))
    application.add_handler(CommandHandler("send", bot.send_command))
    application.add_handler(CommandHandler("sendmanual", bot.send_manual))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.ALL, bot.handle_message))

    # Запуск
    logger.info("✅ Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
