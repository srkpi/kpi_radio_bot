from datetime import time


WEEKDAY_ETHERS = [
    {"id": 0, "name": "Ранковий етер", "start": time(8, 0), "end": time(8, 30)},
    {"id": 1, "name": "Перша перерва", "start": time(10, 5), "end": time(10, 25)},
    {"id": 2, "name": "Друга перерва", "start": time(12, 00), "end": time(12, 20)},
    {"id": 3, "name": "Третя перерва", "start": time(13, 55), "end": time(14, 15)},
    {"id": 4, "name": "Четверта перерва", "start": time(15, 50), "end": time(16, 10)},
    {"id": 5, "name": "Вечірній етер", "start": time(18, 00), "end": time(22, 00)},
]

WEEKEND_ETHERS = [
    {"id": 6, "name": "Ранковий етер", "start": time(9, 0), "end": time(18, 0)},
    {"id": 7, "name": "Вечірній етер", "start": time(18, 0), "end": time(22, 0)},
]
