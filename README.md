# RAG-document-chat
RAG система с временной векторной бд. Схема как NotebookLM

# Запуск

1. Вставить в конфиг апи ключ и хост и в .env
2. Ввести в командной строке в директории с проектом docker-compose up --build
3. Перейти на localhost:8000
4. Для нагрузочного теста в content нужно вставить вопрос, в extra body: {session_id : "id сессии"}
