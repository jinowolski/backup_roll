import os
import random
import shutil
import string
import tempfile
import unittest

import time

import datetime

from backup_roll import main


class TestBackupRoll(unittest.TestCase):

    def setUp(self):
        temp_local_dir_name = 'test_' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        self.test_dir = os.path.join(tempfile.gettempdir(), temp_local_dir_name)
        os.mkdir(self.test_dir, 0o700)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sandbox(self):
        stat = os.stat(self.test_dir)
        timestamp = int(time.time())
        ts2 = int(time.mktime(datetime.datetime(2018,2,1,21,16).timetuple()))
        dt = datetime.datetime.fromtimestamp(timestamp)
        os.utime(self.test_dir, (ts2, ts2))
        print('x')

