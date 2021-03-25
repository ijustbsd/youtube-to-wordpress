import base64
import os

import aiohttp
from aiogram import Bot, Dispatcher, executor, types

BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

WP_USER = os.getenv('WP_USER')
WP_APP_PWD = os.getenv('WP_APP_PWD')
WP_URL = os.getenv('WP_URL')
credentials = f'{WP_USER}:{WP_APP_PWD}'
WP_TOKEN = base64.b64encode(credentials.encode())

YT_API_KEY = os.getenv('YT_API_KEY')
YT_CHANNEL_ID = os.getenv('YT_CHANNEL_ID')

bot = Bot(token=BOT_API_TOKEN)
dp = Dispatcher(bot)


async def get_last_video():
    async with aiohttp.ClientSession() as session:
        url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'channelId': YT_CHANNEL_ID,
            'order': 'date',
            'key': YT_API_KEY
        }
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                resp_data = await resp.json()
    videos = resp_data['items']
    last_video = videos[0]
    return last_video['snippet']['title'], last_video['id']['videoId']


async def get_last_post():
    async with aiohttp.ClientSession() as session:
        url = WP_URL + '/?rest_route=/wp/v2/posts&order=desc&per_page=1'
        headers = {
            'Authorization': 'Basic ' + WP_TOKEN.decode()
        }
        async with session.get(url, headers=headers,) as resp:
            if resp.status == 200:
                resp_data = await resp.json()
                return resp_data[0]['title']['rendered'], resp_data[0]['link']


async def make_wp_post(title, video_id):
    content = '\n'.join([
        f'<!-- wp:embed {{"url":"https://youtu.be/{video_id}","type":"video","providerNameSlug":"youtube",'
        '"responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"} -->',
        '<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube '
        'wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">',
        f'https://youtu.be/{video_id}',
        '</div></figure>',
        '<!-- /wp:embed -->'
    ])
    post = {
        'title': title,
        'status': 'publish',
        'content': content,
        'categories': 5
    }
    async with aiohttp.ClientSession() as session:
        url = WP_URL + '/?rest_route=/wp/v2/posts'
        headers = {
            'Authorization': 'Basic ' + WP_TOKEN.decode()
        }
        async with session.post(url, headers=headers, json=post) as resp:
            if resp.status == 201:
                resp_data = await resp.json()
                return resp_data['link']


@dp.message_handler(commands=['post'])
async def post(message: types.Message):
    title, video_id = await get_last_video()
    title = title[title.find('.') + 2:-1]
    last_post_title, last_post_link = await get_last_post()
    if last_post_title is None:
        await message.answer('Что-то пошло не так 😔')
        return
    if title == last_post_title:
        await message.answer(f'Пост с этим видео уже существует: {last_post_link}')
        return
    link = await make_wp_post(title, video_id)
    if link is not None:
        await message.answer(f'Видео успешно опубликовано: {link}')
    else:
        await message.answer('Что-то пошло не так 😔')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
