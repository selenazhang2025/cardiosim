import unittest

from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    def test_initial_page_renders_without_exceptions(self):
        app = AppTest.from_file("app.py").run(timeout=15)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            app.title[0].value, "CardioSim — 10-year ASCVD Risk Simulator"
        )
        self.assertEqual(len(app.slider), 8)
        self.assertEqual(len(app.checkbox), 6)
        self.assertEqual(len(app.button), 4)


if __name__ == "__main__":
    unittest.main()
