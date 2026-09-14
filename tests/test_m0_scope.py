import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m0_scope import module as m
class ScopeTests(unittest.TestCase):
    def test_reject_invalid_limits(self):
        for value in (True, 0, -1, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validate_config({'max_questions': value, 'max_output_tokens': 10, 'max_bundle_chars': 100})
