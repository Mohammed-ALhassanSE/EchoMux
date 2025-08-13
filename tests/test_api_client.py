import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from echomux.api_client import ApiClient

class TestApiClient(unittest.TestCase):

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.QSettings')
    def test_init_no_api_key(self, mock_qsettings, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = ""

        # We need to mock the api_key property on the TMDb instance
        type(mock_tmdb.return_value).api_key = PropertyMock(return_value=None)

        # Action
        client = ApiClient()

        # Assert
        self.assertFalse(client.is_configured())

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.QSettings')
    def test_init_with_api_key(self, mock_qsettings, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = "fake_api_key"

        # Action
        client = ApiClient()

        # Assert
        # The test for is_configured is tricky now because api_key is set on the mock
        # A better test is to see if the property was set
        self.assertEqual(mock_tmdb.return_value.api_key, "fake_api_key")

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.TV')
    @patch('echomux.api_client.QSettings')
    def test_search_show_success(self, mock_qsettings, mock_tv, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = "fake_api_key"
        type(mock_tmdb.return_value).api_key = PropertyMock(return_value="fake_api_key")

        mock_tv_instance = mock_tv.return_value
        mock_show = MagicMock()
        mock_show.id = 123
        mock_show.name = "Test Show"
        mock_tv_instance.search.return_value = [mock_show]

        client = ApiClient()

        # Action
        result = client.search_show("Test Show")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 123)
        mock_tv_instance.search.assert_called_once_with("Test Show")

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.TV')
    @patch('echomux.api_client.QSettings')
    def test_search_show_not_found(self, mock_qsettings, mock_tv, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = "fake_api_key"
        type(mock_tmdb.return_value).api_key = PropertyMock(return_value="fake_api_key")

        mock_tv_instance = mock_tv.return_value
        mock_tv_instance.search.return_value = []

        client = ApiClient()

        # Action
        result = client.search_show("Unknown Show")

        # Assert
        self.assertIsNone(result)

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.TV')
    @patch('echomux.api_client.QSettings')
    def test_get_episode_title_success(self, mock_qsettings, mock_tv, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = "fake_api_key"
        type(mock_tmdb.return_value).api_key = PropertyMock(return_value="fake_api_key")

        mock_tv_instance = mock_tv.return_value
        mock_episode = {'name': 'The Pilot'}
        mock_tv_instance.episode_details.return_value = mock_episode

        client = ApiClient()

        # Action
        title = client.get_episode_title(123, 1, 1)

        # Assert
        self.assertEqual(title, "The Pilot")
        mock_tv_instance.episode_details.assert_called_once_with(123, 1, 1)

    @patch('echomux.api_client.TMDb')
    @patch('echomux.api_client.TV')
    @patch('echomux.api_client.QSettings')
    def test_get_episode_title_not_found(self, mock_qsettings, mock_tv, mock_tmdb):
        # Setup
        mock_settings_instance = mock_qsettings.return_value
        mock_settings_instance.value.return_value = "fake_api_key"
        type(mock_tmdb.return_value).api_key = PropertyMock(return_value="fake_api_key")

        mock_tv_instance = mock_tv.return_value
        mock_tv_instance.episode_details.return_value = None

        client = ApiClient()

        # Action
        title = client.get_episode_title(123, 1, 99)

        # Assert
        self.assertIsNone(title)

if __name__ == '__main__':
    unittest.main()
