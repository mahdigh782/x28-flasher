"""HTTPS trust and error handling; no external network access needed."""
import ssl
import sys
import types
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import images


class HttpsTests(unittest.TestCase):
    def test_requests_keep_certificate_and_hostname_verification(self):
        with patch.object(images.urllib.request, 'urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'ok'
            self.assertEqual(images.get('https://example.com'), b'ok')
        context = open_url.call_args.kwargs['context']
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertEqual(open_url.call_args.kwargs['timeout'], 60)

    def test_frozen_app_adds_the_bundled_roots_to_the_default_context(self):
        context = MagicMock()
        certifi = types.SimpleNamespace(where=lambda: '/bundle/certifi/cacert.pem')
        with patch.object(images.sys, 'frozen', True, create=True), patch.dict(sys.modules, {'certifi': certifi}), \
             patch.object(images.ssl, 'create_default_context', return_value=context) as default_context, \
             patch.object(images.urllib.request, 'urlopen') as open_url:
            images.get('https://example.com')
        default_context.assert_called_once_with()
        context.load_verify_locations.assert_called_once_with('/bundle/certifi/cacert.pem')
        self.assertIs(open_url.call_args.kwargs['context'], context)

    def test_network_failures_become_reportable_errors_without_an_insecure_retry(self):
        error = urllib.error.URLError('certificate verify failed')
        with patch.object(images.urllib.request, 'urlopen', side_effect=error) as open_url:
            with self.assertRaisesRegex(RuntimeError, 'https://example.com.*certificate verify failed'):
                images.get('https://example.com')
        self.assertEqual(open_url.call_count, 1)


if __name__ == '__main__':
    unittest.main()
