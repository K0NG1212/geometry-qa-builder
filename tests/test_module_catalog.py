import unittest
from tools.export_modules import build


class ModuleCatalogTests(unittest.TestCase):
    def test_seven_real_implementations_exported_without_runtime_data(self):
        catalog = build()
        self.assertEqual([x['id'] for x in catalog['modules']], [f'M{i}' for i in range(7)])
        for module in catalog['modules']:
            self.assertTrue(module['limits'])
            files = {f['name']: f for f in module['files']}
            self.assertIn('def ', files['module.py']['content'])
            self.assertIn('schema.json', files)
            for file in files.values():
                self.assertTrue(file['path'].startswith('builder_modules/'))
                self.assertNotIn('runs/', file['path'])
