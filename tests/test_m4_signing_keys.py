# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Kazuhide Takahashi
"""The channel's signing keys: the key lists, the keyring package, and signature parsing.

A rotation (docs/package-channel.md) moves the channel through three states:
normal, phase 1 (old and new trusted, signed by old) and phase 2 (new trusted,
old revoked, signed by new). Each must pass, and anything else must not.
"""
import importlib.util
import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = json.loads((ROOT / 'packaging/omarchy-m4/channel.json').read_text())
KEYRING = ROOT / 'packaging/omarchy-m4/omarchy-m4-keyring'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load('check_m4_packages', 'tools/check-m4-packages.py')
PUBLISH = load('publish_m4_packages', 'tools/publish-m4-packages.py')
OLD, NEW, OTHER = 'A' * 40, 'B' * 40, 'C' * 40
NORMAL = {'signing_fingerprint': OLD, 'trusted_fingerprints': [OLD], 'revoked_fingerprints': []}
PHASE1 = {'signing_fingerprint': OLD, 'trusted_fingerprints': [OLD, NEW], 'revoked_fingerprints': []}
PHASE2 = {'signing_fingerprint': NEW, 'trusted_fingerprints': [NEW], 'revoked_fingerprints': [OLD]}


class KeyListTests(unittest.TestCase):
    def test_rotation_states_pass(self):
        for channel in (NORMAL, PHASE1, PHASE2, CHANNEL):
            CHECK.check_signing_keys(channel)

    def test_bad_lists_are_refused(self):
        bad = {
            'untrusted signer': {**PHASE2, 'trusted_fingerprints': [OTHER]},
            'trusted and revoked': {**PHASE1, 'revoked_fingerprints': [NEW]},
            'revoked signer': {**PHASE2, 'revoked_fingerprints': [NEW]},
            'duplicate': {**NORMAL, 'trusted_fingerprints': [OLD, OLD]},
            'short': {**NORMAL, 'trusted_fingerprints': [OLD, 'ABCD']},
            'lower case': {**NORMAL, 'revoked_fingerprints': ['b' * 40]},
        }
        for label, channel in bad.items():
            with self.subTest(label), self.assertRaises(ValueError):
                CHECK.check_signing_keys(channel)


class KeyringTests(unittest.TestCase):
    def keyring(self, held, trusted, revoked):
        directory = Path(self.temp.name)
        (directory / 'omarchy-m4.gpg').write_text('public keys')
        (directory / 'omarchy-m4-trusted').write_text(trusted)
        (directory / 'omarchy-m4-revoked').write_text(revoked)
        return directory, mock.patch.object(CHECK, 'keyring_fingerprints', return_value=held)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_each_state_has_its_keyring(self):
        for channel, held, trusted, revoked in (
                (NORMAL, [OLD], f'{OLD}:4:\n', ''),
                (PHASE1, [OLD, NEW], f'{OLD}:4:\n{NEW}:4:\n', ''),
                (PHASE2, [OLD, NEW], f'{NEW}:4:\n', f'{OLD}\n')):
            directory, patch = self.keyring(held, trusted, revoked)
            with self.subTest(channel=channel), patch:
                CHECK.check_keyring(channel, directory)

    def test_mismatched_keyrings_are_refused(self):
        for label, channel, held, trusted, revoked in (
                ('phase 1 keyring trusts only the old key', PHASE1, [OLD, NEW], f'{OLD}:4:\n', ''),
                ('phase 2 keyring does not revoke', PHASE2, [OLD, NEW], f'{NEW}:4:\n', ''),
                ('phase 2 keyring drops the revoked key', PHASE2, [NEW], f'{NEW}:4:\n', f'{OLD}\n'),
                ('extra key', NORMAL, [OLD, OTHER], f'{OLD}:4:\n', ''),
                ('missing signer', NORMAL, [OTHER], f'{OLD}:4:\n', ''),
                ('normal keyring revokes', NORMAL, [OLD, NEW], f'{OLD}:4:\n', f'{NEW}\n')):
            directory, patch = self.keyring(held, trusted, revoked)
            with self.subTest(label), patch, self.assertRaises(ValueError):
                CHECK.check_keyring(channel, directory)

    @unittest.skipUnless(shutil.which('gpg'), 'gpg is not installed')
    def test_the_repository_keyring_matches_the_channel(self):
        CHECK.check_keyring(CHANNEL, KEYRING)


class SignerTests(unittest.TestCase):
    def signer(self, returncode, *fingerprints):
        stdout = ''.join(f'[GNUPG:] VALIDSIG {f} 2026-11-09 0 4 0 22 10 00 {f}\n' for f in fingerprints)
        result = types.SimpleNamespace(returncode=returncode, stdout=stdout)
        with mock.patch.object(PUBLISH.subprocess, 'run', return_value=result):
            return PUBLISH.signer(Path('x.sig'), Path('x'))

    def test_one_good_signature_names_its_key(self):
        self.assertEqual(self.signer(0, NEW), NEW)

    def test_anything_else_has_no_signer(self):
        self.assertIsNone(self.signer(0))
        self.assertIsNone(self.signer(1, NEW))
        self.assertIsNone(self.signer(0, OLD, NEW), 'a signature by two keys is not one by either')

    def test_only_the_channel_key_counts_as_signed(self):
        with mock.patch.object(PUBLISH, 'signer', return_value=OLD), \
             mock.patch.object(PUBLISH, 'FPR', NEW), mock.patch.object(PUBLISH, 'RETIRED', (OLD,)):
            self.assertFalse(PUBLISH.signed(Path('x.sig'), Path('x')))
            self.assertTrue(PUBLISH.retired_signature(Path('x.sig'), Path('x')))
        with mock.patch.object(PUBLISH, 'signer', return_value=OTHER), mock.patch.object(PUBLISH, 'RETIRED', (OLD,)):
            self.assertFalse(PUBLISH.retired_signature(Path('x.sig'), Path('x')))



@unittest.skipUnless(shutil.which('gpg') and shutil.which('gpgconf'), 'gpg is not installed')
class RevocationCertificateTests(unittest.TestCase):
    """Phase 2 with real gpg, when the keyring also carries the old key's revocation certificate.

    gpg still reports one VALIDSIG for the revoked key (with REVKEYSIG and KEYREVOKED),
    so publishing can verify what the old key signed and replace it, and the keyring
    check still counts each key once.
    """

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.signer_home = self.home('signer')
        for name in ('old', 'new'):
            self.gpg(self.signer_home, '--quick-gen-key', f'Rotation test {name} <{name}@invalid>',
                     'ed25519', 'sign', 'never')
        self.old, self.new = (self.fingerprint(self.signer_home, f'{name}@invalid') for name in ('old', 'new'))
        self.data = self.dir / 'package'
        self.data.write_bytes(b'package bytes')
        self.gpg(self.signer_home, '--local-user', self.old, '--detach-sign', '--no-armor',
                 '--output', str(self.dir / 'package.sig'), str(self.data))
        # The certificate gpg wrote when it made the key; its armor lines are escaped with ':'.
        made = (self.signer_home / 'openpgp-revocs.d' / (self.old + '.rev')).read_text()
        (self.dir / 'old.rev').write_text(made.replace(':-----BEGIN', '-----BEGIN'))
        self.gpg(self.signer_home, '--import', str(self.dir / 'old.rev'))
        self.keyrings = self.dir / 'keyrings'
        self.keyrings.mkdir()
        self.gpg(self.signer_home, '--armor', '--output', str(self.keyrings / 'omarchy-m4.gpg'),
                 '--export', self.old, self.new)

    def home(self, name):
        home = self.dir / name
        home.mkdir(mode=0o700)
        self.addCleanup(subprocess.run, ['gpgconf', '--homedir', str(home), '--kill', 'all'],
                        capture_output=True)
        return home

    def gpg(self, home, *args):
        return subprocess.run(['gpg', '--homedir', str(home), '--batch', '--pinentry-mode', 'loopback',
                               '--passphrase', '', *args], check=True, capture_output=True, text=True).stdout

    def fingerprint(self, home, user):
        listing = self.gpg(home, '--with-colons', '--list-keys', user)
        return next(line.split(':')[9] for line in listing.splitlines() if line.startswith('fpr:'))

    def test_the_old_key_is_revoked_in_the_keyring(self):
        listing = self.gpg(self.signer_home, '--with-colons', '--list-keys', self.old)
        self.assertEqual(next(line for line in listing.splitlines() if line.startswith('pub:')).split(':')[1], 'r')

    def test_publishing_still_verifies_what_the_revoked_key_signed(self):
        verifier = self.home('publisher')
        self.gpg(verifier, '--import', str(self.keyrings / 'omarchy-m4.gpg'))  # what publish imports
        signature = self.dir / 'package.sig'
        with mock.patch.dict(os.environ, {'GNUPGHOME': str(verifier)}):
            self.assertEqual(PUBLISH.signer(signature, self.data), self.old)
            with mock.patch.object(PUBLISH, 'FPR', self.new), mock.patch.object(PUBLISH, 'RETIRED', (self.old,)):
                self.assertFalse(PUBLISH.signed(signature, self.data))
                self.assertTrue(PUBLISH.retired_signature(signature, self.data))
            (self.dir / 'other').write_bytes(b'other bytes')
            self.assertIsNone(PUBLISH.signer(signature, self.dir / 'other'))

    def test_the_phase_2_keyring_passes_the_package_check(self):
        (self.keyrings / 'omarchy-m4-trusted').write_text(self.new + ':4:\n')
        (self.keyrings / 'omarchy-m4-revoked').write_text(self.old + '\n')
        phase2 = {'signing_fingerprint': self.new, 'trusted_fingerprints': [self.new],
                  'revoked_fingerprints': [self.old]}
        self.assertEqual(sorted(CHECK.keyring_fingerprints(self.keyrings / 'omarchy-m4.gpg')),
                         sorted([self.old, self.new]))
        CHECK.check_keyring(phase2, self.keyrings)


if __name__ == '__main__':
    unittest.main()
