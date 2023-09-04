import pyperclip

from aniroll.aniroll import AniRoll


def format_output(anime):
    if anime:
        title = anime['title'].get('english') if anime['title'].get('english') else anime['title'].get('romaji')
        pyperclip.copy(title)
        return (
            '>>> I found this! <<<\n'
            f'Title:    {title}\n'
            f'Format:   {anime["format"]}\n'
            f'Episodes: {anime["episodes"]}\n'
            f'Score:    {anime["averageScore"]}\n'
            f'Genres:   {anime["genres"]}\n'
            f'Year:     {anime["seasonYear"]}'
        )
    return "No results found for the given parameters!"


if __name__ == "__main__":
    aniroll = AniRoll(
        username='dietsoda',
        exclude_formats=['MOVIE', 'OVA', 'MUSIC', 'TV_SHORT', 'SPECIAL'],
        user_cache_directory='cache'
    )
    print(format_output(aniroll.roll()))
