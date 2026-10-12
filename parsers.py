import fake_useragent
import requests

from bs4 import BeautifulSoup
from dateutil import parser, tz

# Определение объекта UserAgent
ua = fake_useragent.UserAgent()


# Функция получения BeautifulSoup одной страницы
def get_bs(source_link):
    """
    Функция получения BeautifulSoup страницы

    Принимает на вход ссылку на страницу и возвращает BeautifulSoup

    :param source_link: Ссылка на страницу
    :return: BeautifulSoup страницы
    """

    try:
        headers = {'User-Agent': ua.random}
        response = requests.get(source_link, headers=headers, timeout=10)
        response.raise_for_status()  # автоматически выбрасывает исключение, если сервер вернул ошибку HTTP
        return BeautifulSoup(response.text, "lxml")
    except Exception:
        return None


# Функция форматирования даты
def formatted_date(date):
    """
    Форматирует дату в формат ДД.ММ.ГГГГ

    :param date: дата в виде строки
    :return: дата в формате ДД.ММ.ГГГГ
    """

    # Список сервисных слов для удаления
    service_words = [
        "Updated",
        "Published",
        "Published on"
    ]

    # Очистка даты от сервисных слов
    for word in service_words:
        date = date.replace(word, "").strip()

    # Пояснение часовой зоны EST для азии:
    tz_map = {
        "EST": tz.gettz("Asia/Kuala_Lumpur")
    }

    # Преобразование текста в datetime
    try:
        return parser.parse(date, tzinfos=tz_map).strftime("%d.%m.%Y") if date else None
    except (parser.ParserError, ValueError):
        return None


# Функции парсинга для сайтов
def get_news_nme(item):
    """
    Функция для парсинга NME

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('h3')
    header = header.text if header else None

    summary = item.find('div', 'td-excerpt')
    summary = summary.text if summary else None

    source_link = item.find('div', 'td-module-thumb')
    source_link = source_link.find(name='a').attrs['href'] if source_link else None

    image = item.find('span', 'entry-thumb td-thumb-css')
    image_url = image.attrs.get('data-img-retina-url') if image else None

    article_bs = get_bs(source_link)

    photo_credit = article_bs.find('figcaption')
    photo_credit = photo_credit.text.strip() if photo_credit else None

    date = article_bs.find('time', 'entry-date updated td-module-date')
    date = formatted_date(date.get_text(strip=True) if date else None)

    # Возвращение словаря с данными
    return {
        'source_name': 'NME',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_rs(item):
    """
    Функция для парсинга Rolling Stones

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('a', 'c-title__link lrv-a-unstyle-link lrv-u-color-grey:hover lrv-a-truncate-ellipsis-3line')
    header = header.get_text(strip=True) if header else None

    summary = item.find('p', 'c-dek lrv-a-font-body-m lrv-u-margin-tb-00 lrv-a-truncate-ellipsis-2line')
    summary = summary.get_text(" ", strip=True) if summary else None

    source_link = item.find(name='a')
    source_link = source_link.attrs['href'] if source_link else None

    image_url = item.find('img')
    image_url = image_url.attrs.get('data-lazy-src') if image_url else None

    article_bs = get_bs(source_link)

    photo_credit = article_bs.find('cite')
    photo_credit = photo_credit.text if photo_credit else None

    date = article_bs.find('time', class_='c-timestamp')
    date = formatted_date(date['datetime']) if date else None

    return {
        'source_name': 'Rolling Stone',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_dmn(item):
    """
    Функция для парсинга Digital Music News

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('h2', 'cb-post-title')
    header = header.get_text(strip=True) if header else None

    source_link = item.find(name='a')
    source_link = source_link.attrs['href'] if source_link else None

    image_url = item.find('img')
    image_url = image_url.attrs.get('srcset') if image_url else None
    image_url = image_url.split(' ')[2] if image_url else None

    article_bs = get_bs(source_link)

    if article_bs is None:
        return None

    summary = article_bs.find('meta', property="og:description")
    summary = summary['content'] if summary else None

    photo_credit = article_bs.find('p')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    date = article_bs.find('time', attrs={'class': 'updated'})
    date = formatted_date(date.get_text(strip=True)) if date else None

    return {
        'source_name': 'Digital Music News',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_pf(item):
    """
    Функция для парсинга Pitchfork

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('img')
    header = header['alt'] if header else None

    source_link = item.find('a', 'SummaryItemHedLink-cxRzVg dWagqQ summary-item-tracking__hed-link '
                                 'summary-item__hed-link summary-item__hed-link--underline-disable')
    source_link = ('https://pitchfork.com' + source_link.attrs['href']) if source_link else None

    image_url = item.find('img')
    image_url = image_url.attrs.get('src') if image_url else None

    article_bs = get_bs(source_link)

    photo_credit = article_bs.find('span', 'BaseText-fEwdHD CaptionCredit-cUgOGk fSrqtv '
                                           'hRFzlA caption__credit').get_text(strip=True)
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    date = article_bs.find('time', attrs={'data-testid': 'ContentHeaderPublishDate'})
    date = formatted_date(date.get_text(strip=True)) if date else None

    return {
        'source_name': 'Pitchfork',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_npr(item):
    """
    Функция для парсинга NPR

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('h2')
    header = header.get_text(strip=True) if header else None

    summary = item.find('p', 'teaser')
    summary = summary.text if summary else None

    source_link = item.find('a')
    source_link = source_link['href'] if source_link else None

    photo_credit = item.find('span')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    article_bs = get_bs(source_link)

    image_url = article_bs.find('div', 'imagewrap has-source-dimensions')
    image_url = image_url.find('img')['src'] if image_url else None

    date = article_bs.find('span', 'date')
    date = formatted_date(date.get_text(strip=True)) if date else None

    return {
        'source_name': 'NPR',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_udm(item):
    """
    Функция для парсинга udiscovermusic

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    source_link = item.find('a')
    source_link = source_link['href'] if source_link else None

    article_bs = get_bs(source_link)

    header = article_bs.find('title')
    header = header.get_text(strip=True).split("|")[0] if header else None

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    image_url = article_bs.find('meta', attrs={'property': 'og:image'})
    image_url = image_url['content'] if image_url else None

    photo_credit = article_bs.find('div', 'mvp-feat-caption')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    date = article_bs.find('time', 'rpwe-time published')
    date = formatted_date(date.get_text(strip=True)) if date else None

    return {
        'source_name': 'udiscovermusic',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_hr(item):
    """
    Функция для парсинга the Hollywood Reporter

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('a')
    header = header.get_text(strip=True) if header else None

    summary = item.find('p')
    summary = summary.get_text(strip=True) if summary else None

    source_link = item.find('a')
    source_link = source_link.attrs['href'] if source_link else None

    article_bs = get_bs(source_link)

    photo_credit = article_bs.find('cite', 'a-font-accent-uppercase-xs lrv-u-color-grey-dark')
    photo_credit = photo_credit.text if photo_credit else None

    image_url = article_bs.find('div', 'lrv-a-crop-16x9')
    image_url = image_url.img.get('src') if image_url else None

    date = article_bs.find('div', 'u-margin-l-1@tablet')
    date = formatted_date(date.get_text(strip=True))

    return {
        'source_name': 'The Hollywood Reporter',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_bb(item):
    """
    Функция для парсинга Billboard

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('a',
                       'c-title__link lrv-a-unstyle-link u-article-title-underline:hover u-article-title-underline:hover')
    header = header.get_text(strip=True) if header else None

    source_link = item.find('a')
    source_link = source_link.attrs['href'] if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('p')
    summary = summary.get_text(strip=True) if summary else None

    photo_credit = article_bs.find('cite', 'lrv-u-color-grey-dark')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    image_url = article_bs.find_all('link', {'rel': 'preload', 'imagesrcset': True})
    image_url = image_url[1]['href'] if image_url else None

    date = article_bs.find('div', 'article-timestamp // lrv-u-display-block')
    date = formatted_date(date.get_text(strip=True))

    return {
        'source_name': 'Billboard',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_tm(item):
    """
    Функция для парсинга the music

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('div', 'title')
    header = header.get_text(strip=True) if header else None

    source_link = item['href']
    source_link = f"https://themusic.com.au{source_link}" if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'].encode('latin1').decode('utf-8') if summary else None

    photo_credit = article_bs.find('div', 'caption')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else ''

    image_url = article_bs.find('div', 'article-image')
    image_url = image_url.find('class' == 'image')['src'] if image_url else None

    date = article_bs.find('span', 'local-date')
    date = formatted_date(date['x-data'].split("\'")[1]) if date else None

    return {
        'source_name': 'TheMusic',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_gn(item):
    """
    Функция для парсинга the guardian

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    source_link = item.find('a')
    source_link = f"https://www.theguardian.com{source_link['href']}" if source_link else None

    article_bs = get_bs(source_link)

    header = article_bs.find('title')
    header = header.get_text().split('|')[0].strip() if header else None

    summary = article_bs.find('p')
    summary = summary.get_text() if summary else None

    photo_credit = article_bs.find('figcaption')
    photo_credit = photo_credit.get_text() if photo_credit else None

    image_url = article_bs.find('source')
    image_url = image_url['srcset'] if image_url else None

    date = article_bs.find('meta', property='article:published_time')
    date = formatted_date(date["content"]) if date else None

    return {
        'source_name': 'The Guardian',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_lw(item):
    """
    Функция для парсинга Loudwire

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('img')
    header = header['alt'] if header else None

    source_link = item.find('a')['href']
    source_link = f"https:{source_link}" if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    photo_credit = article_bs.find('div', 'content-header-header')
    photo_credit = photo_credit.get_text() if photo_credit else None

    image_url = article_bs.find('meta', attrs={'name': 'sailthru.image.full'})
    image_url = image_url['content'] if image_url else None

    date = article_bs.find('time')
    date = formatted_date(date['datetime']) if date else None

    return {
        'source_name': 'Loudwire',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_ucr(item):
    """
    Функция для парсинга Ultimate Classic Rock

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('img')
    header = header['alt'] if header else None

    source_link = item.find('a')['href']
    source_link = f"https:{source_link}" if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    photo_credit = article_bs.find('div', 'content-header-header')
    photo_credit = photo_credit.get_text() if photo_credit else None

    image_url = article_bs.find('meta', attrs={'name': 'sailthru.image.full'})
    image_url = image_url['content'] if image_url else None

    date = article_bs.find('time')
    date = formatted_date(date['datetime']) if date else None

    return {
        'source_name': 'Ultimate Classic Rock',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_hola(item):
    """
    Функция для парсинга Hola!

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('a')
    header = header['aria-label'] if header else None

    source_link = item.find('a')
    source_link = source_link['href'] if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    photo_credit = article_bs.find('span', 'ho-imCr-1233683')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    image_url = article_bs.find('img')
    image_url = image_url['src'] if image_url else None

    date = article_bs.find('meta', attrs={'property': 'article:published_time'})
    date = formatted_date(date['content']) if date else None

    return {
        'source_name': 'Hola!',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_exclaim(item):
    """
    Функция для парсинга Exclaim!

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    source_link = item.find('a')
    source_link = f"https://exclaim.ca{source_link['href']}" \
        if source_link and source_link['href'].startswith('/music/article/') else None

    if not source_link:
        return None

    article_bs = get_bs(source_link)

    header = article_bs.find('h1', 'u-m-0 u-py-4 u-text-2xl u-normal-case md:u-text-3xl')
    header = header.get_text(strip=True) if header else None

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    photo_credit = article_bs.find('figcaption', 'u-px-6 u-font-sans md:u-px-0')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    image_url = article_bs.find('img', 'u-mb-2 u-w-full')
    image_url = image_url['src'] if image_url else None

    date = article_bs.find('span', 'u-block')
    date = formatted_date(date.get_text(strip=True).split('Published')[1]) if date else None

    return {
        'source_name': 'Exclaim!',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_mia(item):
    """
    Функция для парсинга Music in Africa

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.get_text(strip=True) if item else None

    source_link = item.find('a')
    source_link = f"https://www.musicinafrica.net{source_link['href']}" if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('meta', attrs={'name': 'description'})
    summary = summary['content'] if summary else None

    date = article_bs.find('div', 'field field-name-post-date field-type-ds field-label-hidden')
    date = formatted_date(date.get_text(strip=True)) if date else None

    if summary is None:
        return None

    else:
        return {
            'source_name': 'Music in Africa',
            'header': header,
            'summary': summary,
            'source_link': source_link,
            'image_url': None,
            'photo_credit': None,
            'date': date
        }


def get_news_nme_asia(item):
    """
    Функция для парсинга NME Asia

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('a')
    header = header['title'] if header else None

    summary = item.find('div', 'td-excerpt')
    summary = summary.get_text(strip=True) if summary else None

    image_url = item.find('span', 'entry-thumb td-thumb-css')
    image_url = image_url['data-img-retina-url'] if image_url else None

    source_link = item.find('a')
    source_link = source_link['href'] if source_link else None

    article_bs = get_bs(source_link)

    photo_credit = article_bs.find('figcaption', 'tdb-caption-text')
    photo_credit = photo_credit.get_text(strip=True) if photo_credit else None

    date = article_bs.find('time', 'entry-date updated td-module-date')
    date = formatted_date(date.get_text(strip=True)) if date else None

    return {
        'source_name': 'NME',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }


def get_news_mpa(item):
    """
    Функция для парсинга Music Press Asia

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('h4', 'heading')
    header = header.get_text(strip=True) if header else None

    source_link = item.find('a')
    source_link = source_link['href'] if source_link else None

    article_bs = get_bs(source_link)

    summary = article_bs.find('div', 'story post-story')
    summary = summary.find('p') if summary else None
    summary = summary.get_text(strip=True) if summary else None

    date = article_bs.find('meta', attrs={'property': 'article:published_time'})
    date = formatted_date(date['content']) if date else None

    return {
        'source_name': 'Music Press Asia',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': None,
        'photo_credit': None,
        'date': date
    }


def get_news_ppl(item):
    """
    Функция для парсинга People

    :param item: BeautifulSoup одной статьи
    :return: словарь {имя ресурса, заголовок, саммари, ссылка на статью, ссылка на фото, подпись к фото}
    """

    header = item.find('span', class_='card__title-text')
    header = header.get_text(strip=True) if header else None

    source_link = item.get('href')

    article_bs = get_bs(source_link)

    summary = article_bs.find('p', 'article-subheading text-utility-300')
    summary = summary.get_text(strip=True) if summary else None

    image_url = article_bs.find('img', 'primary-image__image mntl-primary-image--blurry')
    image_url = image_url['src'] if image_url else None

    photo_credit = article_bs.find('span', 'figure-article-caption-owner')
    photo_credit = photo_credit.text.replace(' :', ':') if article_bs else None

    date = article_bs.find('div', 'mntl-attribution__item-date')
    date = formatted_date(date.get_text()) if date else None

    return {
        'source_name': 'People',
        'header': header,
        'summary': summary,
        'source_link': source_link,
        'image_url': image_url,
        'photo_credit': photo_credit,
        'date': date
    }