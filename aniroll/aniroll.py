import requests
import json

from os import makedirs, getcwd, path, remove
from datetime import date, datetime
from random import randrange

# this code is absolutely cursed (but less cursed than it was before!!)

ALLOWED_FORMATS = ["TV", "TV_SHORT", "MOVIE", "SPECIAL", "OVA", "ONA", "MUSIC"]
# ALLOWED_GENRES = []


class AniRoll:
    def __init__(
                self,
                url: str = 'https://graphql.anilist.co',
                username: str = None,
                lowest_score: int = 69,
                highest_score: int = 100,
                earliest_year: int = 1000,
                latest_year: int = int(date.today().year),
                num_pages_returned: int = 40,
                exclude_formats: list = [],
                exclude_genres: list = [],
                cache_user_list: bool = True,
                user_cache_directory: str = 'cache',
                user_cache_lifetime: int = 60
            ):
        self._url = url
        self._username = username
        self._score_low = lowest_score
        self._score_high = highest_score
        self._earliest_year = earliest_year * 10000  # pad with 4 zeroes
        self._latest_year = latest_year * 10000  # pad with 4 zeroes
        self._num_pages = num_pages_returned
        self._exclude_formats = self._sanitize_exclude_formats(exclude_formats)
        self._exclude_genres = exclude_genres
        self._cache_user_list = cache_user_list
        self._user_cache_directory = user_cache_directory
        self._user_cache_lifetime = user_cache_lifetime
        self._get_full_user_list_query = '''
        query GetEntireUserList($username: String) {
            MediaListCollection(
                    userName: $username,
                    type: ANIME,
                    forceSingleCompletedList: true
                )
            {
                user {
                    name
                }
                lists {
                    status
                    entries {
                        mediaId
                    }
                }
            }
        }
        '''
        self._get_entries_by_score_query = self._get_entries_by_score_query()
        self.cache = Cache(self)

    def roll(self) -> dict:
        return self._retrieve_search_list()

    def _get_entries_by_score_query(self) -> str:
        query_string = 'query AnimeByScores($score_low: Int, $score_high: Int, $year_low: FuzzyDateInt, $year_high: FuzzyDateInt, $exclude_formats: [MediaFormat], $exclude_genres: [String]) {'
        for i in range(self._num_pages):
            query_string += f'''
                Page{i}: Page(page: {i}, perPage: 50) {{
                    media(
                        type: ANIME,
                        averageScore_greater: $score_low,
                        averageScore_lesser: $score_high,
                        startDate_greater: $year_low,
                        startDate_lesser: $year_high,
                        format_not_in: $exclude_formats,
                        genre_not_in: $exclude_genres
                    ) {{
                        id
                        title {{
                            english
                            romaji
                        }}
                        format
                        episodes
                        averageScore
                        genres
                        seasonYear
                    }}
                }}
            '''
        return query_string + '}'

    def _retrieve_user_list(self) -> list:
        variables = {'username': self._username}
        full_list_raw = requests.post(
            self._url,
            json={
                    'query': self._get_full_user_list_query,
                    'variables': variables
                 }
            ).json()['data']['MediaListCollection']['lists']
        full_list = []
        for list in full_list_raw:
            temp_list = [entry['mediaId'] for entry in list['entries']]
            full_list += temp_list
        return full_list

    def _retrieve_search_list(self):
        variables = {
            'score_low': self._score_low,
            'score_high': self._score_high,
            'year_low': self._earliest_year,
            'year_high': self._latest_year,
            'exclude_formats': self._exclude_formats,
            'exclude_genres': self._exclude_genres
        }
        retrieved_search_list = requests.post(
            self._url,
            json={
                    'query': self._get_entries_by_score_query,
                    'variables': variables
                 }
            ).json()['data']
        return self._make_full_search_list(retrieved_search_list)

    def _make_full_search_list(self, search_dict) -> list:
        search_list = []
        for i in range(self._num_pages):
            search_list += search_dict[f'Page{i}']['media']
        if search_list:
            return self._collapse_search_list(search_list)
        return search_list

    def _collapse_search_list(self, search_list) -> list:
        index = randrange(0, len(search_list))
        if self._cache_user_list:
            user_cache = self.cache._read()
            if search_list[index]['id'] in user_cache['LIST']:
                del search_list[index]
                return self._collapse_search_list(search_list)
            return search_list[index]
        return search_list[index]

    def _sanitize_exclude_formats(self, format_list) -> list:
        return [item.upper() for item in format_list
                if item in ALLOWED_FORMATS]


class Cache:
    def __init__(self, main):
        self._main = main
        self._url = main._url
        self._user = main._username
        self._user_cache_dir = main._user_cache_directory
        self._days_to_update = main._user_cache_lifetime
        if main._cache_user_list:
            self._path = f'{getcwd()}/{self._user_cache_dir}/{self._user}.json'
            makedirs(f'{self._user_cache_dir}', exist_ok=True)

    def _read(self) -> dict:  # make better smile
        if path.exists(self._path):
            with open(self._path, 'r') as user_cache:
                read_cache = json.load(user_cache)[self._user]
            if self._requires_update(read_cache):
                return self._update()
            return read_cache
        return self._update()

    def _update(self) -> dict:
        self._delete_old_cache()
        id_list = self._main._retrieve_user_list()
        id_list.sort()
        watched_list = {
            self._user: {
                'UPDATED': str(date.today()),
                'LIST': id_list
            }
        }
        json_obj = json.dumps(watched_list, indent=4)
        with open(self._path, 'w') as user_cache:
            user_cache.write(json_obj)
        return watched_list[self._user]

    def _delete_old_cache(self):
        if path.exists(self._path):
            remove(self._path)

    def _requires_update(self, cache_file) -> bool:
        delta = datetime.today() - datetime.strptime(
            cache_file['UPDATED'],
            '%Y-%m-%d')
        return delta.days >= self._days_to_update
