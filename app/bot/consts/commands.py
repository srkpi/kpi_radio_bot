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
    BotCommand(command="merge_ethers", description="Злити етери (+ опціонально дата)"),
    BotCommand(command="volume", description="Задати гучність програвання"),
    BotCommand(command="temp_volume", description="Задати гучність на поточний трек"),
    BotCommand(command="alert", description="Запустити тривогу"),
    BotCommand(command="stop_alert", description="Скасувати тривогу"),
    BotCommand(command="reply", description="Надіслати фідбек (+ реплай на замовлння)"),
    BotCommand(command="ban", description="Заблокувати користувача (реплай + причина)"),
    BotCommand(
        command="ban_with_feedback",
        description="Заблокувати користувача і зворотку (реплай + причина)",
    ),
    BotCommand(command="unban", description="Розблокувати юзера (+ user id)"),
    BotCommand(command="ban_list", description="Вивести список заблокованих юзерів"),
    BotCommand(command="send_orders", description="Надіслати таблицю з замовленнями"),
    BotCommand(command="send_database", description="Надіслати всю базу даних"),
    BotCommand(
        command="send_database_sql", description="Надіслати всю базу даних SQL файлом"
    ),
    BotCommand(command="restart", description="Перезавантажити бота"),
    BotCommand(command="force_play", description="Примусове програвання пісня (+ url)"),
    BotCommand(
        command="force_playlist",
        description="Примусове програвання плейлісту протягом етеру (+ url)",
    ),
    BotCommand(
        command="force_playlist_once",
        description="Примусове одноразове програвання плейлісту протягом етеру (+ url)",
    ),
    BotCommand(
        command="background_playlist",
        description="Фоновий плейлист: грає, коли немає інших замовлень (+ url)",
    ),
    BotCommand(
        command="background_playlist_once",
        description="Фоновий плейлист одноразово: грає, коли немає інших замовлень (+ url)",
    ),
    BotCommand(command="traktor", description="Їде трактор митися"),
    BotCommand(command="shark", description="Baby Shark Dance"),
    BotCommand(command="snow", description="Сніжинки пушинки"),
    BotCommand(
        command="auto_moderation",
        description="Список пісень автоматичної модерації",
    ),
    BotCommand(
        command="whitelist", description="Додати пісню до whitelist (+ id або реплай)"
    ),
    BotCommand(
        command="blacklist", description="Додати пісню до blacklist (+ id або реплай)"
    ),
    BotCommand(
        command="manual_list",
        description="Додати пісню до завжди ручного модерування (+ id або реплай)",
    ),
    BotCommand(
        command="remove_lists",
        description="Прибрати пісню зі списків модерування (+ id або реплай)",
    ),
    BotCommand(
        command="add_volume_change_point",
        description="Додати точку зміни гучності (час + гучність)",
    ),
    BotCommand(
        command="delete_volume_change_point",
        description="Видалити точку зміни гучності (+ час)",
    ),
    BotCommand(
        command="list_volume_change_points",
        description="Показати список точок зміни гучності",
    ),
    BotCommand(
        command="add_block_phrase",
        description="Додати фразу для блокування замовлення пісні",
    ),
    BotCommand(
        command="delete_block_phrase",
        description="Видалити фразу для блокування замовлення пісні",
    ),
    BotCommand(
        command="list_block_phrases",
        description="Показати фрази для блокування замовлень",
    ),
    BotCommand(
        command="not_moderated",
        description="Список пісень, які очікують на модерацію",
    ),
    BotCommand(command="now", description="Вивід поточної пісні"),
]
