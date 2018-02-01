# backup-roll

Tool to roll backup files. 

Copies files from workspace directory to daily / weekly / monthly backup directories. Where 
file should be copied to is determined by it's modification time (mtime). Old files are deleted from each backup 
directory after specified retention time. Files are deleted also from workspace directory after copying them to backup 
directories. 

This script should work with pure python 2.7 or 3.4+. No additional libraries are required.

```
usage: backup_roll.py [-h] [-s WORKSPACE_DIR] [-d DAILY_DIR] [-w WEEKLY_DIR]
                      [-m MONTHLY_DIR] [-D DAYS] [-W WEEKS] [-M MONTHS]
                      [--weekdays [WEEKDAY [WEEKDAY ...]]]
                      [--monthdays [MONTHDAY [MONTHDAY ...]]] [-k] [-K] [-n]
                      [-o HOURS] [-q--quiet]

optional arguments:
  -h, --help            show this help message and exit
  -s WORKSPACE_DIR, --workspace-dir WORKSPACE_DIR
                        Directory where backups are available initially. Files
                        will be copied from this directory to specific
                        retentions' directories. Defaults to current working
                        directory. (default: None)
  -d DAILY_DIR, --daily-dir DAILY_DIR
                        Directory where daily backups will be copied to.
                        Defaults to WORKSPACE_DIR/daily. (default: None)
  -w WEEKLY_DIR, --weekly-dir WEEKLY_DIR
                        Directory where weekly backups will be copied to.
                        Defaults to WORKSPACE_DIR/weekly. (default: None)
  -m MONTHLY_DIR, --monthly-dir MONTHLY_DIR
                        Directory where monthly backups will be copied to.
                        Defaults to WORKSPACE_DIR/monthly. (default: None)
  -D DAYS, --daily-retention DAYS
                        How many days daily backups will be kept before being
                        deleted (default: 30)
  -W WEEKS, --weekly-retention WEEKS
                        How many weeks weekly backups will be kept before
                        being deleted (default: 12)
  -M MONTHS, --monthly-retention MONTHS
                        How many months monthly backups will be kept before
                        being deleted (default: 12)
  --weekdays [WEEKDAY [WEEKDAY ...]]
                        Weekdays to store weekly backups. 1 is monday .. 7 is
                        sunday. Empty value disables weekly backups (default:
                        [6])
  --monthdays [MONTHDAY [MONTHDAY ...]]
                        Monthdays to store monthly backups. Positive values
                        equals days of months (1 to 31), negative values means
                        n-th day from the end of the month (-1 is 31st of Jan,
                        but 28th or 29th of Feb etc.). Empty value disables
                        monthly backups (default: [1])
  -k, --keep-old-backups
                        Do not delete any old backups from retentions'
                        directories (default: False)
  -K, --keep-workspace  Do not delete files from workspace directory (default:
                        False)
  -n, --dry-run         Do not copy or delete files, only print what would be
                        done (default: False)
  -o HOURS, --offset-hours HOURS
                        Files created this number of hours before midnight
                        will be treated as created the next day. Useful if
                        your nightly backup starts before midnight and you
                        want always keep e.g. saturday/sunday backup
                        regardless it actually was finished slightly before or
                        after midnight (default: 6)
  -q--quiet             Do not print anything to stdout (default: False)
```