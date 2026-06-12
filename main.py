from profile_bot import main
from whatsapp_sender import WhatsAppSender
import signal
import sys

def shutdown_handler(signum, frame):
    print("🔴 Завершение работы...")
    WhatsAppSender.shutdown()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    main()