# Rogue-like Game API

## Описание  
Проект представляет собой API для rogue-like игры с аутентификацией, управлением инвентарем, генерацией карты и примитивной боевой системой. Используется FastAPI (бэкенд), SQLite (база данных) и JWT-токены для авторизации.

## Установка и запуск
1. Клонируйте репозиторий:  
git clone https://github.com/dmitry-19/minigame   
2. Перейдите в папку проекта:  
cd minigame
3. Создайте виртуальное окружение:
python -m venv venv 
4. Активируйте виртуальное окружение:  
- Linux/Mac: source venv/bin/activate  
- Windows: venv\Scripts\activate  
5. Установите зависимости:  
pip install -r requirements.txt
6. Запустите сервер:  
 uvicorn app.main:app --reload  
7. Откройте документацию API:  
http://localhost:8000/docs  
8. Фронтенд доступен по адресу:  
http://localhost:8000/static/index.html  

## Тестирование  
1. Запустите тесты из папки `tests`:  
pytest tests/ -v  

## База данных  
- SQLite-файл (`game.db`) создается автоматически при первом запуске.  
- Все таблицы (`User`, `InventoryItem`, `MapTile`, `Mob`) связаны через внешние ключи. 
