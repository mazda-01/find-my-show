import streamlit as st
import pandas as pd
import os
import requests
import random
from PIL import Image
import io
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
import warnings
import re

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="Serial Finder Pro", layout="wide")

# CSS для красивого интерфейса и одинакового размера картинок
st.markdown("""
<style>
    /* Фиксированный размер для всех постеров */
    .stImage img {
        object-fit: cover;
        border-radius: 10px;
        height: 320px !important;
        width: 100% !important;
        border: 1px solid #444;
    }
    /* Стиль контейнера сообщений чата */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Подсветка заголовков карточек */
    .card-title {
        font-size: 16px;
        font-weight: bold;
        margin-top: 5px;
        height: 40px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Загрузка переменных окружения
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not HF_TOKEN or not GROQ_API_KEY:
    st.error("Ошибка: Проверьте HF_TOKEN и GROQ_API_KEY в файле .env")
    st.stop()

# 2. ИНИЦИАЛИЗАЦИЯ МОДЕЛЕЙ
@st.cache_resource
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

embeddings_model = get_embeddings()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=2000)

# 3. ПОДКЛЮЧЕНИЕ К QDRANT
@st.cache_resource
def load_vector_store():
    try:
        client = QdrantClient(
            url=QDRANT_URL, 
            api_key=QDRANT_API_KEY
        )
        # Проверка наличия коллекции
        collections = client.get_collections().collections
        if not any(c.name == "demo_collection" for c in collections):
            st.sidebar.error("Коллекция 'demo_collection' не найдена!")
            return None
        
        return QdrantVectorStore(
            client=client,
            collection_name="demo_collection",
            embedding=embeddings_model
        )
    except Exception as e:
        st.sidebar.error(f"Ошибка Qdrant: {e}")
        return None

vector_store = load_vector_store()

# 4. ДАННЫЕ И RAG
@st.cache_data
def load_df():
    csv_path = "data/full_df.csv"
    if os.path.exists(csv_path):
        data = pd.read_csv(csv_path)
        # Очистка данных: преобразуем год и рейтинг в числа
        data['year'] = pd.to_numeric(data['year'], errors='coerce').fillna(0).astype(int)
        data['rating'] = pd.to_numeric(data['rating'], errors='coerce').fillna(0.0)
        return data
    return pd.DataFrame()

df = load_df()

def format_docs(docs):
    return "\n\n".join([
        f"TITLE: {d.metadata.get('tvshow_title')}\nYEAR: {d.metadata.get('year')}\n"
        f"RATING: {d.metadata.get('rating')}\nGENRES: {d.metadata.get('genres')}\n"
        f"DESCRIPTION: {d.page_content}" for d in docs
    ])

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """Ты эксперт-аналитик рынка сериалов и ТВ-шоу с многолетним опытом и отличным чувством юмора! 🎥
    Твоя задача — проанализировать предоставленные сериалы и дать профессиональную оценку с долей иронии.
    
    ПРАВИЛА ОТВЕТА:
    - Отвечай на том языке, на котором к тебе обратился пользователь (если на русском — отвечай на русском).
    - Проводи глубокий анализ, но с легкой иронией над ТВ-реалиями.
    - Используй сериальные мемы и шутки там, где это уместно.
    - Подмечай забавные особенности (завышенные рейтинги, сюжетные дыры, клише).
    - Структурируй ответ с эмодзи.
    
    Стиль анализа: Юмор должен быть смешным и слегка саркастичным. Цель — сделать анализ интересным!
    
    ОБЯЗАТЕЛЬНО: Сначала напиши свои мысли в тегах <think>...</think>, затем дай итоговый ответ. Используй только предоставленный контекст базы."""),
    ("human", """📺 ДАННЫЕ ДЛЯ АНАЛИЗА:
{context}

🎯 ЗАПРОС НА ЭКСПЕРТИЗУ: {question}""")
])

if vector_store:
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt | llm | StrOutputParser()
    )

# 5. САЙДБАР (ФИЛЬТРЫ)
st.sidebar.title("⚙️ Настройки поиска")
if not df.empty:
    min_rating = st.sidebar.slider("Минимальный рейтинг", 0.0, 10.0, 5.0)
    
    all_genres = set()
    df['genres'].dropna().str.split(', ').apply(all_genres.update)
    selected_genres = st.sidebar.multiselect("Жанры", sorted(list(all_genres)))

    # Применение фильтрации
    filtered_df = df[df['rating'] >= min_rating]
    if selected_genres:
        filtered_df = filtered_df[filtered_df['genres'].apply(lambda x: any(g in str(x) for g in selected_genres))]
else:
    filtered_df = df

# 6. ИНТЕРФЕЙС ТАБОВ
tab1, tab2 = st.tabs(["🔍 Поиск и Рекомендации", "💬 Аналитик"])

with tab1:
    search_query = st.text_input("Введите название для поиска:")
    
    if search_query and not df.empty:
        # Поиск по названию
        matches = df[df['tvshow_title'].str.contains(search_query, case=False, na=False)].copy()
        
        if not matches.empty:
            matches['display_name'] = matches.apply(lambda x: f"{x['tvshow_title']} ({x['year']}) ⭐ {x['rating']}", axis=1)
            selected = st.selectbox("Найдено несколько вариантов, выберите один:", matches['display_name'].tolist())
            target_row = matches[matches['display_name'] == selected].iloc[0]

            # Отображение выбранного сериала
            st.divider()
            col_img, col_info = st.columns([1, 3])
            with col_img:
                st.image(target_row['image_url'] if pd.notnull(target_row['image_url']) else "https://via.placeholder.com/300x450")
            with col_info:
                st.header(target_row['tvshow_title'])
                st.subheader(f"📅 {target_row['year']} | ⭐ {target_row['rating']}")
                st.write(f"🎭 **Жанры:** {target_row['genres']}")
                st.write(f"📖 **Сюжет:** {target_row['description']}")

            # Похожие по сюжету (Векторный поиск)
            st.divider()
            # Внутри tab1, там где поиск похожих:
            if vector_store:
                with st.spinner("Поиск по векторам..."):
                    # Используем описание как запрос
                    search_text = str(target_row['description'])
                    
                    # Делаем поиск
                    try:
                        hits = vector_store.similarity_search(search_text, k=6)
                        
                        if len(hits) <= 1:
                            st.info("Похожих сериалов не найдено (база вернула только оригинал).")
                        else:
                            st.subheader("Похожие сюжеты:")
                            cols = st.columns(5)
                            idx = 0
                            for hit in hits:
                                m = hit.metadata
                                # Сравниваем названия, чтобы не дублировать главный результат
                                if m.get('tvshow_title') == target_row['tvshow_title']:
                                    continue
                                
                                if idx < 5:
                                    with cols[idx]:
                                        st.image(m.get('image_url', "https://via.placeholder.com/150"), use_container_width=True)
                                        st.markdown(f"**{m.get('tvshow_title')}**")
                                        st.caption(f"{m.get('year')} | ⭐ {m.get('rating')}")
                                    idx += 1
                    except Exception as e:
                        st.error(f"Ошибка поиска: {e}")
        else:
            st.info("Не найдено! Названия на английском языке.")
                
    # Блок рекомендаций (внизу страницы)
    st.divider()
    st.subheader("🎲 Случайные рекомендации (с учетом фильтров)")
    if not filtered_df.empty:
        # Берем 10 штук, чтобы получилось ровно 2 ряда по 5
        n_to_show = min(10, len(filtered_df))
        rec_list = filtered_df.sample(n_to_show)
        
        # Создаем 5 колонок ОДИН раз
        cols_rec = st.columns(5)
        
        for i, (_, row) in enumerate(rec_list.iterrows()):
            # Оператор % 5 гарантирует, что мы всегда попадем в одну из 5 колонок
            with cols_rec[i % 5]:
                img_url = row['image_url'] if pd.notnull(row['image_url']) else "https://via.placeholder.com/300x450"
                st.image(img_url)
                # Используем HTML для ограничения высоты текста, чтобы карточки были ровными
                st.markdown(f"""
                    <div style="height: 45px; overflow: hidden; line-height: 1.2; margin-top: 5px;">
                        <b>{row['tvshow_title']}</b>
                    </div>
                """, unsafe_allow_html=True)
                st.caption(f"📅 {row['year']} | ⭐ {row['rating']}")
    else:
        st.warning("По вашим фильтрам ничего не найдено.")

with tab2:
    if vector_store is None:
        st.error("База данных не подключена")
    else:
        chat_container = st.container()
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    content = msg["content"]
                    if "<think>" in content:
                        parts = re.split(r"<think>(.*?)</think>", content, flags=re.DOTALL)
                        if len(parts) > 2:
                            with st.expander("🤔 Ход мыслей аналитика"):
                                st.info(parts[1].strip())
                            st.markdown(parts[2].strip())
                        else: st.markdown(content)
                    else: st.markdown(content)

        if prompt := st.chat_input("Спроси аналитика о любом сериале..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Анализирую базу данных..."):
                        full_response = rag_chain.invoke(prompt)
                        if "<think>" in full_response:
                            parts = re.split(r"<think>(.*?)</think>", full_response, flags=re.DOTALL)
                            if len(parts) > 2:
                                with st.expander("🤔 Ход мыслей аналитика", expanded=True):
                                    st.info(parts[1].strip())
                                st.markdown(parts[2].strip())
                            else: st.markdown(full_response)
                        else: st.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})