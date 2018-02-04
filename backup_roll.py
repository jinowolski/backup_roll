#!/usr/bin/env python

import argparse
import datetime
import os
import sys

from os.path import isfile


def ts2dt(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)


def ts2d(timestamp):
    return datetime.date.fromtimestamp(timestamp)


class Workspace(object):

    def __init__(self, workspace_dir, offset_hours=0):
        self.workspace_dir = workspace_dir
        self.offset_hours = offset_hours
        self._listing = None

    def listing(self):
        if self._listing is None:
            self._listing = self._create_listing()
        return self._listing

    def _create_listing(self):
        paths = map(lambda filename: os.path.join(self.workspace_dir, filename),
                        os.listdir(self.workspace_dir))
        listing = {}
        for path in paths:
            if not isfile(path):
                continue
            stat = os.stat(path)
            dt = ts2dt(stat.st_mtime) + datetime.timedelta(hours=self.offset_hours)
            d = dt.date()
            if d not in listing.keys():
                listing[d] = []
            listing[d].append(path)
        return listing

    def all_days(self):
        return self.listing().keys()

    def list(self, date):
        return self.listing().get(date, [])


class Retention(object):

    def __init__(self, retention_dir):
        self.retention_dir = retention_dir

    def collect(self, source_files):
        """Copies source_files to retention directory"""
        raise NotImplementedError()

    def cleanup(self):
        """Deletes old files from retention directory"""
        raise NotImplementedError()


class DailyRetention(Retention):

    def __init__(self, retention_dir, keep_days=30):
        """
        Daily retention

        :param retention_dir: Directory to store daily backups
        :param keep_days: How long in days files will be kept
        """
        super(DailyRetention, self).__init__(retention_dir)
        self.keep_days = keep_days


class WeeklyRetention(Retention):

    def __init__(self, retention_dir, keep_weeks=12, weekdays=(6,)):
        """
        Weekly retention

        :param retention_dir: Directory to store weekly backups
        :param keep_weeks: How long in weeks files will be kept
        :param weekdays: Iterable of weekdays to keep files. 0=monday..6=sunday
        """
        super(WeeklyRetention, self).__init__(retention_dir)
        self.keep_weeks = keep_weeks
        self.weekdays = weekdays


class MonthlyRetention(Retention):

    def __init__(self, retention_dir, keep_months=12, monthdays=(1,)):
        """
        Monthly retention

        :param retention_dir:  Directory to store monthly backups
        :param keep_months: How long in months files will be kept
        :param monthdays: Iterable of month days to collect backups from. Negative values indicates
        days number from the end of the month (-1 means 31 of Jan, 28 or 29 of Feb etc.)
        """
        super(MonthlyRetention, self).__init__(retention_dir)
        self.keep_months = keep_months
        self.monthdays = monthdays


def main(args_):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--workspace-dir', type=str,
                        help='Directory where backups are available initially. Files will be copied from this directory '
                             'to specific retentions\' directories. Defaults to current working directory.')
    parser.add_argument('-d', '--daily-dir', type=str,
                        help='Directory where daily backups will be copied to. Defaults to WORKSPACE_DIR/daily.')
    parser.add_argument('-w', '--weekly-dir', type=str,
                        help='Directory where weekly backups will be copied to. Defaults to WORKSPACE_DIR/weekly.')
    parser.add_argument('-m', '--monthly-dir', type=str,
                        help='Directory where monthly backups will be copied to. Defaults to WORKSPACE_DIR/monthly.')
    parser.add_argument('-D', '--daily-retention', default=30, type=int,
                        help='How many days daily backups will be kept before being deleted',
                        metavar='DAYS')
    parser.add_argument('-W', '--weekly-retention', default=12, type=int,
                        help='How many weeks weekly backups will be kept before being deleted',
                        metavar='WEEKS')
    parser.add_argument('-M', '--monthly-retention', default=12, type=int,
                        help='How many months monthly backups will be kept before being deleted',
                        metavar='MONTHS')
    parser.add_argument('--weekdays', default=[6], nargs='*', type=int,
                        help='Weekdays to store weekly backups. 1 is monday .. 7 is sunday. '
                             'Empty value disables weekly backups',
                        metavar='WEEKDAY')
    parser.add_argument('--monthdays', default=[1], nargs='*', type=int,
                        help='Monthdays to store monthly backups. Positive values equals days of months (1 to 31), '
                             'negative values means n-th day from the end of the month (-1 is 31st of Jan, but 28th '
                             'or 29th of Feb etc.). Empty value disables monthly backups',
                        metavar='MONTHDAY')
    parser.add_argument('-k', '--keep-old-backups', action='store_true',
                        help='Do not delete any old backups from retentions\' directories')
    parser.add_argument('-K', '--keep-workspace', action='store_true',
                        help='Do not delete files from workspace directory')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Do not copy or delete files, only print what would be done')
    parser.add_argument('-o', '--offset-hours', default=6, type=int,
                        help='Files created this number of hours before midnight will be treated as created the next '
                             'day. Useful if your nightly backup starts before midnight and you want always keep e.g. '
                             'saturday/sunday backup regardless it actually was finished slightly '
                             'before or after midnight',
                        metavar='HOURS')
    parser.add_argument('-q' '--quiet', action='store_true',
                        help='Do not print anything to stdout')
    args = parser.parse_args(args_)
    if args.workspace_dir is None:
        args.workspace_dir = os.getcwd()
    if args.daily_dir is None:
        args.daily_dir = os.path.join(args.workspace_dir, 'daily')
    if args.weekly_dir is None:
        args.weekly_dir = os.path.join(args.workspace_dir, 'weekly')
    if args.monthly_dir is None:
        args.monthly_dir = os.path.join(args.workspace_dir, 'monthly')

    workspace = Workspace(args.workspace_dir, args.offset_hours)
    retentions = []
    if parser.monthdays:
        retentions.append(MonthlyRetention(retention_dir=parser.monthly_dir,
                                           keep_months=parser.monthly_retention,
                                           monthdays=parser.monthdays))
    if parser.weekdays:
        retentions.append(WeeklyRetention(retention_dir=parser.weekly_dir,
                                          keep_months=parser.weekly_retention,
                                          weekdays=parser.weeklydays))
    retentions.append(DailyRetention(retention_dir=parser.daily_dir,
                                     keep_days=parser.daily_retention))


if __name__ == "__main__":
    main(sys.argv)
