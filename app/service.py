"""
Базовый класс сервиса и демо-реализация.

Этот файл — ЕДИНСТВЕННОЕ место, которое нужно менять студенту.
Всё остальное (FastAPI, схемы, Docker) работает автоматически.

КАК ПОЛЬЗОВАТЬСЯ:
1. Прочитайте комментарии к ServiceBase — там описаны все методы.
2. Посмотрите на DemoService как на рабочий пример.
3. Создайте свой класс-наследник ServiceBase.
4. Обновите функцию get_service() в конце файла.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import (
    ContentPartImage,
    ContentPartText,
    InfoResponse,
    InputType,
    RunRequest,
    RunResponse,
    Schema,
)


class ServiceBase(ABC):
    """Абстрактный базовый класс для всех сервисов.

    Каждый студент должен унаследовать этот класс и реализовать два метода:
      - get_info() — возвращает тип входных данных сервиса.
      - run()      — основная логика обработки запроса.

    Также доступны вспомогательные методы (helpers):
      - get_text(request)  — извлекает текст из content.
      - get_image(request) — извлекает base64 картинку из content.
    """

    @abstractmethod
    def get_info(self) -> InfoResponse:
        """Вернуть метаданные сервиса.

        input_type определяет, какой контент будет отправлять нагрузочный тест:
          - InputType.TEXT           → content — строка с текстом
          - InputType.IMAGE          → content — список с одной картинкой
          - InputType.TEXT_AND_IMAGE → content — список с текстом и картинкой

        input_schema — JSON Schema для параметров extra_body.
        output_schema — JSON Schema для поля result в ответе.
        """
        ...

    @abstractmethod
    def run(self, request: RunRequest) -> RunResponse:
        """Выполнить основную логику сервиса.

        Аргумент request содержит:
          - request.content    : str | list[ContentPart]
              Строка = обычный текст.
              Список = типизированные части (текст + картинка).
          - request.extra_body : dict
              Дополнительные параметры (temperature, max_tokens, ...).

        Верните RunResponse(status="success", result={...}) или
        RunResponse(status="error", error="описание ошибки").
        """
        ...

    # ------------------------------------------------------------------
    # Helper methods — вспомогательные методы для извлечения данных
    # ------------------------------------------------------------------

    def get_text(self, request: RunRequest) -> str | None:
        """Извлечь текст из content.

        Если content — строка, возвращает её как есть.
        Если content — список, ищет первую часть с type="text".
        Если текст не найден, возвращает None.

        Пример использования:
            text = self.get_text(request)
            if text is None:
                return RunResponse(status="error", error="Текст не передан")

        Args:
            request: объект RunRequest с полем content.

        Returns:
            Строка с текстом или None.
        """
        if isinstance(request.content, str):
            return request.content

        for part in request.content:
            if isinstance(part, ContentPartText):
                return part.text

        return None

    def get_image(self, request: RunRequest) -> str | None:
        """Извлечь base64-кодированную картинку из content.

        Ищет первую часть с type="image" в списке content.
        Если content — строка (текст), возвращает None.

        Пример использования:
            image_b64 = self.get_image(request)
            if image_b64 is None:
                return RunResponse(status="error", error="Картинка не передана")
            image_bytes = base64.b64decode(image_b64)

        Args:
            request: объект RunRequest с полем content.

        Returns:
            Строка с base64-кодированной картинкой или None.
        """
        if isinstance(request.content, str):
            return None

        for part in request.content:
            if isinstance(part, ContentPartImage):
                return part.image

        return None


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  СТУДЕНТУ: Ниже находится демо-сервис. Замените его на свою реализацию.   ║
# ║  1. Напишите свой класс-наследник ServiceBase.                            ║
# ║  2. Обновите функцию get_service() в конце файла.                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


from backend.session_manager import create_session, list_sessions
from backend.rag_pipeline import rag_pipeline


class RAGService(ServiceBase):

    def get_info(self) -> InfoResponse:
        return InfoResponse(
            input_type=InputType.TEXT,
            input_schema=Schema.of(
                session_id=Schema.string("ID сессии (если не указан — создаётся новая)", default=""),
            ),
            output_schema=Schema.of(
                answer=Schema.string("Ответ модели"),
                sources=Schema.array("Источники"),
            ),
        )

    def run(self, request: RunRequest) -> RunResponse:
        try:
            # 1. Извлекаем текст запроса
            text = self.get_text(request)
            if not text:
                return RunResponse(status="error", error="Пустой запрос")

            # 2. Определяем сессию
            session_id = request.extra_body.get("session_id", "")
            if not session_id:
                # Создаём временную сессию
                session_info = create_session("load_test_session")
                session_id = session_info.session_id

            # 3. Выполняем RAG
            result = rag_pipeline(text, session_id)

            return RunResponse(
                status="success",
                result={
                    "answer": result.get("answer", ""),
                    "sources": [
                        {
                            "source_file": src.get("source_file", ""),
                            "score": src.get("score"),
                        }
                        for src in result.get("sources", [])
                    ],
                    "latency_ms": result.get("latency_ms"),
                },
            )

        except ValueError as e:
            # Сессия пустая (нет документов) или другие ошибки валидации
            return RunResponse(status="error", error=str(e))
        except Exception as e:
            return RunResponse(status="error", error=f"Ошибка обработки: {str(e)}")


_service_instance: ServiceBase | None = None


def get_service() -> ServiceBase:
    global _service_instance
    if _service_instance is None:
        _service_instance = RAGService()
    return _service_instance