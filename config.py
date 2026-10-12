# Импорт стандартных библиотек
import io
import logging
import os

# Импорт сторонних библиотек
import openai
import tweepy
from dotenv import load_dotenv
from telebot import TeleBot

# Импорт локальных модулей
from parsers import get_news_nme, get_news_rs, get_news_dmn, get_news_pf, get_news_npr, get_news_udm, get_news_hr, \
    get_news_bb, get_news_tm, get_news_gn, get_news_lw, get_news_ucr, get_news_hola, get_news_exclaim, \
    get_news_mia, get_news_nme_asia, get_news_mpa, get_news_ppl

# Загрузка переменных окружения
load_dotenv()

# Пути к файлам:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONT_PATH = os.path.join(BASE_DIR, 'visualization')
STORAGE_PATH = os.path.join(BASE_DIR, 'data')
MODELS_PATH = os.path.join(BASE_DIR, 'models')

# Настройки логирования
log_stream = io.StringIO()  # Буфер для логов

formatter_console = logging.Formatter("%(asctime)s | %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")  # Формат для консоли
formatter_memory = logging.Formatter("%(levelname)s - %(message)s")  # Формат для отправки в ТГ

console_handler = logging.StreamHandler()  # Хэндлер для консоли
console_handler.setFormatter(formatter_console)

memory_handler = logging.StreamHandler(log_stream)  # Хэндлер для буфера в памяти
memory_handler.setFormatter(formatter_memory)

logger = logging.getLogger("main_logger")  # Логгер
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(memory_handler)
logger.propagate = False

# Инициализация ботов
bot_test = TeleBot(
    token=os.getenv('BOT_TEST_TOKEN'),
    parse_mode='html',
    disable_web_page_preview=True
)

bot_ctm = TeleBot(
    token=os.getenv('BOT_CTM_TOKEN'),
    parse_mode='html',
    disable_web_page_preview=True
)

bot_ctm_main = TeleBot(
    token=os.getenv('BOT_CTM_MAIN_TOKEN'),
    parse_mode='html',
    disable_web_page_preview=True
)

# Инициализация API-ключей для X
client_X = tweepy.Client(
    bearer_token=os.getenv('BEARER_TOKEN'),
    consumer_key=os.getenv('CONSUMER_KEY'),
    consumer_secret=os.getenv('CONSUMER_SECRET'),
    access_token=os.getenv('ACCESS_TOKEN'),
    access_token_secret=os.getenv('ACCESS_TOKEN_SECRET'),
)

# Установка API-ключа OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Определение чатов

chat_ctm_bs = {
    'id': os.getenv('CHAT_CTM_BS_ID'),
    'link': os.getenv('TELEGRAM_CHANNEL_LINK', 'https://t.me/your_channel'),
    'name': 'CtM Beautiful Soup',
    'slogan': 'Join to bring music closer',
    'storage': os.path.join(BASE_DIR, 'data', 'storage_ctm_bs.json')
}


chat_ctm_alerting = {
    'id': os.getenv('CHAT_CTM_ALERTING_ID'),
    'link': '',
    'name': 'CTM Alerting',
    'slogan': '',
    'storage': ''
}

chat_ctm_main = {
    'id': os.getenv('CHAT_CTM_MAIN_ID'),
    'link': os.getenv('TELEGRAM_CHANNEL_LINK', 'https://t.me/your_channel'),
    'name': 'Close to Music',
    'slogan': 'Join to bring music closer',
    'storage': os.path.join(BASE_DIR, 'data', 'storage_ctm_main.json'),
    'storage_bn': os.path.join(BASE_DIR, 'data', 'storage_bn.json')
}

chat_ctm_test = {
    'id': os.getenv('CHAT_PM_ID'),
    'link': os.getenv('TELEGRAM_CHANNEL_LINK', 'https://t.me/your_channel'),
    'name': 'CTM Test',
    'slogan': 'Join to bring music closer',
    'storage': os.path.join(BASE_DIR, 'data', 'storage_test.json')
}

twitter_main = {
    'id': '',
    'link': '',
    'name': 'CtM Х',
    'slogan': '',
    'storage': os.path.join(BASE_DIR, 'data', 'storage_x_main.json')
}


# Определение ресурсов

source_nme = {
    'url': 'https://www.nme.com/news/music',
    'name': 'NME',
    'tag': 'div',
    'attrs': 'td-module-container td-category-pos-above',
    'extract_func': get_news_nme
}

source_rs = {
    'url': 'https://www.rollingstone.com/music/music-news/',
    'name': 'ROLLING STONE',
    'tag': 'div',
    'attrs': 'lrv-u-flex lrv-u-flex-direction-column@mobile-max',
    'extract_func': get_news_rs
}

source_dmn = {
    'url': 'https://www.digitalmusicnews.com/category/music-industry/',
    'name': 'DIGITAL MUSIC NEWS',
    'tag': 'article',
    'attrs': (),
    'extract_func': get_news_dmn
}

source_pf = {
    'url': 'https://pitchfork.com/news/',
    'name': 'PITCHFORK',
    'tag': 'div',
    'attrs': 'SummaryItemWrapper-ircdWR lafjem summary-item summary-item--has-border summary-item--no-icon '
             'summary-item--text-align-left summary-item--layout-placement-text-below summary-item--layout-'
             'position-image-left summary-item--layout-proportions-50-50 summary-item--side-by-side-align-'
             'top summary-item--side-by-side-image-right-mobile-false summary-item--standard '
             'SummaryCollectionGridSummaryItem-HgAzv bmPtim',
    'extract_func': get_news_pf
}

source_npr = {
    'url': 'https://www.npr.org/sections/music-news',
    'name': 'NPR',
    'tag': 'article',
    'attrs': 'item has-image',
    'extract_func': get_news_npr
}

source_udm = {
    'url': 'https://www.udiscovermusic.com/music/news/',
    'name': 'UDISCOVERMUSIC',
    'tag': 'li',
    'attrs': 'relative infinite-post',
    'extract_func': get_news_udm
}

source_hr = {
    'url': 'https://www.hollywoodreporter.com/c/news/music-news/',
    'name': 'HR',
    'tag': 'div',
    'attrs': 'lrv-a-grid u-grid-gap-050@mobile-max',
    'extract_func': get_news_hr
}

source_bb = {
    'url': 'https://www.billboard.com/c/music/music-news/',
    'name': 'BILLBOARD',
    'tag': 'div',
    'attrs': 'a-story-grid',
    'extract_func': get_news_bb
}

source_tm = {
    'url': 'https://themusic.com.au',
    'name': 'THE MUSIC',
    'tag': 'a',
    'attrs': {'class': 'article latest'},
    'extract_func': get_news_tm
}

source_gn = {
    'url': 'https://www.theguardian.com/music',
    'name': 'THE GUARDIAN',
    'tag': 'div',
    'attrs': 'dcr-1kd7xsm',
    'extract_func': get_news_gn
}

source_ppl = {
    'url': 'https://people.com/music/',
    'name': 'PEOPLE',
    'tag': 'a',
    'attrs': 'comp mntl-card-list-items mntl-universal-card mntl-document-card mntl-card '
             'card--image-top u-dot-divider--container u-dot-divider--no-margin card card--no-image',
    'extract_func': get_news_ppl
}

source_lw = {
    'url': 'https://loudwire.com/category/news/#google_vignette',
    'name': 'LOUDWIRE',
    'tag': 'figure',
    'attrs': 'frameme v3',
    'extract_func': get_news_lw
}

source_ucr = {
    'url': 'https://ultimateclassicrock.com/category/news/',
    'name': 'UCR',
    'tag': 'figure',
    'attrs': 'frameme v3',
    'extract_func': get_news_ucr
}

source_hola = {
    'url': 'https://www.hola.com/us/tags/music/',
    'name': 'HOLA!',
    'tag': 'article',
    'attrs': 'ho-miCaGrAr-20403fb ho-theme ho-card ho-caHaLi-10929fc',
    'extract_func': get_news_hola
}

source_exclaim = {
    'url': 'https://exclaim.ca/music/news',
    'name': 'EXCLAIM!',
    'tag': 'li',
    'attrs': '',
    'extract_func': get_news_exclaim
}

source_mia = {
    'url': 'https://www.musicinafrica.net/magazine/news',
    'name': 'Music in Africa',
    'tag': 'div',
    'attrs': 'views-field views-field-title',
    'extract_func': get_news_mia
}

source_nme_asia = {
    'url': 'https://www.nme.com/tag/asia',
    'name': 'NME Asia',
    'tag': 'div',
    'attrs': 'td-module-container td-category-pos-above',
    'extract_func': get_news_nme_asia
}

source_mpa = {
    'url': 'https://www.musicpressasia.com/category/music-news/',
    'name': 'MP Asia',
    'tag': 'div',
    'attrs': 'grid clearfix',
    'extract_func': get_news_mpa
}


# Определение списков ресурсов

all_sources = [
    source_nme,
    source_rs,
    source_dmn,
    source_pf,
    source_npr,
    source_udm,
    source_hr,
    source_bb,
    source_tm,
    source_gn,
    source_lw,
    source_ucr,
    source_hola,
    source_exclaim,
    source_mia,
    source_mpa,
    source_ppl
]

# Промпт

general_prompt = """
You have the following NEW UNPUBLISHED NEWS:
{new_news_text}

And the following OLD PUBLISHED NEWS (ordered from oldest to most recent):
{old_news_text}

Your task: select ONE best news item from NEW UNPUBLISHED NEWS to publish next.  

AUDIENCE PROFILE  
- Passionate music lovers valuing albums, reissues, concerts, and artistic statements over gossip.  
- Listen actively, care about both music content and sound quality.  
- Curious across genres since the 1950s; respect legends but open to new acts.  
- Expect news about releases, tours, festivals, reissues, cultural impact, industry changes.  
- Artist personal lives only if significant (death, lineup change, identity, public stance).  

Apply the following rules IN PRIORITY ORDER:

1. **Interest for audience** — Choose the item most engaging for this audience (global impact, novelty, 
cultural weight, high discussion potential).  
   - Prioritize scandals, surprise releases, disasters, or major public statements.  
   - Exclude ads, polls, or clickbait.

2. **Diversity of topics/artists/events** — Ensure variety compared to the last 3 OLD PUBLISHED NEWS.  
   - Avoid repeating the same artist, same event, or same theme unless the new item is clearly more important.  

3. **Follow-up / Refutation** — Publish ONLY if the new item substantially changes the meaning of a previously 
published news item (adds significant new details or is a clear correction/denial).  
   - If the addition is minor or unclear, skip it.  

4. **Death of musician** — Minimize unless the artist is of clear global importance (legend, legendary, icon, 
idol, greatest, godfather, etc.). Otherwise treat as regular news.  

5. **Completeness** — If several items are equal, prefer the one with the most thorough explanation of the event.  

Final instruction:  
Return ONLY the number of the selected news item.  
The output must contain only the number on its own line — no words, punctuation, quotes, or spaces.
"""

breaking_prompt = """
You have the following NEW UNPUBLISHED NEWS:
{new_news_text}

And the following OLD PUBLISHED NEWS (ordered from oldest to most recent):
{old_news_text}

Your task: determine if ANY of the NEW UNPUBLISHED NEWS items qualify as TRUE BREAKING NEWS.

BREAKING NEWS must be EXTREMELY RARE.

The default assumption is:
MOST NEWS IS NOT BREAKING NEWS.

STRICT Definition of BREAKING NEWS (music industry only)

A news item qualifies ONLY if it is:

urgent,
globally significant,
currently unfolding or newly announced,
and important enough to dominate major music headlines.

It MUST satisfy at least ONE of these conditions:

GLOBAL EMERGENCY / MAJOR INCIDENT
Death of a globally famous artist (A-list international level).
Serious accident, hospitalization, disappearance, attack, or catastrophe involving globally known artists.
Large-scale festival disaster or public safety emergency.
INDUSTRY-SHAPING EVENT
Collapse, acquisition, shutdown, or major restructuring of major labels/platforms.
Legal ruling or political decision affecting the global music industry.
Cancellation of a globally important festival or tour on a massive scale.
MAJOR CULTURAL SHOCK
Surprise reunion of globally iconic artists/bands after many years.
Sudden breakup/disbandment of a globally recognized act.
Unexpected release or announcement that becomes worldwide mainstream news immediately.
MAJOR CRIMINAL / LEGAL EVENT
Arrest, conviction, lawsuit, scandal, or investigation ONLY if:
it involves globally famous artists,
AND it is dominating mainstream international coverage.
VERY IMPORTANT: AUTOMATIC DISQUALIFIERS

The following are NOT BREAKING NEWS under any circumstances:

Interviews
Opinions
Reactions
Reflections
Memoirs or book excerpts
Anniversary articles
Historical retrospectives
"Artist reflects on death/event"
Streaming milestones
Chart achievements
Sales milestones
Tour dates
Festival lineups
Concert reviews
Album reviews
Regular album announcements
Surprise albums from non-mainstream artists
Routine celebrity drama
Minor controversies
Rumors or speculation
Articles about past events becoming exhibitions/books/documentaries
“First show of the tour”
Standard release news
Local or niche artist news
Additional filtering rule

If you are unsure whether something is breaking news:
DO NOT SELECT IT.

It is better to miss a borderline story than to incorrectly classify ordinary news as breaking.

Output Rules
If at least one NEW UNPUBLISHED NEWS item CLEARLY matches the strict breaking news criteria:
return ONLY the number of the SINGLE most important item.
If none clearly qualify:
return NOTHING.

Do not explain.
Do not justify.
Do not output any text except the number itself.
"""

