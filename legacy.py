from config import logger


# Функции, которые более не используются

# Функция фильтрации breaking news по ключевым словам
def filter_breaking_news_legacy(news_list):
    """
    Отбирает новости, содержащие ключевые слова для breaking news.

    :param news_list: Список словарей новостей
    :return: Список новостей (словари), которые содержат ключевые слова
    """

    logger.info(f"Фильтрация списка новостей по ключевым словам breaking news...")

    keywords = [
        # смерть и травмы
        "death", "dead", "dies", "killed", "murder", "stabbed", "shot", "injured",
        "suicide", "overdose", "hospitalized", "collapse", "critical condition",

        # катастрофы и несчастья
        "accident", "tragedy", "disaster", "fire", "earthquake", "explosion",

        # правовые и скандальные случаи
        "charged", "charges", "convicted", "conviction", "sentenced", "trial",
        "arrested", "prosecutors", "prison", "jail", "lawsuit", "sued", "indicted",
        "scandal", "investigation", "allegations",

        # кадровые и организационные кризисы
        "fired", "resigns", "resigned", "leaves band", "breakup", "split up",

        # общественные запреты и бойкоты
        "banned", "ban", "sanctions"
    ]

    breaking_news = []

    for news in news_list:
        text = f"{news.get('header', '')} {news.get('summary', '')}".lower()
        if any(keyword in text for keyword in keywords):
            breaking_news.append(news)

    logger.info(f"{len(breaking_news)} потенциальных breaking-новостей найдено")

    return breaking_news
