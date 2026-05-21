"""Clean sql utility."""
import re
from .clean_ascii_code import clean_ascii_code


def clean_sql(str):
    """Sanitize a string for use as a SQLite column name, rejecting reserved words.

    Applies clean_ascii_code first (special chars to mnemonics), then checks
    against the full SQLite reserved keyword list. Used to ensure that channel
    names from instruments can safely become database column names.

    >>> clean_sql('my_channel')
    'my_channel'
    >>> clean_sql('voltage_1')
    'voltage_1'
    >>> clean_sql('SELECT')
    Traceback (most recent call last):
        ...
    Exception: Found "SELECT" reserved keyword in c cleaned string: "SELECT"

    Args:
        str: Input string (will be run through clean_ascii_code first).

    Raises:
        Exception: If the cleaned result contains a SQLite reserved keyword.
    """
    str = clean_ascii_code(str)

    sql_reserved = [
        # https://www.sqlite.org/lang_keywords.html
        'ABORT',
        'ACTION',
        'ADD',
        'AFTER',
        'ALL',
        'ALTER',
        'ANALYZE',
        'AND',
        'AS',
        'ASC',
        'ATTACH',
        'AUTOINCREMENT',
        'BEFORE',
        'BEGIN',
        'BETWEEN',
        'BY',
        'CASCADE',
        'CASE',
        'CAST',
        'CHECK',
        'COLLATE',
        'COLUMN',
        'COMMIT',
        'CONFLICT',
        'CONSTRAINT',
        'CREATE',
        'CROSS',
        'CURRENT_DATE',
        'CURRENT_TIME',
        'CURRENT_TIMESTAMP',
        'DATABASE',
        'DEFAULT',
        'DEFERRABLE',
        'DEFERRED',
        'DELETE',
        'DESC',
        'DETACH',
        'DISTINCT',
        'DROP',
        'EACH',
        'ELSE',
        'END',
        'ESCAPE',
        'EXCEPT',
        'EXCLUSIVE',
        'EXISTS',
        'EXPLAIN',
        'FAIL',
        'FOR',
        'FOREIGN',
        'FROM',
        'FULL',
        'GLOB',
        'GROUP',
        'HAVING',
        'IF',
        'IGNORE',
        'IMMEDIATE',
        'IN',
        'INDEX',
        'INDEXED',
        'INITIALLY',
        'INNER',
        'INSERT',
        'INSTEAD',
        'INTERSECT',
        'INTO',
        'IS',
        'ISNULL',
        'JOIN',
        'KEY',
        'LEFT',
        'LIKE',
        'LIMIT',
        'MATCH',
        'NATURAL',
        'NO',
        'NOT',
        'NOTNULL',
        'NULL',
        'OF',
        'OFFSET',
        'ON',
        'OR',
        'ORDER',
        'OUTER',
        'PLAN',
        'PRAGMA',
        'PRIMARY',
        'QUERY',
        'RAISE',
        'RECURSIVE',
        'REFERENCES',
        'REGEXP',
        'REINDEX',
        'RELEASE',
        'RENAME',
        'REPLACE',
        'RESTRICT',
        'RIGHT',
        'ROLLBACK',
        'ROW',
        'SAVEPOINT',
        'SELECT',
        'SET',
        'TABLE',
        'TEMP',
        'TEMPORARY',
        'THEN',
        'TO',
        'TRANSACTION',
        'TRIGGER',
        'UNION',
        'UNIQUE',
        'UPDATE',
        'USING',
        'VACUUM',
        'VALUES',
        'VIEW',
        'VIRTUAL',
        'WHEN',
        'WHERE',
        'WITH',
        'WITHOUT',
    ]

    for res in sql_reserved:
        if re.search(r'\b{}\b'.format(res), str) is not None:
            raise Exception(
                'Found "{}" reserved keyword in c cleaned string: "{}"'.format(
                    res, str))

    return str
