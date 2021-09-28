from itertools import groupby
import click
import datetime
import sys
from beancount.parser import parser
from beancount.parser import printer
from beancount.core import data


def sortkey(entry):
    return (entry.date, data.SORT_ORDER.get(type(entry), 0))


def print_entries(entries, output=None):
    output = output or sys.stdout
    eprinter = printer.EntryPrinter(None, False)
    prev_entry_type = None
    
    for entry in entries:
        entry_type = type(entry)
        if entry_type in (data.Transaction, data.Commodity) or entry_type is not prev_entry_type:
            output.write('\n')
            prev_entry_type = entry_type

        string = eprinter(entry)
        output.write(string)


@click.command()
@click.argument('filename', nargs=-1)
def main(filename):

    entries = []
    for f in filename:
        this, errors, options = parser.parse_file(f)
        if errors:
            printer.print_errors(errors, sys.stderr)
            sys.exit(1)
        entries.extend(this)

    entries.sort(key=sortkey)

    entries_by_year_month = {}
    for key, group in groupby(entries, lambda entry: (entry.date.year, entry.date.month)):
        entries_by_year_month[key] = list(group)

    for year, keys in groupby(entries_by_year_month.keys(), lambda x: x[0]):
        print(f';;; {year:}')
        for k in keys:
            date = datetime.date(*k, 1)
            print(f';;;; {date:%Y %B}')
            print_entries(entries_by_year_month[k])
            print('')
        
if __name__ == '__main__':
    main()
