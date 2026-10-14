from datetime import timedelta

AVERAGE_SONG_SWITCH_DELAY = 10
WEEKDAYS = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'Пʼятниця', 'Субота', 'Неділя']

# Ethers at least this long (the evening ones) keep their queue during an alarm:
# songs are delayed until the all-clear instead of being cancelled.
LONG_ETHER_MIN_DURATION = timedelta(hours=1)
# A queued song that would start later than this after its expected play time
# is cancelled instead of being played.
ALARM_MAX_DELAY = timedelta(minutes=30)
