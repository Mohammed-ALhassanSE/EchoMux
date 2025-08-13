from PyQt6.QtCore import QSettings
from tmdbv3api import TMDb, TV

class ApiClient:
    def __init__(self):
        self.settings = QSettings("EchoMux", "EchoMux")
        self.tmdb = TMDb()
        self._configure_api()

    def _configure_api(self):
        api_key = self.settings.value("tmdb_api_key", "", type=str)
        if api_key:
            self.tmdb.api_key = api_key
            self.tmdb.language = 'en'
            self.tmdb.debug = False
            return True
        return False

    def is_configured(self):
        return bool(self.tmdb.api_key)

    def search_show(self, show_name):
        if not self.is_configured():
            return None
        try:
            tv = TV()
            results = tv.search(show_name)
            if results:
                return results[0]  # Return the most likely result
            return None
        except Exception as e:
            print(f"Error searching for show '{show_name}': {e}")
            return None

    def get_episode_title(self, show_id, season_number, episode_number):
        if not self.is_configured():
            return None
        try:
            tv = TV()
            episode = tv.episode_details(show_id, season_number, episode_number)
            if episode and 'name' in episode:
                return episode['name']
            return None
        except Exception as e:
            print(f"Error getting episode title for S{season_number}E{episode_number}: {e}")
            return None
