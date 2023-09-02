import requests
import json

from os import makedirs, getcwd, path, remove
from datetime import date, datetime
from random import randrange

# this code is absolutely cursed


class Ranime:
    def __init__(
                self,
                url='https://graphql.anilist.co',
                use_account=False,
                username=None,
                lowest_score=69,
                highest_score=100,
                earliest_year=1900,
                latest_year=int(date.today().year),
                num_pages_returned=40,
                exclude_formats=[],
                exclude_genres=[],
                cache_user_list=True,
                user_cache_directory='cache',
                user_cache_lifetime=60
            ):
        self._url = url
        self._username = username
        self._use_account = use_account
        self._score_low = lowest_score
        self._score_high = highest_score
        self._earliest_year = earliest_year * 10000  # pad with 4 zeroes
        self._latest_year = latest_year * 10000  # pad with 4 zeroes
        self._num_pages = num_pages_returned
        self._exclude_formats = exclude_formats
        self._exclude_genres = exclude_genres
        self._cache_user_list = cache_user_list
        self._user_cache_directory = user_cache_directory
        self._user_cache_lifetime = user_cache_lifetime
        self._get_full_user_list_query = '''
        query GetEntireUserList($username: String) {
            MediaListCollection(userName: $username, type: ANIME, forceSingleCompletedList: true) {
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
        nl = '{\n'  # let me put \n directly into f-strings >:(
        query_string = 'query AnimeByScores($score_low: Int, $score_high: Int, $year_low: FuzzyDateInt, $year_high: FuzzyDateInt, $exclude_formats: [MediaFormat], $exclude_genres: [String]) {'
        for i in range(self._num_pages):
            query_string += (
                "\n"
                f"  Page{i}: Page(page: {i}, perPage: 50) {nl}"
                f"    media(type: ANIME, averageScore_greater: $score_low, averageScore_lesser: $score_high, startDate_greater: $year_low, startDate_lesser: $year_high, format_not_in: $exclude_formats, genre_not_in: $exclude_genres) {nl}"
                "      id\n"
                "      title {\n"
                "        english\n"
                "        romaji\n"
                "      }\n"
                "      format\n"
                "      episodes\n"
                "      averageScore\n"
                "      genres\n"
                "      seasonYear\n"
                "      }\n"
                "  }"
            )
        # print(query_string + '}')
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
        return self._no_results()

    def _collapse_search_list(self, search_list) -> list:
        index = randrange(0, len(search_list))
        if self._username:
            user_cache = self.cache.read()
            if search_list[index]['id'] in user_cache['LIST']:
                del search_list[index]
                return self._collapse_search_list(search_list)
            return search_list[index]
        return search_list[index]

    def _no_results(self) -> list:
        return []


class Cache:
    def __init__(self, main):
        self._main = main
        self._url = main._url
        self._user = main._username
        self._user_cache_dir = main._user_cache_directory
        self._days_to_update = main._user_cache_lifetime
        makedirs(f'{self._user_cache_dir}', exist_ok=True)

    def read(self) -> dict:  # make better smile
        if path.exists(f'{getcwd()}/{self._user_cache_dir}/{self._user}.json'):
            with open(f'{getcwd()}/{self._user_cache_dir}/{self._user}.json', 'r') as user_cache:
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
        with open(f'{getcwd()}/{self._user_cache_dir}/{self._user}.json', 'w') as user_cache:
            user_cache.write(json_obj)
        return watched_list[self._user]

    def _delete_old_cache(self):
        if path.exists(f'{getcwd()}/{self._user_cache_dir}/{self._user}.json'):
            remove(f'{getcwd()}/{self._user_cache_dir}/{self._user}.json')

    def _requires_update(self, cache_file) -> bool:
        delta = datetime.today() - datetime.strptime(cache_file['UPDATED'], '%Y-%m-%d')
        return delta.days >= self._days_to_update
