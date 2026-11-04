"""Quote-bound Solana Pay requests and strict read-only finalized verification."""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode, urlsplit, parse_qsl
import uuid

NETWORK = 'mainnet-beta'
MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
RECIPIENT = 'AUFXqDk3wJ3VTWzoEAng3V4Fcy8yQarUaFzQW3bxgTsS'
SITE = 'https://streamside-notes.sandybloom18.chatgpt.site/pay.html'
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
KEYS = {'v', 'order', 'quote', 'accepted', 'amount', 'reference', 'created', 'expires', 'network', 'mint', 'recipient', 'demo'}

def amount_units(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,14})(\.[0-9]{1,6})?', value):
        raise ValueError('amount must be a plain decimal string, at most six places')
    # Integer arithmetic after Decimal parsing avoids context rounding and floats.
    decimal = Decimal(value)
    numerator, denominator = decimal.as_integer_ratio()
    units, remainder = divmod(numerator * 1000000, denominator)
    if remainder: raise ValueError('fractional USDC base unit')
    if not decimal.is_finite() or not 0 < units <= 2**64-1:
        raise ValueError('amount outside USDC u64 range')
    return units

def base58(raw):
    n = int.from_bytes(raw, 'big'); out = ''
    while n:
        n, r = divmod(n, 58); out = ALPHABET[r] + out
    return '1' * (len(raw) - len(raw.lstrip(b'\0'))) + out

def public_key(value):
    if not isinstance(value, str) or not 32 <= len(value) <= 44 or any(c not in ALPHABET for c in value):
        raise ValueError('invalid public reference')
    n = 0
    for c in value: n = n * 58 + ALPHABET.index(c)
    raw = b'\0' * (len(value)-len(value.lstrip('1'))) + (n.to_bytes((n.bit_length()+7)//8, 'big') if n else b'')
    if len(raw) != 32: raise ValueError('reference must encode 32 bytes')
    return value

def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value): raise ValueError('invalid UTC time')
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

def validate(params, now=None):
    if set(params) != KEYS or any(not isinstance(v, str) for v in params.values()): raise ValueError('unknown or missing fields')
    if (params['v'], params['network'], params['mint'], params['recipient']) != ('1', NETWORK, MINT, RECIPIENT): raise ValueError('fixed payment values changed')
    if not re.fullmatch(r'[a-f0-9]{32}', params['order']) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', params['quote']): raise ValueError('invalid order or quote')
    if params['accepted'] != 'yes' or params['demo'] not in ('yes', 'no'): raise ValueError('accepted quote required')
    amount_units(params['amount']); public_key(params['reference'])
    created, expires = timestamp(params['created']), timestamp(params['expires'])
    now = now or datetime.now(timezone.utc)
    if created > now or expires <= created or expires-created > timedelta(days=7) or expires <= now: raise ValueError('invalid or expired request')
    return params

def transfer_uri(params):
    validate(params)
    if params['demo'] == 'yes': raise ValueError('synthetic demo cannot pay')
    return 'solana:' + RECIPIENT + '?' + urlencode({'amount': params['amount'], 'spl-token': MINT, 'reference': params['reference']})

def parse_link(link, now=None):
    u = urlsplit(link)
    if u.scheme != 'https' or u.netloc != urlsplit(SITE).netloc or u.path != '/pay.html' or u.fragment: raise ValueError('invalid site link')
    pairs = parse_qsl(u.query, keep_blank_values=True, strict_parsing=True)
    if len(pairs) != len(dict(pairs)): raise ValueError('duplicate fields')
    return validate(dict(pairs), now)

def create(directory, amount, quote, accepted=False, demo=False, hours=24):
    if accepted is not True: raise ValueError('explicit quote acceptance required')
    amount_units(amount)
    if type(hours) is not int or not 1 <= hours <= 168: raise ValueError('expiry hours must be 1..168')
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = lambda t: t.strftime('%Y-%m-%dT%H:%M:%SZ')
    p = dict(v='1', order=uuid.uuid4().hex, quote=quote, accepted='yes', amount=amount, reference=base58(secrets.token_bytes(32)), created=fmt(now), expires=fmt(now+timedelta(hours=hours)), network=NETWORK, mint=MINT, recipient=RECIPIENT, demo='yes' if demo else 'no')
    validate(p)
    record = {'schema': 'streamside.payment-order.v1', 'request': p, 'amount_units': amount_units(amount), 'status': 'requested', 'receipt': None, 'payment_uri': None if demo else transfer_uri(p), 'payment_link': SITE+'?'+urlencode(p)}
    # A fresh directory is the transaction boundary: never reuse/overwrite a store.
    target = Path(directory)
    if '..' in target.parts: raise ValueError('ambiguous store path')
    parent = target.absolute().parent
    if parent.resolve() != parent: raise ValueError('symlink store parent')
    target.mkdir(mode=0o700)
    directory_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open('.order.tmp', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(record, out, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.link('.order.tmp', 'order.json', src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
        os.unlink('.order.tmp', dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return record

def create_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    parser.add_argument('--amount', required=True)
    parser.add_argument('--quote', required=True)
    parser.add_argument('--confirm-quote-accepted', action='store_true', required=True)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--expires-hours', type=int, default=24)
    args = parser.parse_args()
    try:
        print(json.dumps(create(args.store, args.amount, args.quote, args.confirm_quote_accepted, args.demo, args.expires_hours), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')



# Deliberately no configurable endpoint, redirect support, or general RPC interface.
import http.client
import urllib.request
import urllib.error
import sqlite3
import stat
import sys
from contextlib import closing

# Full getGenesisHash result, not the truncated CAIP-2 network identifier.
GENESIS = '5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d'
RPC_HOST = 'api.mainnet-beta.solana.com'
RPC_METHODS = frozenset(('getGenesisHash', 'getSignatureStatuses', 'getTransaction'))
MAX_RESPONSE = 2 * 1024 * 1024
PRODUCTION_LEDGER_ID = 0x53535052
SYNTHETIC_LEDGER_ID = 0x53534658
RECEIPT_SCHEMA = 'CREATE TABLE receipts (signature TEXT PRIMARY KEY, order_id TEXT UNIQUE NOT NULL, evidence TEXT NOT NULL)'

class EvidenceError(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)

def signature_value(value):
    require(isinstance(value, str) and 64 <= len(value) <= 88 and all(c in ALPHABET for c in value), 'invalid_signature')
    n = 0
    for c in value:
        n = n * 58 + ALPHABET.index(c)
    raw = b'\0' * (len(value) - len(value.lstrip('1'))) + (n.to_bytes((n.bit_length()+7)//8, 'big') if n else b'')
    require(len(raw) == 64, 'invalid_signature')
    return value

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError('rpc_redirect_forbidden')


def rpc(method, params):
    require(method in RPC_METHODS, 'rpc_method_forbidden')
    # Keep urllib's default system routing and TLS verification. Never follow a redirect.
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        'https://' + RPC_HOST,
        data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode('utf8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=10) as response:
        require(response.status == 200, 'rpc_http_status')
        body = response.read(MAX_RESPONSE + 1)
        require(len(body) <= MAX_RESPONSE, 'rpc_response_too_large')
        def unique(pairs):
            result = {}
            for k, v in pairs:
                require(k not in result, 'rpc_duplicate_key')
                result[k] = v
            return result
        result = json.loads(body, object_pairs_hook=unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(EvidenceError('rpc_nonfinite')))
        require(isinstance(result, dict) and result.get('jsonrpc') == '2.0' and type(result.get('id')) is int and result['id'] == 1 and 'error' not in result and 'result' in result, 'rpc_invalid_envelope')
        return result['result']

def safe_directory(path):
    path = Path(path).absolute()
    require('..' not in path.parts and path.resolve() == path and path.is_dir(), 'unsafe_directory')
    return path

def read_order(directory, synthetic=False):
    directory = safe_directory(directory)
    fd = os.open(directory / 'order.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'r', encoding='utf8') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'invalid_order_file')
        raw = source.read(16385)
    require(len(raw) <= 16384, 'order_too_large')
    record = json.loads(raw)
    require(record.get('schema') == 'streamside.payment-order.v1', 'invalid_order_schema')
    q = record['request']
    # Validation time is creation time: late verification of an on-time transfer is valid.
    validate(q, timestamp(q['created']))
    require(timestamp(q['created']) <= datetime.now(timezone.utc), 'future_order')
    require(type(record['amount_units']) is int and record['amount_units'] == amount_units(q['amount']), 'order_amount_mismatch')
    require(record.get('status') == 'requested' and record.get('receipt') is None, 'invalid_order_state')
    require(q['demo'] == ('yes' if synthetic else 'no'), 'synthetic_order_forbidden')
    return record

def transaction_evidence(tx, q, signature):
    require(isinstance(tx, dict), 'invalid_transaction')
    require(type(tx.get('version')) is int and tx['version'] == 0 or tx.get('version') == 'legacy', 'unsupported_version')
    require(type(tx.get('slot')) is int and tx['slot'] >= 0, 'invalid_slot')
    blocktime = tx.get('blockTime')
    require(type(blocktime) is int and timestamp(q['created']).timestamp() <= blocktime < timestamp(q['expires']).timestamp(), 'invalid_block_time')
    transaction = tx['transaction']; meta = tx['meta']
    require(isinstance(transaction, dict) and isinstance(meta, dict) and 'err' in meta and meta['err'] is None, 'transaction_failed')
    require(isinstance(transaction.get('signatures'), list) and transaction['signatures'] and transaction['signatures'][0] == signature, 'signature_not_bound')
    keys = transaction['message']['accountKeys']
    require(isinstance(keys, list) and keys and all(isinstance(k, str) for k in keys), 'invalid_account_keys')
    for key in keys: public_key(key)
    loaded = meta.get('loadedAddresses')
    if tx['version'] == 0:
        require(isinstance(loaded, dict) and set(loaded) == {'writable', 'readonly'}, 'missing_loaded_addresses')
        for field in ('writable', 'readonly'):
            require(isinstance(loaded[field], list), 'invalid_loaded_addresses')
            for key in loaded[field]: public_key(key)
            keys = keys + loaded[field]
    require(len(keys) == len(set(keys)) and q['reference'] in keys, 'invalid_reference_or_accounts')
    lamports_pre, lamports_post = meta['preBalances'], meta['postBalances']
    require(isinstance(lamports_pre, list) and isinstance(lamports_post, list) and len(lamports_pre) == len(keys) == len(lamports_post) and all(type(x) is int and x >= 0 for x in lamports_pre + lamports_post), 'missing_account_balances')
    def balances(field):
        rows = meta.get(field)
        require(isinstance(rows, list), 'missing_token_balances')
        result = {}
        for row in rows:
            index = row['accountIndex']
            require(type(index) is int and 0 <= index < len(keys) and index not in result, 'invalid_account_index')
            public_key(row['mint']); public_key(row['owner'])
            require(row.get('programId') == 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'invalid_token_program')
            token = row['uiTokenAmount']; units = token['amount']
            require(isinstance(units, str) and re.fullmatch(r'0|[1-9][0-9]{0,19}', units) and int(units) <= 2**64-1 and type(token['decimals']) is int, 'invalid_token_amount')
            if row['mint'] == MINT: require(token['decimals'] == 6, 'invalid_decimals')
            result[index] = (row['mint'], row['owner'], int(units))
        return result
    before, after = balances('preTokenBalances'), balances('postTokenBalances')
    total = 0; found = False
    for index in before.keys() | after.keys():
        a, b = before.get(index), after.get(index)
        if a and b: require(a[:2] == b[:2], 'contradictory_token_identity')
        identity = b or a
        if identity[:2] != (MINT, RECIPIENT): continue
        found = True
        # Missing pre balance is accepted only for a newly funded account that did
        # not exist (zero lamports) before execution. Closed accounts are rejected.
        require(b is not None, 'missing_post_balance')
        if a is None: require(lamports_pre[index] == 0 and lamports_post[index] > 0, 'unproven_new_account')
        total += b[2] - (a[2] if a else 0)
    require(found and total == amount_units(q['amount']), 'net_amount_mismatch')
    return {'signature': signature, 'order': q['order'], 'reference': q['reference'], 'amount_units': total, 'slot': tx['slot'], 'blockTime': blocktime, 'network': NETWORK}

def record_receipt(ledger, receipt):
    """One authoritative SQLite transaction: no externally visible half receipt.

    All production orders MUST use the same dedicated ledger. SQLite's rollback
    journal recovers interrupted transactions, including concurrent processes.
    """
    ledger = safe_directory(ledger)
    path = ledger / 'receipts.sqlite3'
    for name in ('receipts.sqlite3', 'receipts.sqlite3-journal', 'receipts.sqlite3-wal', 'receipts.sqlite3-shm'):
        candidate = ledger / name
        require(not candidate.is_symlink(), 'unsafe_ledger_file')
        if candidate.exists(): require(candidate.is_file() and candidate.stat().st_nlink == 1, 'unsafe_ledger_file')
    # Private directory must be owned by this operator, not writable by others.
    info = ledger.stat()
    require(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'unsafe_ledger_permissions')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        schema = db.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        expected_id = SYNTHETIC_LEDGER_ID if receipt['synthetic'] else PRODUCTION_LEDGER_ID
        ledger_id = db.execute('PRAGMA application_id').fetchone()[0]
        if not schema:
            require(ledger_id in (0, expected_id), 'ledger_domain_mismatch')
            db.execute(RECEIPT_SCHEMA)
            db.execute('PRAGMA application_id = ' + str(expected_id))
        else:
            require(schema == [('table', 'receipts', RECEIPT_SCHEMA)], 'unknown_ledger_schema')
            require(ledger_id == expected_id, 'ledger_domain_mismatch')
        try:
            db.execute('INSERT INTO receipts VALUES (?, ?, ?)', (receipt['signature'], receipt['order'], json.dumps(receipt, sort_keys=True)))
        except sqlite3.IntegrityError as error:
            raise EvidenceError('already_accounted') from error
        db.commit()
    return receipt

def verify(directory, signature, ledger, *, transport=None):
    try:
        synthetic = transport is not None
        ledger_path = safe_directory(ledger)
        require(ledger_path == safe_directory(directory).parent / '.payment-receipts', 'ledger_not_bound_to_order_root')
        root_info = ledger_path.parent.stat()
        require(root_info.st_uid == os.getuid() and root_info.st_mode & 0o077 == 0, 'unsafe_order_root_permissions')
        marker = ledger_path / '.synthetic-fixtures-only'
        require(marker.is_file() and not marker.is_symlink() if synthetic else not marker.exists() and not marker.is_symlink(), 'synthetic_ledger_mismatch')
        record = read_order(directory, synthetic=synthetic)
        signature_value(signature)
        call = transport or rpc
        require(call('getGenesisHash', []) == GENESIS, 'wrong_genesis')
        statuses = call('getSignatureStatuses', [[signature], {'searchTransactionHistory': True}])
        require(isinstance(statuses, dict) and isinstance(statuses.get('value'), list) and len(statuses['value']) == 1, 'invalid_status_response')
        status = statuses['value'][0]
        if status is None: return {'status': 'pending', 'reason': 'signature_not_found'}
        require(isinstance(status, dict) and 'err' in status, 'invalid_signature_status')
        require(status['err'] is None, 'transaction_failed')
        require(status.get('confirmationStatus') in ('processed', 'confirmed', 'finalized'), 'unknown_confirmation_status')
        if status['confirmationStatus'] != 'finalized': return {'status': 'pending', 'reason': 'not_finalized'}
        require(type(status.get('slot')) is int and status['slot'] >= 0 and 'confirmations' in status and status['confirmations'] is None, 'invalid_finalized_status')
        tx = call('getTransaction', [signature, {'commitment': 'finalized', 'encoding': 'json', 'maxSupportedTransactionVersion': 0}])
        if tx is None: return {'status': 'pending', 'reason': 'transaction_not_found'}
        receipt = transaction_evidence(tx, record['request'], signature)
        require(receipt['slot'] == status['slot'], 'slot_mismatch')
        receipt['synthetic'] = synthetic
        record_receipt(ledger, receipt)
        return {'status': 'verified', 'reason': 'finalized_exact_transfer', 'receipt': receipt}
    except EvidenceError as error:
        return {'status': 'unverifiable', 'reason': str(error)}
    except (OSError, ValueError, TypeError, KeyError, IndexError, sqlite3.Error, urllib.error.URLError, http.client.HTTPException, RecursionError, AttributeError, OverflowError):
        return {'status': 'unverifiable', 'reason': 'invalid_or_unavailable_evidence'}

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        parser = argparse.ArgumentParser(description='Read-only mainnet receipt verification; no signing or income recording')
        parser.add_argument('--store', required=True)
        parser.add_argument('--signature', required=True)
        parser.add_argument('--ledger', required=True, help='existing private directory; use one ledger for ALL production orders')
        args = parser.parse_args(sys.argv[2:])
        result = verify(args.store, args.signature, args.ledger)
        print(json.dumps(result, sort_keys=True))
        return
    create_main()

if __name__ == '__main__': main()
