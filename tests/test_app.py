import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
class AppTests(unittest.TestCase):
    def test_app_and_filters(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        app.sidebar.multiselect[0].set_value(['North']).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        app.sidebar.multiselect[0].set_value([]).run(timeout=30)
        self.assertEqual(len(app.exception),0)
if __name__=='__main__': unittest.main()
