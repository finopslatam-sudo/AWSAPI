import csv
from io import StringIO

def build_csv(headers: list, rows: list) -> bytes:
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return output.getvalue().encode("utf-8")
