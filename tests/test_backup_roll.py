# -*- coding: utf-8 -*-
import os
import random
import shutil
import string
import tempfile
import unittest

import time

import datetime

from backup_roll import main, Workspace


class TestBackupRoll(unittest.TestCase):

    def setUp(self):
        temp_local_dir_name = 'test_' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        self.test_dir = os.path.join(tempfile.gettempdir(), temp_local_dir_name)
        os.mkdir(self.test_dir, 0o700)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @staticmethod
    def _dt2ts(dt):
        return int(time.mktime(dt.timetuple()))

    @staticmethod
    def _dt2d(dt):
        return datetime.date(dt.year, dt.month, dt.day)

    @staticmethod
    def _now():
        return int(time.time())

    def _file(self, name, mtime, contents='test'):
        path = os.path.join(self.test_dir, name)
        if isinstance(mtime, datetime.datetime):
            mtime = TestBackupRoll._dt2ts(mtime)
        f = open(path, 'w')
        f.write(contents)
        f.close()
        os.utime(path, (TestBackupRoll._now(), mtime))

    def _dir(self, name, mtime):
        path = os.path.join(self.test_dir, name)
        if isinstance(mtime, datetime.datetime):
            mtime = TestBackupRoll._dt2ts(mtime)
        os.mkdir(path)
        os.utime(path, (TestBackupRoll._now(), mtime))

    def test_workspace_dates_empty(self):
        pass

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        self.assertEqual(0, len(result))

    def test_workspace_dates_single(self):
        dt = datetime.datetime(2000, 12, 31)
        self._file('test', dt)

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        d = TestBackupRoll._dt2d(dt)
        self.assertSetEqual(set([d]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_dates_two(self):
        dt1 = datetime.datetime(2000, 12, 31)
        dt2 = datetime.datetime(2000, 12, 30)
        self._file('test1', dt1)
        self._file('test2', dt2)

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        d1 = TestBackupRoll._dt2d(dt1)
        d2 = TestBackupRoll._dt2d(dt2)
        self.assertSetEqual(set([d1, d2]), set(result))
        self.assertEqual(2, len(result))

    def test_workspace_dates_dir_doesnt_count(self):
        dt = datetime.datetime(2000, 12, 31)
        self._dir('test', dt)

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        self.assertEqual(0, len(result))

    def test_workspace_dates_nested_file_doesnt_count(self):
        dt = datetime.datetime(2000, 12, 31)
        self._dir('testdir', dt)
        self._file(os.path.join('testdir','testfile'), dt)

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        self.assertEqual(0, len(result))

    def test_workspace_dates_no_offset_by_default(self):
        dt1 = datetime.datetime(2000, 12, 31, 0, 0, 0)
        dt2 = datetime.datetime(2000, 12, 31, 23, 59, 59)
        self._file('first', dt1)
        self._file('last', dt2)

        workspace = Workspace(self.test_dir)
        result = workspace.all_days()

        d = TestBackupRoll._dt2d(dt1)
        self.assertSetEqual(set([d]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_dates_positive_offset(self):
        dt1 = datetime.datetime(2000, 12, 30, 23, 0, 0)
        dt2 = datetime.datetime(2000, 12, 31, 22, 59, 59)
        self._file('first', dt1)
        self._file('last', dt2)

        offset = 1
        workspace = Workspace(self.test_dir, offset)
        result = workspace.all_days()

        d = datetime.date(2000, 12, 31)
        self.assertSetEqual(set([d]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_dates_negative_offset(self):
        dt1 = datetime.datetime(2000, 12, 30, 1, 0, 0)
        dt2 = datetime.datetime(2000, 12, 31, 0, 59, 59)
        self._file('first', dt1)
        self._file('last', dt2)

        offset = -1
        workspace = Workspace(self.test_dir, offset)
        result = workspace.all_days()

        d = datetime.date(2000, 12, 30)
        self.assertSetEqual(set([d]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_list_non_existing_date(self):
        pass

        workspace = Workspace(self.test_dir)
        d = datetime.date(2000, 12, 30)
        result = workspace.list(d)

        self.assertEqual(0, len(result))

    def test_workspace_list_date_single(self):
        dt = datetime.datetime(2000, 12, 31)
        self._file('test', dt)

        workspace = Workspace(self.test_dir)
        d = datetime.date(2000, 12, 31)
        result = workspace.list(d)

        self.assertSetEqual(set([os.path.join(self.test_dir, 'test')]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_list_date_two(self):
        dt = datetime.datetime(2000, 12, 31)
        self._file('test1', dt)
        self._file('test2', dt)

        workspace = Workspace(self.test_dir)
        d = datetime.date(2000, 12, 31)
        result = workspace.list(d)

        self.assertSetEqual(set([
            os.path.join(self.test_dir, 'test1'),
            os.path.join(self.test_dir, 'test2'),
        ]), set(result))
        self.assertEqual(2, len(result))

    def test_workspace_list_excludes_dirs(self):
        dt = datetime.datetime(2000, 12, 31)
        self._dir('testdir', dt)
        self._file('testfile', dt)

        workspace = Workspace(self.test_dir)
        d = datetime.date(2000, 12, 31)
        result = workspace.list(d)

        self.assertSetEqual(set([os.path.join(self.test_dir, 'testfile')]), set(result))
        self.assertEqual(1, len(result))

    def test_workspace_list_uses_offset(self):
        dt1 = datetime.datetime(2000, 12, 30, 23, 0, 0)
        dt2 = datetime.datetime(2000, 12, 31, 22, 59, 59)
        dt3 = datetime.datetime(2000, 12, 31, 23, 0, 0)
        self._file('first', dt1)
        self._file('last', dt2)
        self._file('next', dt3)

        offset = 1
        workspace = Workspace(self.test_dir, offset)
        d = datetime.date(2000, 12, 31)
        result = workspace.list(d)

        self.assertSetEqual(set([
            os.path.join(self.test_dir, 'first'),
            os.path.join(self.test_dir, 'last'),
        ]), set(result))
        self.assertEqual(2, len(result))


    # Nie wywala się, gdy nie ma plików w workspace
    # Nie kasuje plików, których nie powinien
    # Przenosi pliki, które powinien
    # Kasuje pliki, które powinien
    # Nie przenosi plików, których nie powinien
    # Uwzględnia zmienne konfiguracyjne

