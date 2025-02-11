from os import environ
from pprint import pprint
from requests import request, Response
from typing import Generator, Tuple, Literal, Dict, Any, Optional, List
from models.release import Release
from models.album import Album
from math import ceil

# Define supported HTTP methods. Extend this tuple if needed.
HTTPMethod = Literal['GET'] | Literal['POST'] | Literal['PATCH'] | Literal['DELETE']
# Define a type alias for an HTTP request, which is a tuple of (method, url_template)
HttpRequest = Tuple[HTTPMethod, str]

class Api:
    # Define an endpoint using our HttpRequest type alias.
    ENDPOINT_WANTED_ALBUMS_MISSING: HttpRequest = (
        'GET',
        '{schema}://{host}:{port}/api/v1/wanted/missing?page={page_num}&pageSize={page_size}&includeArtist={bool_include_artist}&monitored={bool_monitored}'
    )

    def __init__(self, host: str, port: int, api_key: str, ssl: bool = False):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.ssl = ssl  # Determines whether to use 'https' or 'http'

    def do_request(self, _request: HttpRequest, params: Optional[Dict[str, Any]] = None, **kwargs) -> Response:
        """
        Perform an HTTP request based on the given HttpRequest tuple.
        
        :param request: A tuple containing the HTTP method and a URL template.
        :param params: A dictionary of parameters to format into the URL template.
        :param kwargs: Additional keyword arguments to pass to requests.request.
        :return: The HTTP response.
        """
        method, url_template = _request
        schema = 'https' if self.ssl else 'http'
        if params is None:
            params = {}
        # Fill in default values required by the template.
        url = url_template.format(schema=schema, host=self.host, port=self.port, **params)
        
        # Set up headers (e.g., add the API key for authentication)
        headers = kwargs.pop('headers', {})
        headers['X-Api-Key'] = self.api_key
        
        # Make the request using the provided method and URL.
        response = request(method, url, headers=headers, **kwargs,)
        response.raise_for_status()  # Optionally raise an exception for HTTP errors.
        return response

    def get_releases_page(self, page_num: int = 1, page_size: int = 50, include_artist:bool = True, monitored_only: bool = True, unique_tracks: bool = True) -> Generator[Release, None, None] | Generator[Tuple[int, ...], None, None]:
        # Example parameters for the endpoint URL.
        params = {
            'page_num': page_num,
            'page_size': page_size,
            'bool_include_artist': 'true' if include_artist else 'false',  # Ensure booleans are formatted as expected.
            'bool_monitored': 'true' if monitored_only else 'false',
        }
        response = self.do_request(self.ENDPOINT_WANTED_ALBUMS_MISSING, params=params)
        # Assuming the response is JSON containing album data:
        albums: Dict = response.json()
        page = page_num
        total_records = albums['totalRecords']
        total_pages = ceil(total_records / page_size)
        result = albums['records']
        yield page, total_pages
        for item in result:
            album_dataobject = Album.from_dict(item)
            track_title: Optional[str] = None
            for song in album_dataobject.releases:
                if unique_tracks and song.title != track_title:
                    yield song
                    track_title = song.title
                elif unique_tracks and song.title == track_title:
                    # Already have had the same song 
                    break
                else:
                    yield song
            

    def iter_all_release_pages(self) -> Generator[Release, None, None]:
        page_num: int = 1
        page_size: int = 50 
        max_page: int = 1
        current_page: int = 0
        while (current_page < max_page) or current_page == 0:
            for _release in self.get_releases_page(
                    page_num=page_num, page_size=page_size,
                    include_artist=True, monitored_only=True, unique_tracks=True):
                if isinstance(_release, tuple):
                    current_page, max_page = _release
                    page_num = current_page + 1
                elif isinstance(_release, Release):
                    yield _release

    def get_all_release_pages(self) -> List[Release]:
        return list(self.iter_all_release_pages())
                
# Example usage:
if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv('../.env')
    api = Api(host=environ['LIDARR_HOST'], port=int(environ['LIDARR_PORT']), api_key=environ['LIDARR_API'], ssl=bool(environ['LIDARR_SSL']))
    pprint(api.get_all_release_pages())
