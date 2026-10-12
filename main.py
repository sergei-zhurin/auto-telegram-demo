from core import send_news, send_logs, deduplicate_news, check_schedule, review_general, \
    review_breaking, send_news_twitter
from config import chat_ctm_bs, bot_ctm, chat_ctm_alerting, chat_ctm_main, bot_ctm_main, client_X, twitter_main
from config import all_sources

# 1. Сохраняем время запуска и сверяем с расписанием
time_for_general_news = check_schedule(
    freq_weekday=2,
    freq_weekend=3,
    pub_minute=0,
    utc_offset=0
)

time_for_general_news_X = check_schedule(
    freq_weekday=4,
    freq_weekend=6,
    pub_minute=0,
    utc_offset=0
)

# 2. Если время для General News, парсим сайты и публикуем одну новость
if time_for_general_news:

    send_news(
        all_sources,
        chat_ctm_bs,
        bot_ctm,
        news_limit=5
    )

    send_news(
        chat_ctm_bs['storage'],
        chat_ctm_main,
        bot_ctm_main,
        days=2,
        deduplicate_func=deduplicate_news,
        review_func=review_general,
        retext_func=None,
        breaking=False
    )

    # И если при этом время для поста в Х, постим в Х
    if time_for_general_news_X:
        send_news_twitter(
            client_X,
            chat_ctm_main['storage'],
            twitter_main['storage']
        )

# 3. Если нет - парсим по одной новости и публикуем только если есть breaking_news
else:

    send_news(
        all_sources,
        chat_ctm_bs,
        bot_ctm,
        news_limit=1
    )

    send_news(
        chat_ctm_bs['storage'],
        chat_ctm_main,
        bot_ctm_main,
        days=1,
        deduplicate_func=deduplicate_news,
        review_func=review_breaking,
        retext_func=None,
        breaking=True
    )

    send_news_twitter(
        client_X,
        chat_ctm_main['storage_bn'],
        twitter_main['storage']
    )


# 4. Отправляем лог
send_logs(
    chat_ctm_alerting,
    bot_ctm,
    mode='errors'
)
