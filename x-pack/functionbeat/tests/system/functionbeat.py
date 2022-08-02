import os
import sys
from beat.beat import TestCase


class BaseTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.beat_name = "functionbeat"
        cls.beat_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../")
        )

        super(BaseTest, cls).setUpClass()
