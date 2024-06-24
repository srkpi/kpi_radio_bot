START = 'Привіт, це бот Радіо КПІ.\n' \
        'Ти можеш:\n' \
        '📝 Замовити пісню\n' \
        '🖌 Поставити будь-яке запитання, що-небудь запропонувати, запропонувати свою кандидатуру до наших лав\n' \
        '🎧 Дізнатися, що грає зараз, грало чи гратиме\n' \
        '⏱ Дізнатися, коли в улюбленому КПІ перерви\n' \
        '\n⁉️ Радимо насамперед прочитати інструкцію (/help)'

MENU = 'Вибери, що хочеш зробити 😜'

# user making order

ORDER_CHOOSE_SONG = 'Що ти хочеш почути?\n' \
                    '➖ Напиши назву пісні, та бот її знайде 🔎\n' \
                    '➖ Скинь посилання на трек із music.youtube.com\n' \
                    '➖ Завантаж або перейшли аудіофайл\n' \
                    '➖ Скористайся інлайн пошуком нижче\n' \
                    '➖ Використовуй інших ботів для пошуку та перейшли аудіо сюди (@vkm4bot, @LyBot)\n' \
                    '\n⛔️ /cancel для скасування'

ORDER_INLINE_SEARCH = 'Натисни кнопку для інлайн-пошуку в нашому боті 👀'

CHOOSE_DAY = 'Вибери день'
CHOOSE_TIME = '{0}, відмінно. Тепер вибери час'

ORDER_CANCELED = 'Ну ок'

ORDER_ERR_TOOLATE = 'На цей час вже точно не встигне'
ORDER_ERR_TOOMUCH = 'Ви замовили забагато треків на цей етер'

ORDER_ON_MODERATION = 'Дякуємо за замовлення ({0}), чекай на модерацію!'

ORDER_ACCEPTED = 'Твоє замовлення "<b>{0}</b>", ({1}) прийняте!'
ORDER_ACCEPTED_NOW = 'Твоє замовлення "<b>{0}</b>" прийняте та заграє {1}'
ORDER_ACCEPTED_TOOLATE = 'Ми хотіли прийняти твоє замовлення "<b>{0}</b>", ({1}), але воно вже не влізе в етер(( ' \
                         'Бажаєш перезамовлення?'
ORDER_DENIED = 'Твоє замовлення "<b>{0}</b>" ({1}) відхилено('

# pasted in ORDER_ACCEPTED_NOW.1
# and after ORDER_CAPTION_MODERATED *for admins*
ORDER_WILL_PLAY_UPNEXT = 'прямо зараз!'
ORDER_WILL_PLAY_IN = 'через {0} {1}'

# only for admins
ORDER_WILL_PLAY_SOMETIME = 'Заграє коли треба'
ORDER_ERR_NOT_ENOUGH_TIME = 'Не встиг :('
ORDER_ERR_DUPLICATE = 'Такий самий трек вже прийнятий на цей етер'


# notifies
ORDER_PLAYING = 'Твоє замовлення "<b>{0}</b>" заграло! \n /notify — вимкнути сповіщення'
ORDER_NOTIFY_STATUS = "Сповіщення <b>вимкнуті</b> \n /notify - увімкнути", \
                      "Сповіщення <b>увімкнуті</b> \n /notify - вимкнути"

ORDER_PEREZAKLAD = 'Твоє замовлення не встигло заграти на цьому етері. Бажаєш перезамовлення?'


# captions
ORDER_CAPTION = '{is_now_mark} Нове замовлення: \n' \
                '{ether_name} \n' \
                'від {user_name}<code>   </code>#відмодерити\n' \
                '{is_anime_mark}{bad_words}'

ORDER_CAPTION_MODERATED = 'Замовлення: \n' \
                          '{ether_name} \n' \
                          'від {user_name} \n' \
                          '{status_text} ({moder_name})'

ORDER_IS_NOW_MARK = '❗️', '‼️'
ORDER_IS_NOW_TEXT = '', '(зараз!)'
ORDER_IS_ANIME_MARK = '', '🅰️'
ORDER_BAD_WORDS_MARK = '', "🆗", "⚠"
ORDER_STATUS = '❌Відхилено', '✅Прийнято'
#


BAN_TRY_ORDER = 'Ти не можеш пропонувати музику до {0}'
BAN_YOU_BANNED = 'Ти був/-ла забанений/-а на {0}. {1}'
BAN_REASON = " Бан по причині: <i>{}</i>"

SEARCH_FAILED = 'Нічого не знайшов( \n Можеш завантажити аудіо сам або переслати від іншого бота!'

SOMETHING_BAD_IN_ORDER = '<i>Упс..</i> Є деяка <b>імовірність</b>, що цей трек порушує правила: \n' \
                         '{} \n\n Якщо ти вважаєш, що все ок, натисни кнопку "<code>Все ок</code>"'

BAD_ORDER_SHORT = 'Трек занадто короткий (&lt;1 хв)'
BAD_ORDER_LONG = 'Трек занадто довгий (>6 хв). Краще не замовляти його на перерви'
BAD_ORDER_BADWORDS = 'Імовірно, трек містить мати'
BAD_LANGUAGE = 'Пішов нахуй звідси'
BAD_ORDER_ANIME = 'Імовірно, трек є аніме опенінгом'
BAD_ORDER_PERFORMER = 'Імовірно, трек є "не форматом радіо"'

# playlist

PLAYLIST_NOW = '⏮ <b>Попередній трек: </b> {0}\n' \
               '▶ <b>Зараз грає: </b> {1}\n' \
               '⏭ <b>Наступний трек: </b> {2}'

PLAYLIST_NOW_NOTHING = 'На Політехнічній наразі нічого не грає. Але грає на *вставити посилання на ютуб*'  # todo
PLAYLIST_EMPTY = "❗️Ще нічого не замовлено"
PLAYLIST_ITEM = "🕖<b>{start_time}</b> {track_name}"

# timetable
TIMETABLE_ITEM = "   {start} - {stop}   {ether_name}\n"
TIMETABLE_ETHER_NOW = "\nЕтер прям зараз!"
TIMETABLE_ETHER_CLOSEST = f"\nНайближчий етер - {0}, {1}"


# feedback
FEEDBACK = 'Пиши сюди все, що хочеш, чи роби реплай на повідомлення від нас, і ми відповімо тобі) \n' \
           'Ще у нас є чат: @rhub_kpi \n (⛔️ /cancel)'
FEEDBACK_THANKS = 'Дякуємо за повідомлення!'

# communication
COMMUNICATION_RECEIVE = "Від {user} #{hashtag}: \n"

COMMUNICATION_REPLY_TO_AUDIO = "На твоє замовлення <i>({})</i> відповіли: \n"
COMMUNICATION_REPLY_TO_TEXT = "На твоє повідомлення відповіли: \n"

# other

HISTORY_TITLE = 'Замовив/-ла {0}'
ERROR = 'Не вийшло('
UNKNOWN_CMD = 'Що ти хочеш? Для замовлення пісні не забувай натискати кнопку "Замовити пісню". Допомога тут: /help'

STARTUP_MESSAGE = "Ребутнувся!"

MINUTES = ('хвилину', 'хвилини', 'хвилин')

HELP = {
    'orders': '''
📝 Є 3 способи <b>замовити пісню:</b>

- Натиснути на кнопку <code>Замовити пісню</code> та увести назву, бот вибере найімовірніший варіант

- Використовувати інлайн режим пошуку (увести <code>@kpiradio_bot</code> або натиснути на відповідну кнопку).
    У цьому випадку ти можеш вибрати із 50 знайдених варіантів з можливістю спочатку послухати

- Завантажити або надіслати боту бажану пісню
Після цього необхідно вибрати день та час для замовлення.''',

    'criteria': '''
✅ Вітаються нейтральні, спокійні пісні, які не відволікатимуть від навчального процесу.

⚠️ Будь ласка, не замовляй багато пісень одразу. Не замовляй більше 1 треку на етер, окрім вечірнього.

❌ Відхиляються:
    - биті треки
    - треки довжиною менше 1 хвилини
    - треки довжиною понад 6 хвилин, крім вечірнього етеру
    - лайви, ремікси поганої якості
    - двічі та більше замовлений трек на один етер
    - треки з матами, поганим змістом
    - треки з невідповідною назвою
    - не формат радіо (див. нижче)

Скільки людей, стільки та смаків. Але ми найчастіше відхиляємо:
    - російський реп
    - треки з елементами скріму, жорсткого металу
    - гачі, стогін, аніме опенінги
    - кавери (radio tapok)
    - таких виконавців, як Корж, Команда Білоруських та подібні

❗️ Рупора радіо – не колонки у клубі. Памʼятай про це.
️Модератори мають право відхилити ваш трек без пояснення причин.''',

    'playlist': '''
<b>⏭ Плейлист радіо:</b>

- Дізнатися, що грає зараз, грало до цього або буде грати, можна, якщо натиснути на кнопку "<code>Що грає</code>"

- Памʼятаєш дату та час, коли грала пісня, та хочеш її знайти? Можеш знайти її там же — "<code>Що грало?</code>"

- Хочеш дізнатися, що буде грати в майбутньому? "<code>Що гратиме</code>"!

- Замовлення <b>одноразове</b>. Якщо твоя пісня не встигла увійти в етер, <b>перезамов наступного разу</b>.''',

    'feedback': '''
  <b>🖌 Зворотній звʼязок:</b>

- Ти завжди можеш написати команді адмінів, що думаєш про них і про радіо

- Якщо хочеш стати частиною радіо, пиши про це і готуйся до анкет

- Вважаєш щось незручним? Є пропозиції щодо покращення? Не замислюючись, пиши нам.

- У нас є чат @rhub_kpi''',

    'start': 'Вибери тему, що тебе цікавить. (Радимо прочитати все)'
}
