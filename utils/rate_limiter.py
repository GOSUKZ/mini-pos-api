from collections import defaultdict
import time
from fastapi import HTTPException, status

class RateLimiter:
    """
    Простой класс для ограничения скорости запросов.
    Отслеживает количество запросов от каждого пользователя за указанный временной интервал.
    """

    def __init__(self, max_requests: int, time_window: int):
        """
        Инициализирует RateLimiter с указанными параметрами.

        Args:
            max_requests: Максимальное количество запросов, разрешенных в указанный временной интервал
            time_window: Временной интервал в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_counts = defaultdict(list)

    def check_rate_limit(self, user_identifier: str):
        """
        Проверяет, не превышен ли лимит запросов для пользователя.
        Вызывает HTTPException, если лимит превышен.

        Args:
            user_identifier: Идентификатор пользователя (или IP-адрес)
        """
        current_time = time.time()

        # Удаляем устаревшие записи запросов
        self.request_counts[user_identifier] = [
            timestamp for timestamp in self.request_counts[user_identifier]
            if current_time - timestamp < self.time_window
        ]

        # Проверяем количество запросов в текущем окне
        if len(self.request_counts[user_identifier]) >= self.max_requests:
            # Вычисляем время до сброса лимита
            oldest_request = min(self.request_counts[user_identifier]) if self.request_counts[user_identifier] else current_time
            reset_time = oldest_request + self.time_window - current_time

            headers = {
                "X-RateLimit-Limit": str(self.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time)),
            }

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {int(reset_time)} seconds.",
                headers=headers
            )

        # Записываем текущий запрос
        self.request_counts[user_identifier].append(current_time)

        # Возвращаем информацию о лимитах для заголовков
        return {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(self.max_requests - len(self.request_counts[user_identifier])),
            "X-RateLimit-Reset": str(int(self.time_window)),
        }