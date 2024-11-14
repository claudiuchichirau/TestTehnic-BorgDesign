import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from openai import OpenAI
from main import read_from_file, get_api_keys, create_client, check_assistant_exists, create_assistant, get_vector_store, create_vector_store, update_assistant_with_vector_store, create_and_poll_thread, wait_for_assistant_response


class TestDatabaseQueryAssistant(unittest.TestCase):
    
    @patch('builtins.open', new_callable=MagicMock)
    def test_read_from_file(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = ' something '

        result = read_from_file('test_text.txt')
        self.assertEqual(result, 'something')

    @patch('main.read_from_file')
    def test_get_api_keys(self, mock_read_from_file):
        mock_read_from_file.return_value = 'test_value'
        api_key, organization_id, project_id = get_api_keys()
        self.assertEqual(api_key, 'test_value')
        self.assertEqual(organization_id, 'test_value')
        self.assertEqual(project_id, 'test_value')

if __name__ == "__main__":
    unittest.main()
