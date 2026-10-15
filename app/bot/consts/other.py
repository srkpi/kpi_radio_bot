from datetime import timedelta

AVERAGE_SONG_SWITCH_DELAY = 10
WEEKDAYS = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'Пʼятниця', 'Субота', 'Неділя']

# Long ethers keep their queue during an alarm: songs are delayed until the
# all-clear instead of being cancelled. "Long" is the same notion that order_menu
# uses: the evening ether, or any ether longer than LONG_ETHER_DURATION.
EVENING_ETHER_NAME = "Вечірній етер"
LONG_ETHER_DURATION = timedelta(hours=2)
# A queued song that would start later than this after its expected play time
# is cancelled instead of being played.
ALARM_MAX_DELAY = timedelta(minutes=30)
