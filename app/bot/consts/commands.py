from aiogram.types import BotCommand

USER_COMMANDS = [
    BotCommand(command="start", description="До початку"),
    BotCommand(command="help", description="Допомога"),
]

ADMIN_COMMANDS = [
    BotCommand(command="skip", description="Пропустити поточний трек"),
    BotCommand(command="cancel", description="Скасувати трек (+ реплай на замовлення)"),
    BotCommand(command="stop", description="Скасувати треки на поточний етер"),
    BotCommand(command="stop_today", description="Скасувати треки на сьогодні"),
    BotCommand(command="stop_all", description="Скасувати усі треки"),
    BotCommand(command="holiday", description="Зробити етери як на вихідний день"),
    BotCommand(command="unholiday", description="Зробити етери як у будній день"),
    BotCommand(command="close", description="Закрити день до замовлень (+ причина)"),
    BotCommand(command="open", description="Відкрити день до замовлень"),
    BotCommand(command="volume", description="Задати гучність програвання"),
    BotCommand(command="temp_volume", description="Задати гучність на поточний трек"),
    BotCommand(command="alert", description="Запустити тривогу"),
    BotCommand(command="stop_alert", description="Скасувати тривогу"),
    BotCommand(command="reply", description="Надіслати фідбек (+ реплай на замовлння)"),
    BotCommand(command="ban", description="Заблокувати користувача (реплай + причина)"),
    BotCommand(command="unban", description="Розблокувати юзера (+ user id)"),
    BotCommand(command="ban_list", description="Вивести список заблокованих юзерів"),
    BotCommand(command="send_orders", description="Надіслати таблицю з замовленнями"),
    BotCommand(command="send_database", description="Надіслати всю базу даних"),
    BotCommand(command="restart", description="Перезавантажити бота"),
    BotCommand(command="force_play", description="Примусове програвання пісня (+ url)"),
    BotCommand(
        command="force_playlist",
        description="Примусове програвання плейлісту протягом етеру (+ url)",
    ),
    BotCommand(command="traktor", description="Їде трактор митися"),
    BotCommand(command="shark", description="Baby Shark Dance"),
]
