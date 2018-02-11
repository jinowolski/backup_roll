#!/usr/bin/env python

import argparse
import datetime
import logging
import os
import shutil
import sys

from os.path import isfile


class LessThanFilter(logging.Filter):
    """
    based on https://stackoverflow.com/a/31459386/532515
    """

    def __init__(self, exclusive_maximum, name=""):
        super(LessThanFilter, self).__init__(name)
        self.max_level = exclusive_maximum

    def filter(self, record):
        # non-zero return means we log this message
        return 1 if record.levelno < self.max_level else 0


class LoggerSetup():
    """
    based on https://stackoverflow.com/a/31459386/532515
    """
    initialized = False

    def __init__(self, level=logging.INFO):
        if not LoggerSetup.initialized:
            # Get the root logger
            logger = logging.getLogger()
            # Have to set the root logger level, it defaults to logging.WARNING
            logger.setLevel(logging.NOTSET)

            LoggerSetup.logging_handler_out = logging.StreamHandler(sys.stdout)
            LoggerSetup.logging_handler_out.addFilter(LessThanFilter(logging.WARNING))
            logger.addHandler(LoggerSetup.logging_handler_out)

            LoggerSetup.logging_handler_err = logging.StreamHandler(sys.stderr)
            logger.addHandler(LoggerSetup.logging_handler_err)

            LoggerSetup.initialized = True

        LoggerSetup.logging_handler_out.setLevel(level)
        LoggerSetup.logging_handler_err.setLevel(logging.WARNING if level <= logging.WARNING else level)


def ts2dt(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)


def ts2d(timestamp):
    return datetime.date.fromtimestamp(timestamp)


class Directory(object):

    def __init__(self, directory, offset_hours=0):
        logging.debug('Initializing {class_} at {workspace_dir}'.format(class_=self.__class__.__name__,
                                                                        workspace_dir=directory))
        self.directory = directory
        self.offset_hours = offset_hours
        self._listing = None

    def listing(self):
        if self._listing is None:
            self._listing = self._create_listing()
        return self._listing

    def _create_listing(self):
        if not os.path.isdir(self.directory):
            return {}
        paths = map(lambda filename: os.path.join(self.directory, filename),
                    os.listdir(self.directory))
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


class Workspace(Directory):

    def cleanup(self, dry_run=False):
        if not os.path.isdir(self.directory):
            return
        paths = map(lambda filename: os.path.join(self.directory, filename),
                    os.listdir(self.directory))
        for path in paths:
            if not isfile(path):
                continue
            logging.info("Deleting workspace file: {file}".format(file=path))
            if not dry_run:
                os.remove(path)


class Retention(Directory):

    def __init__(self, retention_dir, offset_hours=0):
        super(Retention, self).__init__(retention_dir, offset_hours)

    def filter_for_collect(self, dates):
        raise NotImplementedError()

    def filter_for_cleanup(self, dates):
        return set(dates) - set(self.filter_for_collect(dates))

    def collect(self, workspace, dry_run=False):
        """Copies files from workspace to the retention directory"""
        if not os.path.isdir(self.directory):
            logging.info("Creating directory {directory}".format(directory=self.directory))
            if not dry_run:
                mask = os.umask(0)
                os.umask(mask)
                perms = mask ^ 0o0777 # looks like os.mkdir ignores umask, so handle it manually
                os.mkdir(self.directory, perms)
        all_days = workspace.all_days()
        collect_days = self.filter_for_collect(all_days)
        for day in collect_days:
            files = workspace.list(day)
            for src in files:
                basename = os.path.basename(src)
                dest = os.path.join(self.directory, basename)
                logging.info("Copying {src} -> {dest}".format(src=src, dest=dest))
                if not dry_run:
                    shutil.copy(src, dest)
                    stat = os.stat(src)
                    os.utime(dest, (stat.st_atime, stat.st_mtime))

    def cleanup(self, dry_run=False):
        """Deletes old files from the retention directory"""
        all_days = self.all_days()
        cleanup_days = self.filter_for_cleanup(all_days)
        for day in cleanup_days:
            old_files = self.list(day)
            for old_file in old_files:
                logging.info("Deleting old file: {old_file}".format(old_file=old_file))
                if not dry_run:
                    os.remove(old_file)


class DailyRetention(Retention):

    def __init__(self, retention_dir, offset_hours=0, keep_days=30):
        """
        Daily retention

        :param retention_dir: Directory to store daily backups
        :param keep_days: How long in days files will be kept
        """
        super(DailyRetention, self).__init__(retention_dir, offset_hours)
        self.keep_days = keep_days

    def filter_for_collect(self, dates):
        min_date = datetime.datetime.now().date() - datetime.timedelta(days=self.keep_days)
        logging.debug("Minimal day for collecting daily files: {day}".format(day=min_date))
        return filter(lambda date: date > min_date, dates)


class WeeklyRetention(Retention):

    def __init__(self, retention_dir, offset_hours=0, keep_weeks=12, weekdays=(6,)):
        """
        Weekly retention

        :param retention_dir: Directory to store weekly backups
        :param keep_weeks: How long in weeks files will be kept
        :param weekdays: Iterable of weekdays to keep files. 0=monday..6=sunday
        """
        super(WeeklyRetention, self).__init__(retention_dir, offset_hours)
        self.keep_weeks = keep_weeks
        self.weekdays = weekdays

    def filter_for_collect(self, dates):
        min_date = datetime.datetime.now().date() - datetime.timedelta(days=self.keep_weeks * 7)
        logging.debug("Minimal day for collecting weekly files: {day}".format(day=min_date))
        return filter(lambda date: date > min_date and date.weekday() in self.weekdays, dates)


class MonthlyRetention(Retention):

    def __init__(self, retention_dir, offset_hours=0, keep_months=12, monthdays=(1,)):
        """
        Monthly retention

        :param retention_dir:  Directory to store monthly backups
        :param keep_months: How long in months files will be kept
        :param monthdays: Iterable of month days to collect backups from. Negative values indicates
        days number from the end of the month (-1 means 31 of Jan, 28 or 29 of Feb etc.)
        """
        super(MonthlyRetention, self).__init__(retention_dir, offset_hours)
        self.keep_months = keep_months
        self.monthdays = monthdays

    def _month_length(self, date):
        return ((date.replace(day=28) + datetime.timedelta(days=4)).replace(
            day=1) - datetime.timedelta(days=1)).day

    def filter_for_collect(self, dates):
        today = datetime.datetime.now().date()
        first = today.replace(day=1)
        n_months_ago = first.replace(year=first.year - ((self.keep_months + 12 - first.month) / 12),
                                     month=(first.month - self.keep_months - 1) % 12 + 1)
        diff = first - n_months_ago
        min_date = today - diff
        return filter(lambda date: date > min_date and (
                date.day in self.monthdays or (date.day - self._month_length(date)) - 1 in self.monthdays), dates)


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
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help='Do not print anything to stdout')
    args = parser.parse_args(args_)

    LoggerSetup(logging.INFO)
    if args.quiet:
        LoggerSetup(logging.WARNING)
    if args.verbose:
        LoggerSetup(logging.DEBUG)

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
    if args.monthdays:
        retentions.append(MonthlyRetention(retention_dir=args.monthly_dir,
                                           offset_hours=args.offset_hours,
                                           keep_months=args.monthly_retention,
                                           monthdays=args.monthdays))
    if args.weekdays:
        retentions.append(WeeklyRetention(retention_dir=args.weekly_dir,
                                          offset_hours=args.offset_hours,
                                          keep_weeks=args.weekly_retention,
                                          weekdays=args.weekdays))
    retentions.append(DailyRetention(retention_dir=args.daily_dir,
                                     offset_hours=args.offset_hours,
                                     keep_days=args.daily_retention))
    for retention in retentions:
        retention.collect(workspace, dry_run=args.dry_run)
        if not args.keep_old_backups:
            retention.cleanup(dry_run=args.dry_run)
    if not args.keep_workspace:
        workspace.cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    argv = sys.argv
    main(sys.argv[1:])
