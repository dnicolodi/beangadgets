import sys
import re

from beancount.parser import printer
from beancount.utils import misc_utils
from beancount.core import inventory
from beancount.core import data


class EntryPrinter(printer.EntryPrinter):
    def __init__(self, currency_column=66):
        super().__init__()
        self.target_currency_column = currency_column

    def Balance(self, entry, oss):
        amount = self.dformat.format(entry.amount.number, entry.amount.currency)

        # Render optional tolerance.
        tolerance = ''
        if entry.tolerance:
            tolerance = '~ {} '.format(self.dformat.format(entry.tolerance, entry.amount.currency))
            
        width = self.target_currency_column - len(amount) - len(tolerance) - len('0000-00-00 balance   ')
            
        oss.write(f'{entry.date} balance {entry.account:{width}s} {amount} {tolerance}{entry.amount.currency}\n')
        self.write_metadata(entry.meta, oss)

    def Open(self, entry, oss):
        currencies = ','.join(entry.currencies or [])
        booking = '"{}"'.format(entry.booking.name) if entry.booking is not None else ''
        oss.write(f'{entry.date} open {entry.account} {currencies} {booking}'.rstrip())
        oss.write('\n')
        self.write_metadata(entry.meta, oss)
        
    def Transaction(self, entry, oss):
        # Compute the string for the payee and narration line.
        strings = []
        if entry.payee:
            strings.append('"{}"'.format(misc_utils.escape_string(entry.payee)))
        if entry.narration:
            strings.append('"{}"'.format(misc_utils.escape_string(entry.narration)))
        elif entry.payee:
            # Ensure we append an empty string for narration if we have a payee.
            strings.append('""')

        oss.write('{e.date} {e.flag} {}\n'.format(' '.join(strings), e=entry))

        if entry.tags:            
            for tag in sorted(entry.tags):
                print(f'{self.prefix}#{tag}', file=oss)
        if entry.links:
            for link in sorted(entry.links):
                print(f'{self.prefix}^{link}', file=oss)
        
        self.write_metadata(entry.meta, oss)

        rows = [self.render_posting_strings(posting) for posting in entry.postings]
        strs_account = [row[0] for row in rows]
        strs_position, width_position = printer.align_position_strings(row[1] for row in rows)
        strs_weight, width_weight = printer.align_position_strings(row[2] for row in rows)

        width_number = re.search(r'[A-Z]', strs_position[0]).start()
        width_account = self.target_currency_column - width_number - len(self.prefix) - 2

        if self.render_weight and any(map(inventory.has_nontrivial_balance, entry.postings)):
            fmt = "{0}{{:{1}}}  {{:{2}}}  ; {{:{3}}}\n".format(
                self.prefix, width_account, width_position, width_weight).format
            for posting, account, position, weight in zip(entry.postings,
                                                          strs_account,
                                                          strs_position,
                                                          strs_weight):
                oss.write(fmt(account, position, weight))
                if posting.meta:
                    self.write_metadata(posting.meta, oss, '    ')
        else:
            fmt_str = "{0}{{:{1}}}  {{:{2}}}".format(
                self.prefix, width_account, max(1, width_position))
            fmt = fmt_str.format
            for posting, account, position in zip(entry.postings, strs_account, strs_position):
                print(fmt(account, position).rstrip(), file=oss)
                if posting.meta:
                    self.write_metadata(posting.meta, oss, '    ')


def print_entries(entries, output=sys.stdout):
    """A convenience function that prints a list of entries to a file.

    Args:
      entries: A list of directives.
      file: An optional file object to write the entries to.
    """
    if not entries:
        return

    printer = EntryPrinter()
    prev_entry_type = type(entries[0])

    for entry in entries:
        entry_type = type(entry)
        if (entry_type in (data.Transaction, data.Commodity) or entry_type is not prev_entry_type):
            output.write('\n')
            prev_entry_type = entry_type
        output.write(printer(entry))
