# -*- coding: utf-8 -*-
import datetime
import logging
import os
import random
import shutil
import string
import tempfile
import time
import unittest

from backup_roll.backup_roll import Workspace, DailyRetention, LoggerSetup, WeeklyRetention, MonthlyRetention


class TestBackupRoll(unittest.TestCase):

    def setUp(self):
        LoggerSetup(logging.DEBUG)
        logging.debug("TEST {test}".format(test=self._testMethodName))
        temp_local_dir_name = 'test_' + ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        self.test_dir = os.path.join(tempfile.gettempdir(), temp_local_dir_name)
        os.mkdir(self.test_dir, 0o700)
        self.retention_dir = os.path.join(self.test_dir, 'retention')

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

    @staticmethod
    def _month_length(date):
        return ((date.replace(day=28) + datetime.timedelta(days=4)).replace(
            day=1) - datetime.timedelta(days=1)).day

    def _file(self, name, mtime, contents='test', basedir=None):
        if basedir is None:
            basedir = self.test_dir
        path = os.path.join(basedir, name)
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


class TestWorkspace(TestBackupRoll):

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
        self._file(os.path.join('testdir', 'testfile'), dt)

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


class TestDailyRetention(TestBackupRoll):

    def test_daily_creates_dir(self):
        self.assertFalse(os.path.exists(self.retention_dir), 'incorrect test prerequisites')
        self.assertFalse(os.path.isdir(self.retention_dir), 'incorrect test prerequisites')

        workspace = Workspace(self.test_dir)
        daily = DailyRetention(self.retention_dir)
        daily.collect(workspace)

        self.assertTrue(os.path.isdir(self.retention_dir), 'daily dir should be created')

    def test_daily_keeps_existing_dir(self):
        os.mkdir(self.retention_dir)
        self._file('old', datetime.datetime.now(), basedir=self.retention_dir)

        workspace = Workspace(self.test_dir)
        daily = DailyRetention(self.retention_dir)
        daily.collect(workspace)

        self.assertTrue(os.path.isdir(self.retention_dir), 'daily dir should exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'old')), 'old file should exist')

    def test_daily_collects_only_files_within_retention(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        before_midnight = midnight - datetime.timedelta(seconds=1)
        after_midnight = midnight + datetime.timedelta(seconds=1)
        self._file('midnight', midnight)
        self._file('before_midnight', before_midnight)
        self._file('after_midnight', after_midnight)

        workspace = Workspace(self.test_dir)
        daily = DailyRetention(self.retention_dir, keep_days=1)
        daily.collect(workspace)

        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'midnight')),
                        '"midnight" file should exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'before_midnight')),
                         '"before_midnight" file should not exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'after_midnight')),
                        '"after_midnight" file should exist')

    def test_daily_collects_only_files_regarding_offset(self):
        offsetted = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(
            hours=1)
        before_offsetted = offsetted - datetime.timedelta(seconds=1)
        after_offsetted = offsetted + datetime.timedelta(seconds=1)
        self._file('offsetted', offsetted)
        self._file('before_offsetted', before_offsetted)
        self._file('after_offsetted', after_offsetted)

        workspace = Workspace(self.test_dir, offset_hours=1)
        daily = DailyRetention(self.retention_dir, keep_days=1)
        daily.collect(workspace)

        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'offsetted')),
                        '"offsetted" file should exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'before_offsetted')),
                         '"before_offsetted" file should not exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'after_offsetted')),
                        '"after_offsetted" file should exist')

    def test_daily_deletes_only_files_outside_retention(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = midnight - datetime.timedelta(days=1)
        after_yesterday = yesterday + datetime.timedelta(seconds=1)
        before_midnight = midnight - datetime.timedelta(seconds=1)
        after_midnight = midnight + datetime.timedelta(seconds=1)
        self._file('yesterday', yesterday)
        self._file('after_yesterday', after_yesterday)
        self._file('midnight', midnight)
        self._file('before_midnight', before_midnight)
        self._file('after_midnight', after_midnight)
        given_workspace = Workspace(self.test_dir)
        given_daily = DailyRetention(self.retention_dir, keep_days=2)
        given_daily.collect(given_workspace)

        daily = DailyRetention(self.retention_dir, keep_days=1)
        daily.cleanup()

        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'yesterday')),
                         '"yesterday" file should not exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'after_yesterday')),
                         '"after_yesterday" file should not exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'before_midnight')),
                         '"before_midnight" file should not exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'midnight')),
                        '"midnight" file should exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'after_midnight')),
                        '"after_midnight" file should exist')

    def test_daily_deletes_only_files_regarding_offset(self):
        offsetted = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(
            hours=1)
        before_offsetted = offsetted - datetime.timedelta(seconds=1)
        after_offsetted = offsetted + datetime.timedelta(seconds=1)
        offsetted_yesterday = offsetted - datetime.timedelta(days=1)
        after_offseted_yesterday = offsetted_yesterday + datetime.timedelta(seconds=1)
        self._file('offsetted', offsetted)
        self._file('before_offsetted', before_offsetted)
        self._file('after_offsetted', after_offsetted)
        self._file('offsetted_yesterday', offsetted_yesterday)
        self._file('after_offseted_yesterday', after_offseted_yesterday)
        given_workspace = Workspace(self.test_dir, offset_hours=1)
        given_daily = DailyRetention(self.retention_dir, keep_days=2)
        given_daily.collect(given_workspace)

        daily = DailyRetention(self.retention_dir, offset_hours=1, keep_days=1)
        daily.cleanup()

        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'offsetted_yesterday')),
                         '"offsetted_yesterday" file should not exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'after_offseted_yesterday')),
                         '"after_offseted_yesterday" file should not exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'before_offsetted')),
                         '"before_offsetted" file should not exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'offsetted')),
                        '"offsetted" file should exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'after_offsetted')),
                        '"after_offsetted" file should exist')

    def test_daily_cleanup_works_without_retention_directory(self):
        self.assertFalse(os.path.exists(self.retention_dir), 'incorrect test prerequisites')
        self.assertFalse(os.path.isdir(self.retention_dir), 'incorrect test prerequisites')

        daily = DailyRetention(self.retention_dir)
        daily.cleanup()

        self.assertFalse(os.path.exists(self.retention_dir), 'path should not be created')


class TestWeeklyRetention(TestBackupRoll):

    def test_weekly_collects_only_within_retention(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(7):
            date = midnight - datetime.timedelta(days=i)
            self._file('minus_{i}'.format(i=i), date)

        workspace = Workspace(self.test_dir)
        weekly = WeeklyRetention(self.retention_dir, keep_weeks=1, weekdays=(0, 1, 2, 3, 4, 5, 6))
        weekly.collect(workspace)

        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'minus_7')),
                         'file created 7 days ago shoud not be copied')
        for i in range(6):
            self.assertTrue(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                            'file created {i} days ago shoud be copied'.format(i=i))

    def test_weekly_collects_only_selected_weekdays(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        weekdays = (2, 4, 6)
        expected_to_be_collected = []
        expected_to_be_skipped = []
        for i in range(6):
            date = midnight - datetime.timedelta(days=i)
            self._file('minus_{i}'.format(i=i), date)
            if date.weekday() in weekdays:
                expected_to_be_collected.append(i)
            else:
                expected_to_be_skipped.append(i)

        workspace = Workspace(self.test_dir)
        weekly = WeeklyRetention(self.retention_dir, keep_weeks=1, weekdays=weekdays)
        weekly.collect(workspace)

        for i in expected_to_be_collected:
            weekday = (midnight - datetime.timedelta(days=i)).weekday()
            self.assertTrue(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                            'file created on weekday {weekday} shoud be copied'.format(weekday=weekday))
        for i in expected_to_be_skipped:
            weekday = (midnight - datetime.timedelta(days=i)).weekday()
            self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                             'file created on weekday {weekday} shoud not be copied'.format(weekday=weekday))

    def test_weekly_collects_regarding_offset(self):
        offsetted = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(
            days=6, hours=1)
        before_offsetted = offsetted - datetime.timedelta(seconds=1)
        after_offsetted = offsetted + datetime.timedelta(seconds=1)
        self._file('offsetted', offsetted)
        self._file('before_offsetted', before_offsetted)
        self._file('after_offsetted', after_offsetted)

        workspace = Workspace(self.test_dir, offset_hours=1)
        weekly = WeeklyRetention(self.retention_dir, offset_hours=1, keep_weeks=1, weekdays=(0, 1, 2, 3, 4, 5, 6))
        weekly.collect(workspace)

        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'offsetted')),
                        '"offsetted" file should exist')
        self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'before_offsetted')),
                         '"before_offsetted" file should not exist')
        self.assertTrue(os.path.isfile(os.path.join(self.retention_dir, 'after_offsetted')),
                        '"after_offsetted" file should exist')


class TestMonthlyRetention(TestBackupRoll):

    def test_monthly_collects_one_month_within_retention(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(32):
            date = midnight - datetime.timedelta(days=i)
            self._file('minus_{i}'.format(i=i), date)

        workspace = Workspace(self.test_dir)
        monthly = MonthlyRetention(self.retention_dir, keep_months=1, monthdays=list(range(1, 32)))
        monthly.collect(workspace)

        last_month_length = TestBackupRoll._month_length(midnight.replace(day=1) - datetime.timedelta(days=1))
        for i in range(last_month_length, 32):
            self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                             'file created {i} days ago shoud not be copied'.format(i=i))
        for i in range(last_month_length):
            self.assertTrue(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                            'file created {i} days ago shoud be copied'.format(i=i))

    def test_monthly_collects_two_months_within_retention(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(64):
            date = midnight - datetime.timedelta(days=i)
            self._file('minus_{i}'.format(i=i), date)

        workspace = Workspace(self.test_dir)
        monthly = MonthlyRetention(self.retention_dir, keep_months=2, monthdays=list(range(1, 32)))
        monthly.collect(workspace)

        last_month_length = TestBackupRoll._month_length(midnight.replace(day=1) - datetime.timedelta(days=1))
        previous_month_length = TestBackupRoll._month_length(
            (midnight.replace(day=1) - datetime.timedelta(days=1)).replace(day=1) - datetime.timedelta(days=1))
        for i in range(last_month_length + previous_month_length, 64):
            self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                             'file created {i} days ago shoud not be copied'.format(i=i))
        for i in range(last_month_length + previous_month_length):
            self.assertTrue(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                            'file created {i} days ago shoud be copied'.format(i=i))

    def test_monthly_collects_only_selected_monthdays(self):
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        monthdays = (1,10,-1,-4)
        expected_to_be_collected = []
        expected_to_be_skipped = []
        last_month_length = TestBackupRoll._month_length(midnight.replace(day=1) - datetime.timedelta(days=1))
        for i in range(last_month_length):
            date = midnight - datetime.timedelta(days=i)
            self._file('minus_{i}'.format(i=i), date)
            if date.day in monthdays or date.day - (TestBackupRoll._month_length(date)) - 1 in monthdays:
                expected_to_be_collected.append(i)
            else:
                expected_to_be_skipped.append(i)

        workspace = Workspace(self.test_dir)
        monthly = MonthlyRetention(self.retention_dir, keep_months=1, monthdays=monthdays)
        monthly.collect(workspace)

        for i in expected_to_be_collected:
            day = (midnight - datetime.timedelta(days=i)).day
            self.assertTrue(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                            'file created on day {day} shoud be copied'.format(day=day))
        for i in expected_to_be_skipped:
            day = (midnight - datetime.timedelta(days=i)).day
            self.assertFalse(os.path.exists(os.path.join(self.retention_dir, 'minus_{i}'.format(i=i))),
                             'file created on day {day} shoud not be copied'.format(day=day))