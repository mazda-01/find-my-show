# 🎬 Serial Finder Pro (find-my-show)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![Langchain](https://img.shields.io/badge/Langchain-v0.1-green.svg)](https://python.langchain.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Search-purple.svg)](https://qdrant.tech/)

**Serial Finder Pro** — это интеллектуальный помощник для поиска и выбора сериалов, построенный на базе передовых LLM и RAG (Retrieval-Augmented Generation) архитектуры. Приложение не просто ищет проекте по фильтрам, но и понимает контекст, находит похожие сюжеты с помощью продвинутого векторного поиска и выступает в роли эксперта-аналитика.

## 🌟 Ключевые возможности

* **Интеллектуальный поиск**: Быстрый и точный поиск по базе сериалов с учетом сюжета, жанров и рейтинга.
* **Векторные рекомендации (RAG)**: Нахождение похожих сериалов на основе семантической близости описаний сюжетов с использованием `Sentence-Transformers`.
* **Reranking результатов**: Оптимизация поисковой выдачи с помощью алгоритмов Cross-Encoder (`FlashrankRerank`) для максимальной релевантности.
* **Чат с ИИ-Аналитиком**: Встроенный помощник на базе LLM (`Llama-3.3`), который не только советует проекты, но и дает им профессиональную, слегка саркастичную оценку. 
* **Удобный интерфейс**: Интуитивно понятный UI на базе Streamlit с продуманной структурой (разделение на поиск и чат-ассистента).

## 🚀 Используемые технологии

* **Frontend & Backend**: Streamlit, Pandas
* **База данных**: Qdrant (Vector Store для хранения эмбеддингов)
* **LLM & Пайплайны**: 
  * `Langchain` (Оркестрация RAG)
  * `HuggingFaceEmbeddings` (`paraphrase-multilingual-MiniLM-L12-v2` для векторизации описаний)
  * `FlashRank` (Реренжинг ответов для лучшего качества RAG)
  * `ChatGroq` (`llama-3.3-70b-versatile` в качестве генеративной LLM)

## ⚙️ Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone git@github.com:mazda-01/find-my-show.git
cd find-my-show
```

2. Установите зависимости (рекомендуется использовать виртуальное окружение, например Poetry или venv):
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
Создайте файл `.env` в корне проекта и добавьте следующие ключи:
```env
HF_TOKEN="ваш_huggingface_токен"
GROQ_API_KEY="ваш_groq_токен"
QDRANT_URL="url_вашего_qdrant_кластера"
QDRANT_API_KEY="ваш_qdrant_ключ"
```

4. Поместите датасет с сериалами `full_df.csv` в папку `data/`.

5. Запустите приложение:
```bash
streamlit run app.py
```

## 📂 Структура проекта
* `app.py` — Главный файл Streamlit приложения, содержащий UI, подключение моделей и RAG пайплайн.
* `data/` — Директория с данными по сериалам.
* `notebooks/` — Jupyter ноутбуки (EDA, парсинг данных, тесты векторизации).
* `requirements.txt` — Список зависимостей.


