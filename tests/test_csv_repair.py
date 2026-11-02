"""Exercise the delivered command in subprocesses and disposable directories."""
import csv
import io
import importlib.util
from unittest.mock import patch
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1]/'csv_repair.py'
spec = importlib.util.spec_from_file_location('csv_repair', CLI)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CSVTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root/'out.csv'
        self.report = self.root/'report.json'

    def invoke(self, *args):
        return subprocess.run([sys.executable, '-B', str(CLI), *map(str, args)], capture_output=True, text=True)

    def source(self, name, data):
        p = self.root/name
        p.write_bytes(data.encode('utf-8'))
        return p

    def repair(self, *inputs, trim=False):
        args = [*inputs, '--output', self.out, '--report', self.report]
        if trim:
            args.append('--trim-fields')
        return self.invoke(*args)

    def test_merge_preserves_text_and_first_order(self):
        a = self.source('a.csv', '\ufeffid,value\n1, x \n2,\n1, x \n')
        b = self.source('b.csv', 'id,value\n1,x\n2,\n3,"multi\nline"\n')
        result = self.repair(a, b)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_text(), 'id,value\n1, x \n2,\n1,x\n3,"multi\nline"\n')
        report = json.loads(self.report.read_text())
        self.assertEqual([report[k] for k in ('input_records','output_records','duplicates')], [6,4,2])
        self.assertEqual(report['records'][2]['reason'], 'exact processed field tuple')
        self.assertEqual(report['records'][2]['first'], {'source':str(a),'record':2,'line':2})
        self.assertEqual(report['records'][-1]['line'], 5)
        self.assertEqual(a.read_bytes(), '\ufeffid,value\n1, x \n2,\n1, x \n'.encode())

    def test_quoted_commas_escaped_quotes_crlf_and_header_only(self):
        a = self.source('a.csv', 'id,value\r\n1,"a,b"\r\n2,"say ""hi"""\r\n')
        empty = self.source('empty.csv', 'id,value\r\n')
        result = self.repair(a, empty)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_text(), 'id,value\n1,"a,b"\n2,"say ""hi"""\n')
        self.assertEqual(json.loads(self.report.read_text())['output_records'], 2)

    def test_explicit_trimming_deduplicates_without_filling(self):
        a = self.source('a.csv', 'id,value\n1, x \n1,x\n2,  \n')
        result = self.repair(a, trim=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_text(), 'id,value\n1,x\n2,\n')
        self.assertEqual(json.loads(self.report.read_text())['duplicates'], 1)

    def test_invalid_inputs_have_report_without_partial_output(self):
        valid = self.source('valid.csv', 'id,value\n1,ok\n')
        for data in ('value,id\nx,2\n', 'id,other\n2,x\n', 'id,id\n2,x\n',
                     'id, \n2,x\n', '', 'id,value\n2\n', 'id,value\n2,x,extra\n',
                     'id,value\n2,"unclosed\n', 'id,value\n2,"x"bad\n', 'id,value\n2,bad"quote\n', 'id,value\n\n'):
            with self.subTest(data=data):
                bad = self.source('bad.csv', data)
                result = self.repair(valid, bad)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr)
                self.assertFalse(self.out.exists())
                report = json.loads(self.report.read_text())
                self.assertEqual(report['status'], 'error')
                self.assertIn('bad.csv', report['error'])
                self.report.unlink()

    def test_invalid_utf8(self):
        p = self.root/'bad.csv'
        p.write_bytes(b'id\nvalid\n\xff\n')
        result = self.repair(p)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('record 3: invalid UTF-8', result.stderr)
        self.assertFalse(self.out.exists())
        self.assertEqual(json.loads(self.report.read_text())['status'], 'error')

    def test_no_overwrite_or_path_alias(self):
        a = self.source('a.csv', 'id\n1\n')
        for target in (self.out, self.report):
            target.write_text('existing')
            self.assertNotEqual(self.repair(a).returncode, 0)
            self.assertEqual(target.read_text(), 'existing')
            self.assertFalse((self.report if target == self.out else self.out).exists())
            target.unlink()
        for output, report in ((a,self.report), (self.out,a), (self.out,self.out)):
            self.assertNotEqual(self.invoke(a,'--output',output,'--report',report).returncode, 0)
            self.assertEqual(a.read_text(), 'id\n1\n')
        self.out.symlink_to(a)
        self.assertNotEqual(self.repair(a).returncode, 0)
        self.assertEqual(a.read_text(), 'id\n1\n')

    def test_demo_actual_matches_expected_and_is_synthetic(self):
        demo = self.root/'demo'
        result = self.invoke('--demo', demo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((demo/'expected.csv').read_bytes(), (demo/'actual.csv').read_bytes())
        self.assertEqual(json.loads((demo/'expected-report.json').read_text()), json.loads((demo/'report.json').read_text()))
        self.assertEqual((demo/'expected-report.json').read_bytes(), (demo/'report.json').read_bytes())
        self.assertTrue(json.loads((demo/'report.json').read_text())['synthetic_demo'])
        self.assertTrue(json.loads((demo/'error-report.json').read_text())['synthetic_demo'])
        self.assertEqual(json.loads((demo/'error-report.json').read_text()), json.loads((demo/'expected-error-report.json').read_text()))
        self.assertFalse((demo/'invalid-output.csv').exists())
        self.assertIn('synthetic', (demo/'SYNTHETIC.txt').read_text())
        self.assertNotEqual(self.invoke('--demo',demo).returncode, 0)

    def test_empty_fields_unicode_and_logical_records(self):
        a = self.source('a.csv', '\ufeffid,value\n,\n  , \n甲,"逗号,与\n换行"\n')
        before = a.read_bytes()
        result = self.repair(a, trim=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.reader(io.StringIO(self.out.read_text())))
        self.assertEqual(rows, [['id', 'value'], ['', ''], ['甲', '逗号,与\n换行']])
        report = json.loads(self.report.read_text())
        self.assertEqual(report['input_records'], report['output_records'] + report['duplicates'])
        self.assertEqual(report['changed_fields'], 2)
        self.assertEqual([r['record'] for r in report['records']], [2, 3, 4])
        self.assertEqual(report['records'][-1]['line'], 5)
        self.assertEqual(a.read_bytes(), before)

    def test_header_only_and_zero_inputs(self):
        a = self.source('a.csv', 'id,value\n')
        self.assertEqual(self.repair(a).returncode, 0)
        self.assertEqual(self.out.read_text(), 'id,value\n')
        self.assertEqual(json.loads(self.report.read_text())['input_records'], 0)
        with self.assertRaisesRegex(ValueError, 'at least one input'):
            module.repair([])

    def test_relative_and_directory_symlink_aliases(self):
        a = self.source('a.csv', 'id\n1\n')
        alias = self.root/'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        for target in (self.root/'..'/self.root.name/'a.csv', alias/'a.csv'):
            result = self.invoke(a, '--output', target, '--report', self.report)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.report.exists())
            self.assertEqual(a.read_bytes(), b'id\n1\n')

    def test_missing_input_is_reported(self):
        result = self.repair(self.root/'missing.csv')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing.csv', result.stderr)
        self.assertFalse(self.out.exists())
        self.assertEqual(json.loads(self.report.read_text())['status'], 'error')

    def test_write_and_close_failures_clean_only_new_files(self):
        a = self.source('a.csv', 'id\n1\n')
        existing = self.source('existing.csv', 'untouched')
        real_open = Path.open
        for target in (self.out, self.report):
            for stage in ('write', 'close'):
                with self.subTest(target=target, stage=stage):
                    class Broken:
                        def __init__(self, stream):
                            self.stream = stream
                        def __enter__(self):
                            return self
                        def write(self, text):
                            self.stream.write(text[:3])
                            if stage == 'write':
                                raise OSError('simulated write failure')
                        def __exit__(self, *args):
                            self.stream.close()
                            if stage == 'close':
                                raise OSError('simulated close failure')
                    def opening(path, *args, **kwargs):
                        stream = real_open(path, *args, **kwargs)
                        return Broken(stream) if path == target else stream
                    stderr = io.StringIO()
                    with patch.object(Path, 'open', opening), patch.object(sys, 'argv',
                            [str(CLI), str(a), '--output', str(self.out), '--report', str(self.report)]), patch.object(sys, 'stderr', stderr):
                        self.assertEqual(module.main(), 1)
                    self.assertIn('failed to write output/report', stderr.getvalue())
                    self.assertFalse(self.out.exists())
                    self.assertFalse(self.report.exists())
                    self.assertEqual(a.read_bytes(), b'id\n1\n')
                    self.assertEqual(existing.read_text(), 'untouched')

    def test_arguments_required(self):
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertNotEqual(self.invoke('--demo',self.root/'demo','--trim-fields').returncode, 0)

    def test_read_failure_reports_source_without_field_contents(self):
        a = self.source('a.csv', 'id\nprivate-value\n')
        before = a.read_bytes()
        real_open = Path.open

        def opening(path, *args, **kwargs):
            if path == a:
                raise PermissionError(f'{path}: simulated read failure')
            return real_open(path, *args, **kwargs)

        with patch.object(Path, 'open', opening):
            with self.assertRaisesRegex(OSError, 'simulated read failure'):
                module.run([a], self.out, self.report)
        diagnostic = json.loads(self.report.read_text())
        self.assertEqual(diagnostic['status'], 'error')
        self.assertIn(str(a), diagnostic['error'])
        self.assertNotIn('private-value', diagnostic['error'])
        self.assertFalse(self.out.exists())
        self.assertEqual(a.read_bytes(), before)

    def test_create_failure_and_error_report_failure_exit_nonzero(self):
        a = self.source('a.csv', 'id\n1\n')
        real_open = Path.open
        for invalid in (False, True):
            if invalid:
                a.write_bytes(b'id\nsecret,extra\n')
            before = a.read_bytes()

            def opening(path, *args, **kwargs):
                if path == self.report:
                    raise PermissionError('simulated create failure')
                return real_open(path, *args, **kwargs)

            stderr = io.StringIO()
            with patch.object(Path, 'open', opening), patch.object(sys, 'argv',
                    [str(CLI), str(a), '--output', str(self.out), '--report', str(self.report)]), patch.object(sys, 'stderr', stderr):
                self.assertEqual(module.main(), 1)
            self.assertIn('failed to write', stderr.getvalue())
            if invalid:
                self.assertIn('record 2', stderr.getvalue())
                self.assertNotIn('secret', stderr.getvalue())
            self.assertFalse(self.out.exists())
            self.assertFalse(self.report.exists())
            self.assertEqual(a.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
