"""Local UTF-8 CSV repair. All built-in examples are synthetic demonstrations."""
import argparse
import csv
import io
import json
from pathlib import Path
import sys

DEMO_INPUTS = {'synthetic-a.csv': 'id,name\n1, Ada \n2,Bob\n',
               'synthetic-b.csv': '\ufeffid,name\n1,Ada\n3,\n'}
DEMO_OUTPUT = 'id,name\n1,Ada\n2,Bob\n3,\n'
DEMO_REPORT = {
    'status': 'ok', 'synthetic_demo': True, 'trim_fields': True,
    'input_records': 4, 'output_records': 3, 'duplicates': 1,
    'changed_fields': 1,
    'records': [
        {'source': 'synthetic-a.csv', 'record': 2, 'line': 2, 'action': 'kept'},
        {'source': 'synthetic-a.csv', 'record': 3, 'line': 3, 'action': 'kept'},
        {'source': 'synthetic-b.csv', 'record': 2, 'line': 2, 'action': 'duplicate',
         'reason': 'exact processed field tuple', 'first': {'source': 'synthetic-a.csv', 'record': 2, 'line': 2}},
        {'source': 'synthetic-b.csv', 'record': 3, 'line': 3, 'action': 'kept'}]}

for _record in DEMO_REPORT['records']:
    _record['changed_fields'] = int(_record['source'] == 'synthetic-a.csv' and _record['record'] == 2)

DEMO_ERROR_REPORT = {'status': 'error', 'error': 'synthetic-invalid.csv: record 2, line 2: field count mismatch', 'synthetic_demo': True}

def strict_lines(stream, source):
    """Reject stray quotes too, which csv.reader(strict=True) accepts in bare fields."""
    state = 'start'
    for number, line in enumerate(stream, 1):
        if any(0xDC80 <= ord(char) <= 0xDCFF for char in line):
            raise UnicodeError('invalid UTF-8')
        for char in line:
            if state == 'quoted':
                if char == '"':
                    state = 'closed'
            elif char in '\r\n':
                state = 'start'
            elif state == 'closed':
                if char == '"':
                    state = 'quoted'
                elif char == ',':
                    state = 'start'
                else:
                    raise ValueError(f'{source}: line {number}: illegal CSV after closing quote')
            elif char == ',':
                state = 'start'
            elif char == '"':
                if state != 'start':
                    raise ValueError(f'{source}: line {number}: illegal CSV quote in unquoted field')
                state = 'quoted'
            else:
                state = 'plain'
        yield line


def repair(inputs, trim=False, synthetic=False):
    if not inputs:
        raise ValueError('at least one input is required')
    header = None
    rows, seen, records = [], {}, []
    for source in inputs:
        label = source.name if synthetic else str(source)
        with source.open(encoding='utf-8-sig', errors='surrogateescape', newline='') as stream:
            reader = csv.reader(strict_lines(stream, label), dialect='excel', strict=True)
            number = 0
            try:
                columns = next(reader, None)
                number = 1
                if not columns or any(not c.strip() for c in columns) or len(set(columns)) != len(columns):
                    raise ValueError(f'{label}: record 1: invalid empty or duplicate header')
                if header is None:
                    header = columns
                if columns != header:
                    raise ValueError(f'{label}: record 1: header names/order mismatch')
                for number, row in enumerate(reader, 2):
                    location = {'source': source.name if synthetic else str(source), 'record': number, 'line': reader.line_num}
                    if len(row) != len(header):
                        raise ValueError(f'{label}: record {number}, line {reader.line_num}: field count mismatch')
                    key = tuple(cell.strip() for cell in row) if trim else tuple(row)
                    changed = sum(before != after for before, after in zip(row, key))
                    if key in seen:
                        records.append(dict(location, action='duplicate', reason='exact processed field tuple', first=seen[key]))
                    else:
                        seen[key] = location
                        rows.append(key)
                        records.append(dict(location, action='kept'))
                    records[-1]['changed_fields'] = changed
            except csv.Error as exc:
                raise ValueError(f'{label}: record {number + 1}, line {reader.line_num}: illegal CSV') from exc
            except UnicodeError as exc:
                raise ValueError(f'{label}: record {number + 1}: invalid UTF-8') from exc
            except ValueError as exc:
                if str(exc).startswith(f'{label}: line '):
                    raise ValueError(f'{label}: record {number + 1}: illegal CSV quote') from exc
                raise
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue(), dict(status='ok', synthetic_demo=synthetic, trim_fields=trim,
                                   input_records=len(records), output_records=len(rows),
                                   duplicates=len(records)-len(rows),
                                   changed_fields=sum(r['changed_fields'] for r in records), records=records)


def write_new(path, text):
    # Only unlink a file that this call exclusively created, including write/close failures.
    stream = path.open('x', encoding='utf-8', newline='')
    try:
        with stream:
            stream.write(text)
    except BaseException:
        path.unlink()
        raise


def run(inputs, output, report, trim=False, synthetic=False):
    inputs = list(inputs)
    targets = [output.resolve(), report.resolve()]
    if len(set(targets)) != 2 or any(p in targets for p in (s.resolve() for s in inputs)):
        raise ValueError('output/report must be distinct and cannot overwrite inputs')
    if any(p.exists() or p.is_symlink() for p in (output, report)):
        raise ValueError('refusing to overwrite existing target')
    try:
        data, result = repair(inputs, trim, synthetic)
    except (ValueError, OSError, UnicodeError) as exc:
        try:
            write_new(report, json.dumps({'status': 'error', 'error': str(exc), 'synthetic_demo': synthetic}, indent=2)+'\n')
        except OSError as write_error:
            raise OSError(f'{exc}; failed to write error report: {write_error}') from write_error
        raise
    created = []
    try:
        # Exclusive creation protects existing paths, including concurrent writers.
        for path, text in ((output, data), (report, json.dumps(result, indent=2)+'\n')):
            write_new(path, text)
            created.append(path)
    except OSError as exc:
        for path in created:
            path.unlink()
        raise OSError('failed to write output/report: ' + str(exc)) from exc


def demo(directory):
    directory.mkdir(exist_ok=False)
    for name, data in DEMO_INPUTS.items():
        write_new(directory/name, data)
    write_new(directory/'expected.csv', DEMO_OUTPUT)
    write_new(directory/'expected-report.json', json.dumps(DEMO_REPORT, indent=2)+'\n')
    write_new(directory/'expected-error-report.json', json.dumps(DEMO_ERROR_REPORT, indent=2)+'\n')
    write_new(directory/'SYNTHETIC.txt', 'All files in this directory are synthetic demonstration data, never customer results.\n')
    run([directory/name for name in DEMO_INPUTS], directory/'actual.csv', directory/'report.json', True, True)
    write_new(directory/'synthetic-invalid.csv', 'id,name\n4\n')
    try:
        run([directory/'synthetic-invalid.csv'], directory/'invalid-output.csv', directory/'error-report.json', synthetic=True)
    except ValueError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='*', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--trim-fields', action='store_true')
    parser.add_argument('--demo', type=Path, help='create a new synthetic demonstration directory')
    args = parser.parse_args()
    if args.demo:
        if args.inputs or args.output or args.report or args.trim_fields:
            parser.error('--demo cannot be combined with repair arguments')
    elif not args.inputs or args.output is None or args.report is None:
        parser.error('inputs, --output and --report are required')
    try:
        if args.demo:
            demo(args.demo)
        else:
            run(args.inputs, args.output, args.report, args.trim_fields)
    except (OSError, ValueError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
