import asyncio
import aiohttp
from bs4 import BeautifulSoup
import csv
from typing import List, Dict
import re
from urllib.parse import urljoin
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import random
import os
from tqdm import tqdm

class IMDBSeriesParser:
    def __init__(self):
        self.base_url = "https://www.imdb.com"
        self.search_url = "https://www.imdb.com/search/title/?title_type=tv_series&release_date=2015-01-01,2026-12-31"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.partial_file = "imdb_urls_partial.txt"
        self.csv_file = "imdb_series_2015_2026.csv"

    def get_selenium_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def get_all_series_urls_with_selenium(self) -> List[str]:
        print("Запуск браузера для сбора ссылок...")
        driver = self.get_selenium_driver()
        all_urls = set()

        # 1. Загружаем уже собранные ссылки
        if os.path.exists(self.partial_file):
            try:
                with open(self.partial_file, 'r', encoding='utf-8') as f:
                    all_urls = {line.strip() for line in f if line.strip() and line.startswith('https://')}
                print(f"Загружено {len(all_urls):,} ссылок из {self.partial_file}")
            except Exception as e:
                print(f"Ошибка чтения файла: {e}")

        try:
            driver.get(self.search_url)
            print("Страница загружена, ждём...")
            time.sleep(random.uniform(4, 8))

            click_count = 0
            max_clicks = 500
            no_new_content_count = 0
            last_save_time = time.time()

            while click_count < max_clicks:
                current_count = len(all_urls)

                try:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    links = soup.find_all('a', {'class': 'ipc-title-link-wrapper'})
                    added = 0
                    for link in links:
                        href = link.get('href')
                        if href and '/title/tt' in href:
                            full_url = urljoin(self.base_url, href.split('?')[0].rstrip('/') + '/')
                            if re.match(r'^https://www\.imdb\.com/title/tt\d+/$', full_url):
                                if full_url not in all_urls:
                                    all_urls.add(full_url)
                                    added += 1

                    print(f" Текущее количество сериалов: {len(all_urls):,}")

                    # Сохранение каждые 200 новых или каждые 4 минуты
                    if added > 0 and (len(all_urls) % 200 == 0 or time.time() - last_save_time > 240):
                        with open(self.partial_file, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(sorted(all_urls)))
                        print(f"  Сохранено {len(all_urls):,} ссылок")
                        last_save_time = time.time()
                except Exception as e:
                    print(f"Ошибка извлечения ссылок: {e}")

                if len(all_urls) == current_count:
                    no_new_content_count += 1
                    if no_new_content_count >= 5:
                        print("Нет новых ссылок 5 раз подряд — конец списка")
                        break
                else:
                    no_new_content_count = 0

                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 300);")
                    time.sleep(random.uniform(3, 7))

                    button = None
                    try:
                        button = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "button.ipc-see-more__button"))
                        )
                    except:
                        pass

                    if button and button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(random.uniform(1, 3))
                        try:
                            driver.execute_script("arguments[0].click();", button)
                            click_count += 1
                            print(f" Клик {click_count}: загружаем ещё...")
                            time.sleep(random.uniform(4, 8))
                        except Exception as e:
                            print(f"Не удалось кликнуть: {e}")
                except Exception as e:
                    print(f"Ошибка скролла/клика: {e}")
                    time.sleep(5)

        except WebDriverException as e:
            print(f"Краш браузера: {e}. Ссылки сохранены.")
        finally:
            driver.quit()

        valid_urls = sorted(list(all_urls))
        with open(self.partial_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_urls))
        print(f"\nИтого уникальных ссылок: {len(valid_urls):,}")
        return valid_urls

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str | None:
        try:
            async with session.get(url, headers=self.headers, timeout=35) as resp:
                if resp.status == 200:
                    return await resp.text()
                print(f"{resp.status} → {url}")
                return None
        except Exception as e:
            print(f"Ошибка загрузки {url}: {e}")
            return None

    def extract_seasons_count(self, html: str) -> str:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            tabs = soup.find_all('a', {'data-testid': 'tab-season-entry'})
            if tabs:
                return tabs[-1].get_text(strip=True)
            select = soup.find('select', {'id': 'browse-episodes-season'})
            if select:
                return str(len(select.find_all('option')))
        except:
            pass
        return ''

    def extract_series_info(self, html: str, page_url: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        data = {
            'page_url': page_url,
            'image_url': '',
            'tvshow_title': '',
            'year': '',
            'rating': '',
            'director': '',
            'actors': '',
            'seasons': '',
            'series': '',
            'genres': '',
            'countries': '',
            'description': ''
        }
        try:
            # Заголовок
            title = soup.find('h1', {'data-testid': 'hero__primary-text'}) or soup.find('h1')
            if title:
                data['tvshow_title'] = title.get_text(strip=True)

            # Постер
            poster_url = ''
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    ld = json.loads(json_ld.string)
                    if isinstance(ld, dict) and 'image' in ld:
                        img = ld['image']
                        poster_url = img if isinstance(img, str) else (img[0] if isinstance(img, list) else '')
                except:
                    pass
            data['image_url'] = poster_url

            # Год
            year_li = soup.find('li', {'data-testid': 'title-details-releasedate'})
            if year_li:
                match = re.search(r'\b(19\d{2}|20\d{2})\b', year_li.get_text())
                if match:
                    data['year'] = match.group(1)

            # Рейтинг
            rating_div = soup.find('div', {'data-testid': 'hero-rating-bar__aggregate-rating__score'})
            if rating_div:
                match = re.search(r'(\d+\.?\d*)', rating_div.get_text(strip=True))
                if match:
                    data['rating'] = match.group(1)

            # Режиссёр / Создатель
            for li in soup.find_all('li', {'data-testid': 'title-pc-principal-credit'}):
                label = li.find('span', class_='ipc-metadata-list-item__label')
                if label and ('Creator' in label.text or 'Director' in label.text):
                    names = [a.text.strip() for a in li.find_all('a')]
                    data['director'] = ', '.join(names[:3])
                    break

            # Актёры
            cast = soup.find('section', {'data-testid': 'title-cast'})
            if cast:
                actors = [a.text.strip() for a in cast.find_all('a', {'data-testid': 'title-cast-item__actor'})]
                data['actors'] = ', '.join(actors[:6])

            # Эпизоды
            ep = soup.find('span', class_='ipc-title__subtext')
            if ep:
                match = re.search(r'(\d+)', ep.get_text(strip=True))
                if match:
                    data['series'] = match.group(1)

            # Жанры — исправлено: без дубликатов, чистая строка
            genres_set = set()
            for chip in soup.select('div[data-testid="interests"] span.ipc-chip__text, div[data-testid="genres"] a.ipc-chip'):
                text = chip.get_text(strip=True)
                if text:
                    genres_set.add(text)
            data['genres'] = ', '.join(sorted(genres_set))

            # Страны
            origin = soup.find('li', {'data-testid': 'title-details-origin'})
            if origin:
                countries = [a.get_text(strip=True) for a in origin.select('a.ipc-metadata-list-item__list-content-item')]
                data['countries'] = ', '.join(countries)

            # Описание
            desc = soup.find('span', {'data-testid': 'plot-xl'}) or soup.find('span', {'data-testid': 'plot-l'})
            if desc:
                data['description'] = desc.get_text(strip=True)

        except Exception as e:
            print(f"Ошибка парсинга {page_url}: {e}")

        return data

    async def parse_series(self, session: aiohttp.ClientSession, url: str) -> Dict | None:
        html = await self.fetch_page(session, url)
        if not html:
            return None
        data = self.extract_series_info(html, url)
        if data and not data.get('seasons'):
            ep_html = await self.fetch_page(session, url.rstrip('/') + '/episodes/')
            if ep_html:
                data['seasons'] = self.extract_seasons_count(ep_html)
        await asyncio.sleep(random.uniform(0.6, 1.8))
        return data

    async def parse_multiple_series(self, urls: List[str], batch_size: int = 8, fast_mode: bool = False) -> List[Dict]:
        all_results = []
        processed_urls = set()

        # Если CSV уже существует — читаем уже спарсенные page_url
        if os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    processed_urls = {row['page_url'] for row in reader if 'page_url' in row}
                print(f"Найдено {len(processed_urls):,} уже спарсенных страниц в CSV")
            except:
                pass

        urls_to_parse = [u for u in urls if u not in processed_urls]
        print(f"Из {len(urls):,} ссылок нужно спарсить ещё {len(urls_to_parse):,}")

        async with aiohttp.ClientSession() as session:
            for i in tqdm(range(0, len(urls_to_parse), batch_size),
                          desc="Парсинг" + (" (fast)" if fast_mode else ""),
                          unit="batch"):
                batch = urls_to_parse[i:i + batch_size]
                tasks = [self.parse_series(session, u) for u in batch]
                results = await asyncio.gather(*tasks)
                valid_results = [r for r in results if r]
                all_results.extend(valid_results)

                # Сразу добавляем в CSV (режим append)
                if valid_results:
                    fieldnames = ['page_url', 'image_url', 'tvshow_title', 'year', 'rating',
                                  'director', 'actors', 'seasons', 'series', 'genres',
                                  'countries', 'description']
                    file_exists = os.path.exists(self.csv_file)
                    with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        if not file_exists:
                            writer.writeheader()
                        writer.writerows(valid_results)
                    print(f"  Добавлено {len(valid_results)} строк в CSV")

                await asyncio.sleep(random.uniform(2, 5) if not fast_mode else random.uniform(0.5, 1.5))

        return all_results

async def main():
    parser = IMDBSeriesParser()
    print("=" * 70)
    print("Парсер сериалов IMDb 2015–2026 — с продолжением и добавлением в CSV")
    print("=" * 70)

    urls = parser.get_all_series_urls_with_selenium()
    if not urls:
        print("Ссылок не найдено")
        return

    # fast_mode=True — ускоряет, но выше риск бана
    await parser.parse_multiple_series(urls, batch_size=8, fast_mode=False)

    print(f"\nГотово. Итоговый файл: {parser.csv_file}")

    # Статистика по годам (из CSV)
    if os.path.exists(parser.csv_file):
        years = {}
        with open(parser.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                year = row.get('year', 'Unknown')
                years[year] = years.get(year, 0) + 1
        print("\nСтатистика по годам:")
        for y in sorted(years):
            print(f"{y}: {years[y]}")

if __name__ == "__main__":
    asyncio.run(main())