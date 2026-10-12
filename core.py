# Импорт стандартных библиотек
import json
import os
import random
import re
import string
import time
import warnings
from datetime import datetime, timedelta
from io import BytesIO
import fake_useragent
import numpy as np

# Импорт сторонних библиотек
import openai
import requests
import html
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from telebot import formatting
from unidecode import unidecode

# Импорт локальных модулей
from config import FRONT_PATH, MODELS_PATH, logger, log_stream, breaking_prompt, general_prompt, chat_ctm_main, \
    STORAGE_PATH

# Подавление лишних предупреждений
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*Could not load dynamic library 'libcudart.so.11.0'.*")


# Функция проверки времени по расписанию
def check_schedule(freq_weekday, freq_weekend, pub_minute=0, utc_offset=0):
    """
    Проверяет текущее время и сверяет с заданным расписанием публикации

    :param freq_weekday: Частота публикаций по будням в часах
    :param freq_weekend: Частота публикаций по выходным в часах
    :param pub_minute: Минута публикации
    :param utc_offset: Отклонение от времени UTC в часах
    :return: True если текущее время соответствует расписанию, False если не соответствует
    """

    # Получаем текущую дату, время, день недели, часы и минуты
    now = datetime.utcnow() + timedelta(hours=utc_offset)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    # Проверка минут на публикацию - True если время 00 с погрешностью 4 минуты
    check_minute = True if (minute - pub_minute) in range(0, 6) else False

    # Проверка часа публикации с учётом дня недели
    if weekday < 5:  # будни
        result = (check_minute and (hour % freq_weekday == 0))
    else:  # выходные
        result = (check_minute and (hour % freq_weekend == 0))

    if result:
        logger.info(f"Время запуска: {now} - соответствует расписанию публикации")
    else:
        logger.info(f"Время запуска: {now} - не соответствует расписанию публикации")

    return result


# Функция для отправки логов в ТГ
def send_logs(chat, bot, mode='errors'):
    """
    Отправляет логи в Telegram в зависимости от режима:
    - 'always': всегда отправлять лог
    - 'errors': отправить лог, только если были ошибки
    - 'notifications': отправить короткое сообщение, если были ошибки

    :param chat: чат
    :param bot: бот
    :param mode: режим отправки логов ('always', 'errors', 'notifications')
    """

    # Записываем логи в переменную
    log_text = log_stream.getvalue()

    # Определяем ошибки
    has_errors = "ERROR" in log_text or "CRITICAL" in log_text

    # Текущее дата и время для логов
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Если режим "always" - отправляем файл с логами и выводим сообщение были ли ошибки
    if mode == 'always':
        log_file = BytesIO()
        log_file.name = "logs.txt"
        log_file.write(log_text.encode('utf-8'))
        log_file.seek(0)
        caption = (
            f"✅ Скрипт выполнен без ошибок | {timestamp}"
            if not has_errors else
            f"⚠️ Скрипт выполнен. Были ошибки | {timestamp}"
        )
        bot.send_document(chat['id'], document=log_file, caption=caption)

    # Если режим "errors" - отправляем лог и сообщение только если были ошибки
    elif mode == 'errors':
        if has_errors:
            log_file = BytesIO()
            log_file.name = "logs.txt"
            log_file.write(log_text.encode('utf-8'))
            log_file.seek(0)
            bot.send_document(chat['id'], document=log_file,
                              caption=f"❗ Ошибки при выполнении скрипта {timestamp}. Смотри логи")

    # Если режим "notifications" - отправляем только сообщение если были ошибки
    elif mode == 'notifications':
        if has_errors:
            bot.send_message(chat['id'], f"❗ Были ошибки при выполнении скрипта {timestamp}, проверь логи")

    else:
        logger.warning(f"Неизвестный режим отправки логов: {mode}")


# Функция-декоратор try-except
def safe_extract(func):
    """
    Декоратор, который оборачивает любую функцию и возвращает None если есть любая ошибка.

    :param func: Функция
    :return: None в случае любой ошибки
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return None

    return wrapper


# Функция получения списка готовых новостей из одного ресурса в виде словарей
def news_to_post(source, news_limit=20):
    """
    Принимает на вход словарь ресурса и возвращает список всех новостей на странице ресурса
    :param source: Словарь ресурса
    :param news_limit: Количество новостей для парсинга
    :return: Список словарей всех новостей из указанного ресурса
    """
    # Инициализация user_agent и запрос
    ua = fake_useragent.UserAgent()
    headers = {'User-Agent': ua.random}
    response = requests.get(source['url'], headers=headers)
    bs = BeautifulSoup(response.text, "lxml")

    # Получение списка всех новостей
    bs_items = bs.find_all(source['tag'], source['attrs'])

    # Получаем безопасную функцию, обернув в декоратор
    extract_func = safe_extract(source['extract_func'])

    # Создаём список из news_limit последних новостей
    one_source_news = []
    for item in bs_items:
        if len(one_source_news) >= news_limit:
            break
        news = extract_func(item)
        if news is not None and news.get('date') is not None:
            one_source_news.append(news)

    return one_source_news


# Функция получения новостей за последние n дней
def get_newest_news(news_list, days=2):
    """
    Отбирает новости за последние `days` дней (включая сегодня).

    :param news_list: Список словарей новостей
    :param days: Количество дней для отбора, включая сегодня
    """

    # Рассчитываем минимальную дату относительно сегодня
    today = datetime.today().date()
    min_date = today - timedelta(days=days - 1)

    # Создаём новый пустой список для формирования подходящих новостей
    newest_news = []

    # Цикл для каждой новости из изначального списка
    for news_item in news_list:
        # Если в новости есть ключ date и он None - логируем и пропускаем
        if 'date' in news_item and news_item['date'] is None:
            logger.warning(
                f"В новости {news_item.get('source_link')} отсутствует дата (None)"
            )
            continue
        # Получаем дату из новости
        news_date_str = news_item.get('date')
        # Если в новости нет ключа date или пустая строка - молча пропускаем такую новость
        if not news_date_str:
            continue
        try:
            # Сохраняем в переменную дату из новости в виде объекта datetime
            news_date = datetime.strptime(news_date_str, "%d.%m.%Y").date()
        except ValueError:
            # Если формат даты не соответствует ожидаемому, логируем и пропускаем
            logger.warning(f"Неверный формат даты в новости {news_item.get('source_link')}: {news_date_str}")
            continue

        # Если дата в промежутке от минимальной даты до сегодня, добавляем новость в список
        if min_date <= news_date <= today:
            newest_news.append(news_item)

    logger.info(f"{len(newest_news)} новостей прошли отбор по дате за последние {days} дней")

    return newest_news


# Функция отбора случайной новости
def get_random_news(old_news, new_news):
    """
    Возвращает случайную новость из списка.
    :param old_news: Список опубликованных новостей (не используется, передаётся для совместимости)
    :param new_news: Список новых новостей
    :return: Список, содержащий одну случайную новость
    """

    logger.info(f"Возвращается рандомная новость")
    return [random.choice(new_news)] if new_news else []


# Функция нормализации текста
def normalize_text(text: str) -> str:
    # Вернём пустую строку если нет текста
    if not text:
        return ""
    # Приводим к нижнему регистру
    text = text.lower()
    # Убираем пунктуацию
    text = text.translate(str.maketrans("", "", string.punctuation))
    # Убираем лишние пробелы
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Функция дедубликации на основе косинусного сходства
def deduplicate_news(old_news, new_news, threshold=0.5):
    """
    Функция дедубликации новых новостей относительно старых
    на основе раздельного косинусного сходства заголовков и summary.

    :param old_news: Список словарей старых новостей
    :param new_news: Список словарей новых новостей
    :param threshold: Порог итогового косинусного сходства
    :return: Список уникальных новостей
    """
    logger.info("Запущена дедубликация новостей")

    if not old_news:
        logger.info(
            "Список старых новостей пуст, возвращается полный список новых новостей"
        )
        return new_news

    # Нормализуем заголовки
    old_headers = [
        normalize_text(item.get('header'))
        for item in old_news
    ]

    new_headers = [
        normalize_text(item.get('header'))
        for item in new_news
    ]

    # Нормализуем summary
    old_summaries = [
        normalize_text(item.get('summary')) if item.get('summary') else ''
        for item in old_news
    ]

    new_summaries = [
        normalize_text(item.get('summary')) if item.get('summary') else ''
        for item in new_news
    ]

    logger.info("  • Заголовки и summary нормализованы")

    # Обучаем отдельные TF-IDF на заголовках и summary
    header_vectorizer = TfidfVectorizer(stop_words="english")
    summary_vectorizer = TfidfVectorizer(stop_words="english")

    all_headers = old_headers + new_headers
    all_summaries = old_summaries + new_summaries

    header_vectorizer.fit(all_headers)

    # Если summary отсутствуют у всех новостей, не обучаем vectorizer
    if any(all_summaries):
        summary_vectorizer.fit(all_summaries)

    tfidf_old_headers = header_vectorizer.transform(old_headers)
    tfidf_new_headers = header_vectorizer.transform(new_headers)

    # Считаем сходство summary только если они есть
    if any(all_summaries):
        tfidf_old_summaries = summary_vectorizer.transform(old_summaries)
        tfidf_new_summaries = summary_vectorizer.transform(new_summaries)
    else:
        tfidf_old_summaries = None
        tfidf_new_summaries = None

    logger.info("  • TF-IDF заголовков и summary обучен, тексты векторизованы")

    # Косинусное сходство заголовков
    header_similarities = cosine_similarity(
        tfidf_new_headers,
        tfidf_old_headers
    )

    # Косинусное сходство summary
    if tfidf_old_summaries is not None:
        summary_similarities = cosine_similarity(
            tfidf_new_summaries,
            tfidf_old_summaries
        )
    else:
        summary_similarities = None

    logger.info(
        "  • Косинусное сходство новых новостей со старыми оценено"
    )

    # Списки для уникальных новостей и дублей
    unique_new_news, duplicates = [], []

    # Вес заголовка и summary
    header_weight = 0.7
    summary_weight = 0.3

    # Порог для практически идентичных заголовков
    header_duplicate_threshold = 0.85

    # Составляем списки уникальных новостей и дублей
    for idx, header_sim_row in enumerate(header_similarities):

        # Максимальное сходство заголовка новой новости
        # с заголовками старых новостей
        header_score = header_sim_row.max()

        # Максимальное сходство summary новой новости
        # с summary старых новостей
        if summary_similarities is not None:
            summary_score = summary_similarities[idx].max()
        else:
            summary_score = 0

        # Итоговый score с большим весом заголовка
        combined_score = (
            header_weight * header_score
            + summary_weight * summary_score
        )

        # Новость считается дублем, если:
        # 1. заголовок практически идентичен
        # ИЛИ
        # 2. итоговое сходство превышает заданный threshold
        if (
            header_score >= header_duplicate_threshold
            or combined_score >= threshold
        ):
            duplicates.append((combined_score, new_news[idx]))
        else:
            unique_new_news.append((combined_score, new_news[idx]))

    # Логируем результаты
    logger.info(f"  • {len(unique_new_news)} новостей прошли отбор")
    logger.info(f"  • {len(duplicates)} новостей не прошли отбор")

    if not unique_new_news:
        logger.info(
            "Все новые новости оказались дублями, возвращается пустой список"
        )

    # Убираем коэффициенты score и возвращаем только новости
    unique_new_news = [item for _, item in unique_new_news]

    return unique_new_news


# Функция отбора новостей через GPT
def gpt_review(old_news, new_news, prompt, allow_none=False):
    """
    Функция для отбора одной новости по заданным критериям через GPT.
    :param old_news: Список ранее опубликованных новостей
    :param new_news: Список новостей, которые ещё не были опубликованы
    :param prompt: Промпт для отбора
    :param allow_none: Параметр разрешения возврата None
    :return: Отобранный по критериям список, содержащий только одну новость
    """

    # Лог - информирование об используемой функции отбора
    logger.info(f"Работает функция отбора новости через GPT")

    try:
        # Формируем текст для отправки в GPT
        new_news_text = "\n".join(
            [f"{i + 1}: {news['header']} (source: {news['source_name']})"
             for i, news in enumerate(new_news)])

        old_news_text = "\n".join(
            [f"{i + 1}: {news['header']} (source: {news['source_name']})"
             for i, news in enumerate(old_news)])

        full_prompt = prompt.format(
            new_news_text=new_news_text,
            old_news_text=old_news_text
        )

        # Запрос к GPT
        response_gpt = openai.ChatCompletion.create(
            model="gpt-6-luna",
            messages=[
                {
                    "role": "system",
                    "content": "You are the editor of a global music magazine and a professional curator of news for "
                               "an international Telegram music channel."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            reasoning_effort="low",
            max_completion_tokens=100
        )

        logger.info(f'Запрос GPT отправлен: \n{full_prompt}')

        # Извлекаем результат
        response_text = response_gpt.choices[0].message['content']

        # Возвращаем пустой список, если GPT вернул пустой ответ
        if not response_text:
            logger.info("GPT не вернул номер новости (нет подходящей новости)")
            return [] if allow_none else get_random_news(old_news, new_news)

        # Возвращаем номер новости, если ответ не пуст
        selected_news_number = response_text.strip()
        logger.info(f'GPT вернул номер новости для публикации: {selected_news_number}')

        # Преобразуем номер в индекс (чтобы учесть, что индексы в Python начинаются с 0)
        try:
            selected_news_index = int(selected_news_number) - 1
            if 0 <= selected_news_index < len(new_news):
                selected_news = [new_news[selected_news_index]]
                logger.info(f'Новость в списке найдена')
                return selected_news
            else:
                logger.warning(f"Новость не найдена: {response_text}")
                return None if allow_none else get_random_news(old_news, new_news)
        except ValueError:
            logger.error(
                f"Ошибка преобразования номера новости: {response_text}")
            return None if allow_none else get_random_news(old_news, new_news)

    except Exception as e:
        logger.error(f"Ошибка при отборе новостей через GPT: {e}")
        return None if allow_none else get_random_news(old_news, new_news)


# Функция фильтрации breaking news по ключевым словам
def filter_breaking_news(news_list, similarity_threshold=0.4):
    """
    Фильтрует новости по косинусному сходству с центроидами категорий.

    :param news_list: Список словарей новостей
    :param similarity_threshold: Порог косинусного сходства для отбора
    :return: Список новостей, у которых есть сходство с центроидом >= порога
    """
    logger.info("Фильтрация списка новостей по косинусному сходству с центроидами запущена")

    # Загружаем центроиды категорий
    with open(os.path.join(STORAGE_PATH, 'centroids_bn.json'), 'r', encoding='utf-8') as f:
        centroids = json.load(f)

    # Загружаем модель
    model = SentenceTransformer(os.path.join(MODELS_PATH, 'all-MiniLM-L6-v2'), device='cpu')

    selected_news = []

    logger.info(f"Оценка косинусного сходства эмбеддингов новостей с центроидами категорий:")

    for news in news_list:
        text = f"{news.get('header', '')}. {news.get('summary', '')}"
        embedding = model.encode(text, normalize_embeddings=True).reshape(1, -1)

        # Считаем сходство со всеми категориями
        similarities = {}
        for category, centroid in centroids.items():
            centroid_vec = np.array(centroid).reshape(1, -1)
            similarity = cosine_similarity(embedding, centroid_vec)[0][0]
            similarities[category] = similarity

        # Логируем сходство для каждой новости
        sim_str = ", ".join([f"\n  • {cat}: {sim:.3f}" for cat, sim in similarities.items()])
        logger.info(f"\nНовость: '{news.get('header', '')}': {sim_str}")

        # Если есть хотя бы одно сходство >= threshold, добавляем в результат
        if any(sim >= similarity_threshold for sim in similarities.values()):
            selected_news.append(news)

    logger.info(f"Отобрано {len(selected_news)} новостей с сходством >= {similarity_threshold}")

    return selected_news


# Функция для дедубликации ресурсов
def deduplicate_sources(old_news, new_news, last_n):
    """
    Исключает из new_news новости источников, что и последние N опубликованных.

    :param old_news: Список ранее опубликованных новостей
    :param new_news: Список неопубликованных новостей
    :param last_n: Количество последних новостей для анализа источников
    :return: Отфильтрованный список new_news
    """

    logger.info(f"Запущена фильтрация ресурсов {len(new_news)} новых новостей по последним {last_n}")

    # Если один из списков оказался пуст, возвращаем new_news как есть
    if not old_news or not new_news:
        logger.info("Один из списков пуст - невозможно сравнить, возвращается исходный список")
        return new_news

    # Если количество новостей не задано, возвращается исходный список
    if not last_n:
        logger.info(f"Количество новостей не задано - возвращается исходный список")
        return new_news

    # Определяем последние источники
    last_sources = {news['source_name'] for news in old_news[-last_n:] if news.get('source_name')}
    logger.info(f"Источники последних {last_n} новостей: {', '.join(last_sources)}")

    # Фильтруем новые новости
    filtered_news = [n for n in new_news if n.get('source_name') not in last_sources]
    logger.info(f"После фильтрации осталось {len(filtered_news)} из {len(new_news)} новостей")

    # Если после фильтрации ничего не осталось — возвращаем исходный список
    if not filtered_news:
        logger.info("После фильтрации не осталось новостей, возвращается исходный список")
        return new_news

    return filtered_news


# Функция отбора general news через GPT
def review_general(old_news, new_news):
    """
    Функция для отбора general news через GPT. Использует базовую функцию gpt_review с промптом для general news.

    :param old_news: Список опубликованных новостей
    :param new_news: Список неопубликованных новостей
    :return: Список из одной новости или пустой список
    """

    # Дедубликация ресурсов
    new_news = deduplicate_sources(old_news, new_news, 2)

    # Отбор через GPT
    one_general_news = gpt_review(old_news, new_news, general_prompt, allow_none=False)

    return one_general_news


# Функция отбора breaking news через GPT
def review_breaking(old_news, new_news):
    """
    Функция для отбора breaking news через GPT. Фильтрует новости по ключевым словам, затем передаёт GPT.

    :param old_news: Список опубликованных новостей
    :param new_news: Список неопубликованных новостей
    :return: Список из одной новости или пустой список
    """
    breaking_news = filter_breaking_news(new_news, 0.3)

    if breaking_news:
        one_breaking_news = gpt_review(old_news, breaking_news, breaking_prompt, allow_none=True)
        return one_breaking_news or []
    else:
        return []


# Функция разделения и очистки текста
def clean_text(text, del_prefix=False, del_junk=False, add_dot=False):
    """
    Функция очистки текста

    :param text: Текст
    :param del_prefix: Разделяет текст, удаляя левую часть, включая разделитель
    :param del_junk: Удаляет мусорные символы
    :param add_dot: Добавляет точку, если в конце нет знака препинания
    :return: Обработанный текст без лишних символов
    """

    # Проверяем на наличие текста
    if not text:
        return ''

    # Преобразование html-сущностей в символы
    text = html.unescape(text)

    # Задаём список разделителей
    separators = [
        'photo credit:',
        'credit:',
        'photo by:',
        'photo by',
        'photo:',
        'cover:',
        'graphic by',
        'artwork by',
        'photographed by',
        'credits:',
        'credit -',
        'courtesy of',
        'courtesy',
        'source:',
        '(',
        'photograph:',
        '2025',
        '2026',
        'Composite:',
        'Portraits:'
    ]

    # Задаём список мусорных символов для удаления
    junk = [
        '\n',
        '\t',
        'Read More...',
        '\x95 ',
        '*',
        '© '
    ]

    # Удаление левой части текста, включая разделитель
    if del_prefix:

        # Компилируем паттерн для всех сепараторов, с экранированием и игнорированием регистра
        pattern = re.compile('|'.join(re.escape(sep) for sep in separators), flags=re.IGNORECASE)

        # Делим текст по разделителям, оставляя правую часть
        text = pattern.split(text)[-1].strip() if pattern.search(text) else text

        # Специальный случай: если разделитель был '(', удалим закрывающую скобку справа
        if '(' in separators and ')' in text:
            text = text.replace(')', '', 1)

    # Удаление мусорных символов
    if del_junk:
        for j in junk:
            text = text.replace(j, '')

    # Добавление точки, если в конце текста нет знаков препинания
    if add_dot:

        # Удаляем лишние пробелы
        text = text.strip()

        # Определяем какие знаки будем считать закрывающими предложение
        end_punctuations = {'.', '!', '?', '…', '...'}
        closing_chars = {'"', "'", '”', '’', '»'}

        # Берём последний символ или предпоследний, если последний кавычка
        if text:
            if text[-1] in closing_chars:
                if len(text) > 1 and text[-2] not in end_punctuations:
                    # Вставляем точку перед закрывающей кавычкой
                    text = text[:-1] + '.' + text[-1]
            elif text[-1] not in end_punctuations:
                text += '.'

    return text


# Функция перевода через chatGPT
def translate_with_gpt(text):
    """
    Принимает на вход текст и переводит его с помощью чата GPT
    :param text: Текст
    :return: Переведённый текст
    """

    try:
        response_gpt = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты профессиональный переводчик."},
                {"role": "user", "content": f"Упрости, переформулируй и переведи следующий текст на русский язык "
                                            f"в журналистском стиле, "
                                            f"если в тексте используются кавычки, заменяй их на кавычки-ёлочки: {text}"}
            ],
            max_tokens=1000
        )
        translated_text = response_gpt.choices[0].message['content']
        logger.info(f"Новость успешно переведена.")
        return translated_text.strip()
    except Exception as e:
        logger.error(f"Ошибка перевода через GPT: {e}")
        return text  # Возвращает оригинальный текст в случае ошибки


# Функция для составления сообщения
def construct_message(title, summary, source_name, source_link, chat_link, chat_slogan):
    """
    Принимает на вход ссылки и текст для публикации и возвращает сформированное сообщение для телеграм.
    :param title: Заголовок поста
    :param summary: Лид поста (саммари)
    :param source_name: Название ресурса
    :param source_link: Ссылка на статью
    :param chat_link: Ссылка на канал (чат)
    :param chat_slogan: Слоган чата
    :return: Пост в формате сообщения в ТГ
    """

    # Очищаем заголовок и саммари от мусорных символов
    title = clean_text(title, del_junk=True)
    summary = clean_text(summary, del_junk=True, add_dot=True)

    # Форматируем caption
    caption = f"{formatting.hbold(title)}\n\n"  # Жирный заголовок, два отступа
    caption += f"{summary} More: {formatting.hlink(source_name, source_link)}\n\n" \
        if summary else ''  # Добавляем саммари если есть, два отступа
    caption += f"•••\n{formatting.hlink(chat_slogan, chat_link)}"  # Добавляем ссылки в подвал сообщения

    return caption


# Функция для создания фото с указанием правообладателей
def add_photo_credit(image_url, photo_credit, target_size=1200, max_line_length=75, shadow_offset=(2, 2)):
    """
    Принимает на вход ссылку на изображение, подпись и возвращает новое изображение с подписью.
    Разбивает текст на две строки, если длина текста превышает max_line_length.
    Добавляет тень для текста.

    :param image_url: Ссылка на исходную картинку
    :param photo_credit: Текст для подписи
    :param target_size: Размер меньшей стороны картинки
    :param max_line_length: Максимальная длина строки
    :param shadow_offset: Смещение тени относительно основного текста
    :return: Новое изображение с заданным размером и подписью
    """
    if not image_url or not photo_credit:
        logger.info("Нет фото или авторства фото - изображение не сформировано")
        return None

    try:
        # Загрузка изображения
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0.0.0 Safari/537.36"
            ),
            "Accept": "image/jpeg,image/png,image/webp,image/*;q=0.8",
        }

        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()

        if not response.headers.get("Content-Type", "").startswith("image/"):
            logger.error(f"Ссылка не вернула изображение: {response.headers.get('Content-Type')}")
            return None

        image = Image.open(BytesIO(response.content))

        # Убедимся, что изображение находится в режиме RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Преобразование изображения с сохранением пропорций
        if image.width > image.height:
            new_height = target_size
            new_width = int((new_height / image.height) * image.width)
        else:
            new_width = target_size
            new_height = int((new_width / image.width) * image.height)

        # Масштабирование изображения
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Добавление текста "Photo Credit:"
        photo_credit = clean_text(photo_credit, del_prefix=True,
                                  del_junk=True)  # Разделяем и очищаем от лишних символов
        credit_text = "Credit: " + unidecode(photo_credit)  # Преобразуем в стандартную латиницу и добавляем "Credit:"

        # Разбиение текста на несколько строк, если необходимо
        lines = []
        current_line = ""
        for word in credit_text.split():
            if len(current_line + " " + word) <= max_line_length:
                current_line += (" " + word if current_line else word)
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Настройки для текста
        draw = ImageDraw.Draw(image)
        font_size = max(10, image.width // 40)  # Размер шрифта зависит от ширины изображения
        font = ImageFont.truetype(os.path.join(FRONT_PATH, 'mandali.ttf'), font_size)  # Используем стандартный шрифт

        # Определение размера текста
        text_width = 0
        text_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = max(text_width, bbox[2] - bbox[0])
            text_height += bbox[3] - bbox[1] + 5  # Добавляем небольшой отступ между строками

        # Определение позиции текста
        x = image.width - text_width - 20
        y = image.height - text_height - 60

        # Рисуем тень текста (черный текст с небольшим смещением)
        for i, line in enumerate(lines):
            shadow_x = x + shadow_offset[0]
            shadow_y = y + i * (font_size + 5) + shadow_offset[1]
            draw.text((shadow_x, shadow_y), line, font=font, fill="black")

        # Рисуем основной текст (серым цветом)
        for i, line in enumerate(lines):
            draw.text((x, y + i * (font_size + 5)), line, font=font, fill=(230, 230, 230))

        # Сохранение изображения в память
        output = BytesIO()
        image.save(output, format="JPEG")
        output.seek(0)
        return output

    except Exception as e:
        logger.error(f"Ошибка при добавлении подписи на фото: {e}")
        return None


# Функция извлечения новостей в зависимости ит заданного типа ресурса
def get_news_from_sources(sources, news_limit=None):
    """
    Принимает на вход список ресурсов или путь к хранилищу json и возвращает список новостей

    :param sources: Список ресурсов для парсинга или путь к хранилищу
    :param news_limit: Количество новостей из каждого ресурса
    :return: список новостей
    """
    # Список всех новостей
    all_news = []

    # Если ресурс задан как список источников, парсим
    if isinstance(sources, list):
        logger.info("Ресурс - список источников. Парсинг:")

        for source in sources:
            news_list = news_to_post(source, news_limit)
            logger.info(f"  • {source['name']} → {len(news_list)} новостей")
            all_news.extend(news_list)
        all_news = [item for item in all_news if item]  # Удаляем None если есть

        return all_news

    # Если ресурс задан как путь к хранилищу, берём новости из json этого хранилища
    elif isinstance(sources, str) and os.path.isfile(sources):
        logger.info(f"Ресурс - путь к хранилищу. Чтение из хранилища {sources.split('data')[-1]}")
        with open(sources, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Группируем по источнику и берём последние news_limit новостей если он задан
            if news_limit:
                grouped = {}
                for item in data:
                    grouped.setdefault(item.get("source_name"), []).append(item)
                for items in grouped.values():
                    all_news.extend(items[-news_limit:])
            else:
                all_news.extend(data)

        # Удаляем из списка None и новости без даты
        all_news = [item for item in all_news if item and item.get("date")]

        return all_news

    else:
        logger.error("Неправильный формат 'sources'")
        return []


# Функция загрузки списка новостей из хранилища
def load_storage(storage_path):
    """
    Принимает на вход путь к хранилищу и возвращает список новостей из него

    :param storage_path: Путь к хранилищу
    :return: Список новостей из хранилища
    """
    if os.path.exists(storage_path) and os.path.getsize(storage_path) > 0:
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [item for item in data if item.get("date")]
    return []


# Функция создания уникальных идентификаторов новостей по заголовку и ссылке
def build_news_keys(news_list):
    """
    Принимает список полных новостей и создаёт из него список идентификаторов по ссылкам
    для дальнейшей дедубликации

    :param news_list: Список новостей
    :return: Список уникальных идентификаторов
    """
    return {news["source_link"] for news in news_list}


# Функция отправки новости в чат
def send_news_item(bot, chat_id, caption, image_url, photo_credit=''):
    """
    Отправляет новость указанным ботом в указанный чат с изображением и текстом

    :param bot: Объект бота из Telebot
    :param chat_id: id чата
    :param caption: Сообщение
    :param image_url: Ссылка ни изображение
    :param photo_credit: Текст для фото кредит
    :return: None
    """

    if image_url:
        modified_image = add_photo_credit(image_url, photo_credit)
        if modified_image:
            bot.send_photo(chat_id=chat_id, photo=modified_image, caption=caption, timeout=120)
            return  # Выходим из функции после отправки фото
    bot.send_message(chat_id=chat_id, text=caption, timeout=120)
    logger.info("Фото отсутствует - отправлен текст.")


# Функция перезаписи хранилища новым списком
def update_news_storage(storage_path, news_list, limit=1000):
    """Перезаписывает хранилище новостей, оставляя только Х последних элементов

    :param storage_path: Путь к файлу хранилища
    :param news_list: Список новостей для сохранения
    :param limit: Лимит элементов для сохранения
    :return: Обновлённое хранилище новостей
    """
    with open(storage_path, 'w', encoding='utf-8') as f:
        json.dump(news_list[-limit:], f, ensure_ascii=False, indent=4)


# Функция для отправки одной новости
def send_one_news(caption, item, bot, chat, storage_news, max_storage=800, retries=3):
    """
    Отправляет одну новость в чат с повторными попытками.
    При успехе добавляет новость в хранилище и обновляет его.

    :param caption: Пост для телеграм
    :param item: Словарь новости
    :param bot: Объект бота
    :param chat: Словарь чата
    :param storage_news: Список ранее опубликованных новостей
    :param max_storage: Максимальное количество новостей в хранилище
    :param retries: Количество попыток отправки
    :return: True если отправка успешна, иначе False
    """

    # Отправка новости с повторными попытками в случае ошибки
    for attempt in range(1, retries + 1):
        try:
            # Попытка отправки боту для публикации
            send_news_item(
                bot,
                chat_id=chat['id'],
                caption=caption,
                image_url=item.get('image_url'),
                photo_credit=item.get('photo_credit', '')
            )

            # Добавляем новость в список опубликованных новостей
            storage_news.append(item)

            # Перезаписываем хранилище списком опубликованных новостей (оставляя только последние 800)
            update_news_storage(chat['storage'], storage_news, max_storage)

            logger.info(f"Опубликована новость: {item['header'][:25]}... ({item['source_name']}). "
                        f"Хранилище {chat['storage'].split('data')[-1]} обновлено")

            return True  # Выход из функции

        except Exception as e:
            logger.error(f"Ошибка при обработке новости: {e}")

            if attempt < retries:
                logger.warning(f"Не удалось отправить новость. Попытка {attempt}/{retries} отправки новости...")
                time.sleep(random.randint(5, 10))
            else:
                logger.error("Превышено количество попыток отправки. Пропускаем новость.")
                return False


# Функция для отправки последней новости из хранилища в X
def send_news_twitter(client, storage_tg, storage_twitter):
    """
    Публикует последнюю новость из хранилища в X (твиттер),
    только если она ещё не была опубликована в Twitter.

    :param client: Объект tweepy Client
    :param storage_tg: Хранилище новостей (JSON)
    :param storage_twitter: Хранилище опубликованных новостей в X (JSON)
    """

    # Логирование запуска
    logger.info("-" * 45)
    logger.info(f"▶ ЗАПУСК ДЛЯ X")
    logger.info("-" * 45)

    try:
        # Загружаем новости из хранилища
        storage_news = load_storage(storage_tg)
        if not storage_news:
            logger.info("В хранилище нет новостей для публикации в X.")
            return

        last_news = storage_news[-1]  # последняя новость

        # Загружаем список уже опубликованных новостей в Twitter
        twitter_news = load_storage(storage_twitter) or []
        twitter_keys = build_news_keys(twitter_news)

        # Проверяем, была ли новость уже опубликована
        if last_news['source_link'] in twitter_keys:
            logger.info("Новых новостей для публикации в X нет.")
            return

        # Формируем сообщение и публикуем
        message = f"{last_news['source_name']}: {last_news['header']}"
        message = message if len(message) <= 280 else message[:277] + "..."
        client.create_tweet(text=message)
        logger.info(f"Новость опубликована в X: {message}")

        # Добавляем новость в X-хранилище и обновляем файл
        twitter_news.append(last_news)
        update_news_storage(storage_twitter, twitter_news, limit=800)

    except Exception as e:
        logger.error(f"Ошибка публикации в X: {e}")


# Пайплайн отправки новостей
def send_news(sources, chat, bot, news_limit=None, days=None, deduplicate_func=None, review_func=None, retext_func=None,
              breaking=False):
    """
    Основной пайплайн отправки новостей

    :param sources: Список ресурсов или путь к файлу хранилища со всеми новостями
    :param chat: Словарь определения чата
    :param bot: Объект бота
    :param news_limit: Максимальное количество новостей из каждого ресурса
    :param days: Количество дней, включая сегодня, для парсинга новостей
    :param deduplicate_func: Функция дедубликации
    :param review_func: Функция отбора новостей
    :param retext_func: Функция обработки текста
    :param breaking: Флаг breaking_news, изменяет ход пайплайна для отбора и публикации breaking_news
    """

    # 0. Логирование запуска
    logger.info("-" * 45)
    logger.info(f"▶ ЗАПУСК ДЛЯ КАНАЛА: {chat['name']}")
    logger.info("-" * 45)

    # 1. Получение списков опубликованных и неопубликованных новостей
    news_limit = 1 if breaking else news_limit  # Если режим breaking, парсим по одной новости

    all_news = get_news_from_sources(sources, news_limit)
    if not all_news:
        return
    logger.info(f"{len(all_news)} всего новостей получено")

    storage_news = load_storage(chat['storage'])
    logger.info(f"{len(storage_news)} ранее опубликованных новостей загружено из хранилища "
                f"{chat['storage'].split('data')[-1]}")

    # 2. Фильтрация и дедубликация списков новостей
    storage_news_keys = build_news_keys(storage_news)  # Список уникальных идентификаторов (ссылок)
    new_news = [news for news in all_news if news["source_link"] not in storage_news_keys]  # Удаляем опубликованные

    if isinstance(days, int) and days > 0:
        logger.info(f"Обрезка списка неопубликованных новостей по дате:")
        new_news = get_newest_news(new_news, days)
        logger.info(f"Обрезка списка опубликованных новостей по дате:")
        published_news = get_newest_news(storage_news, days + 2)
    else:
        published_news = storage_news  # Если количество дней не задано, берём полный список опубликованных новостей

    if deduplicate_func:  # Используем функцию для дедубликации по смыслу, если она задана
        new_news = deduplicate_func(published_news, new_news, 0.2)

    if new_news:  # Если список новостей не пуст, лог количества новостей
        logger.info(f"{len(new_news)} уникальных новостей осталось в списке на публикацию")
    else:  # В противном случае завершаем функцию, так как новостей для публикации нет
        logger.info(f"Новых уникальных новостей в источниках нет. Выполнение функции завершено \n")
        return

    # 3. Отбор новостей (если функция отбора задана)
    logger.info(f"Отбор новости: метод {review_func.__name__}") if review_func else (
        logger.info(f"Отбор не задан - публикация всех новостей"))

    new_news = review_func(published_news, new_news) if review_func else new_news
    if not new_news:
        logger.info("Отбор вернул пустой список. Новостей для публикации нет.")
        return
    else:
        logger.info(f"Новостей для публикации: {len(new_news)}")

    # 4. Отправка новостей (цикл для каждой новости из списка)
    for item in new_news:
        # 4.1 Обработка заголовка и саммари через функцию ретекста, если она задана
        header = retext_func(item['header']) if retext_func else item['header']
        summary = retext_func(item['summary']) if retext_func and item.get('summary') else item.get('summary', '')

        # 4.2 Добавляем префикс BREAKING к заголовку, если флаг breaking_news включён
        header = f"BREAKING: {header}" if breaking and chat == chat_ctm_main else header

        # 4.3 Составление поста
        caption = construct_message(
            header,
            summary,
            item['source_name'],
            item['source_link'],
            chat['link'],
            chat['slogan']
        )

        # 4.4 Отправка поста и обновление хранилища
        send_one_news(caption, item, bot, chat, storage_news, 800, 3)

        # 4.5 Если флаг breaking news, добавляем опубликованную новость в отдельное хранилище для breaking news
        if breaking:
            try:
                with open(chat_ctm_main['storage_bn'], 'r', encoding='utf-8') as f:
                    current_news = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                current_news = []  # Создаём пустой список если файла нет или он пустой

            current_news.append(item)  # Добавляем новость в список
            update_news_storage(chat_ctm_main['storage_bn'], current_news)  # Обновляем хранилище

        # 5. Пауза после успешной отправки новости
        time.sleep(10)
