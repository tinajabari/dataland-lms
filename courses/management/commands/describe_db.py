"""
چاپ ساختار دیتابیس SQL Server که جنگو به آن وصل است:
جدول‌ها، ستون‌ها، کلید اصلی، کلیدهای خارجی و تعداد ردیف‌ها.

این دستور فقط می‌خواند و چیزی را در دیتابیس تغییر نمی‌دهد؛
پس می‌توانید قبل از اجرای migrate با خیال راحت آن را اجرا کنید.

    python manage.py describe_db
    python manage.py describe_db --output schema.txt
    python manage.py describe_db --samples 3    # + چند ردیف نمونه (داده‌ی واقعی چاپ می‌شود)
"""
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

COLUMNS_SQL = """
SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE,
       c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS c
JOIN INFORMATION_SCHEMA.TABLES t
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
"""

PK_SQL = """
SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
 AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
ORDER BY kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.ORDINAL_POSITION
"""

FK_SQL = """
SELECT SCHEMA_NAME(tp.schema_id), tp.name, cp.name,
       SCHEMA_NAME(tr.schema_id), tr.name, cr.name
FROM sys.foreign_key_columns fkc
JOIN sys.tables  tp ON fkc.parent_object_id = tp.object_id
JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id
                   AND fkc.parent_column_id = cp.column_id
JOIN sys.tables  tr ON fkc.referenced_object_id = tr.object_id
JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id
                   AND fkc.referenced_column_id = cr.column_id
ORDER BY 1, 2
"""


def _quote(name):
    return '[' + str(name).replace(']', ']]') + ']'


def _short(value, limit=60):
    if isinstance(value, (bytes, bytearray)):
        return f'<{len(value)} bytes>'
    text = str(value).replace('\n', ' ').replace('\r', ' ')
    return text if len(text) <= limit else text[:limit] + '…'


class Command(BaseCommand):
    help = 'چاپ ساختار (جدول‌ها و ستون‌ها) دیتابیس SQL Server وصل‌شده'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default', help='نام دیتابیس در settings (پیش‌فرض: default)')
        parser.add_argument('--output', help='ذخیره‌ی خروجی در یک فایل متنی (UTF-8)')
        parser.add_argument('--samples', type=int, default=0,
                            help='تعداد ردیف نمونه از هر جدول (پیش‌فرض ۰ = بدون نمونه)')

    def handle(self, *args, **options):
        conn = connections[options['database']]
        if conn.vendor != 'microsoft':
            raise CommandError(
                f'این دستور فقط برای SQL Server است، ولی دیتابیس فعلی «{conn.vendor}» است.\n'
                'ابتدا MSSQL_NAME (و بقیه‌ی MSSQL_*) را در فایل .env تنظیم کنید.'
            )
        try:
            conn.ensure_connection()
        except Exception as exc:  # خطای اتصال: راهنمای ساده بدهیم
            raise CommandError(
                f'اتصال به SQL Server برقرار نشد:\n  {exc}\n\n'
                'بررسی کنید: ۱) سرویس SQL Server روشن است  ۲) MSSQL_HOST درست است (نام سرور در SSMS)\n'
                '۳) دیتابیس ریستور شده و MSSQL_NAME درست است  ۴) ODBC Driver 18 یا 17 نصب است.'
            )

        lines = []
        with conn.cursor() as cur:
            cur.execute('SELECT @@SERVERNAME, DB_NAME()')
            server, db_name = cur.fetchone()

            cur.execute(COLUMNS_SQL)
            columns = defaultdict(list)
            for schema, table, column, dtype, length, nullable in cur.fetchall():
                if length is not None and dtype in ('nvarchar', 'varchar', 'char', 'nchar', 'varbinary', 'binary'):
                    dtype = f'{dtype}({"max" if length == -1 else length})'
                columns[(schema, table)].append((column, dtype, nullable == 'YES'))

            cur.execute(PK_SQL)
            primary_keys = defaultdict(list)
            for schema, table, column in cur.fetchall():
                primary_keys[(schema, table)].append(column)

            cur.execute(FK_SQL)
            foreign_keys = defaultdict(list)
            for s1, t1, c1, s2, t2, c2 in cur.fetchall():
                foreign_keys[(s1, t1)].append(f'{c1} -> {s2}.{t2}.{c2}')

            lines.append(f'SERVER   : {server}')
            lines.append(f'DATABASE : {db_name}')
            lines.append(f'TABLES   : {len(columns)}')
            lines.append('')

            for (schema, table), cols in sorted(columns.items()):
                try:
                    cur.execute(f'SELECT COUNT(*) FROM {_quote(schema)}.{_quote(table)}')
                    rows = cur.fetchone()[0]
                except Exception as exc:
                    rows = f'? ({exc.__class__.__name__})'
                lines.append(f'== {schema}.{table}   (rows: {rows})')
                if primary_keys.get((schema, table)):
                    lines.append('   PK: ' + ', '.join(primary_keys[(schema, table)]))
                for name, dtype, nullable in cols:
                    lines.append(f'   - {name}  {dtype}  {"NULL" if nullable else "NOT NULL"}')
                for fk in foreign_keys.get((schema, table), []):
                    lines.append(f'   FK: {fk}')

                if options['samples'] > 0 and isinstance(rows, int) and rows:
                    try:
                        cur.execute(f'SELECT TOP ({int(options["samples"])}) * FROM {_quote(schema)}.{_quote(table)}')
                        names = [d[0] for d in cur.description]
                        for row in cur.fetchall():
                            pairs = ', '.join(f'{n}={_short(v)}' for n, v in zip(names, row))
                            lines.append(f'   · {pairs}')
                    except Exception as exc:
                        lines.append(f'   (نمونه قابل خواندن نبود: {exc.__class__.__name__})')
                lines.append('')

        text = '\n'.join(lines)
        if options['output']:
            with open(options['output'], 'w', encoding='utf-8') as fh:
                fh.write(text + '\n')
            self.stdout.write(self.style.SUCCESS(f'ساختار دیتابیس در فایل {options["output"]} ذخیره شد.'))
        else:
            self.stdout.write(text)
