#!/usr/bin/env python

import os
import os.path
import sys
import unittest
from datetime import datetime, timedelta, date
from Crypto import Random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
if sys.version_info <= (3, 0):
    print('Python 2 is vintage. Please use Python 3.')
    sys.exit(1)

import securid
from securid.stoken import StokenFile
from securid.stdin import StdinFile
from securid.utils import (
    AES_KEY_SIZE,
    arrayset,
    aes_ecb_encrypt,
    aes_ecb_decrypt,
    cbc_hash
)

T0 = datetime(2001, 1, 1, 1, 1, 1, 1)
T1 = datetime(2010, 10, 10, 10, 10, 10, 10)
T2 = datetime(2020, 2, 2, 2, 2, 2, 2)
s1 = timedelta(seconds=1)
s30 = timedelta(seconds=30)
s60 = timedelta(seconds=60)

class TokenTest(unittest.TestCase):

    def test_at(self):
        seed = '9e2cdb3468bd84fe6cf42570d1f8559c'
        serial = '000123456789'
        t = securid.Token(serial=serial, seed=seed)
        self.assertEqual(t.at(T0), '078264')
        self.assertEqual(t.at(T0 + s30), '078264')
        self.assertNotEqual(t.at(T0 + s60), '078264')

        serial2 = '000987654321'
        t2 = securid.Token(serial=serial2, seed=seed)
        self.assertNotEqual(t.at(T0), t2.at(T0))

        seed2 = '884c91dc46f17970e4d08a34d852ee18'
        t3 = securid.Token(serial=serial2, seed=seed2)
        self.assertNotEqual(t3.at(T0), t2.at(T0))

    def test_serial_seed_as_bytes(self):
        seed = b'9e2cdb3468bd84fe6cf42570d1f8559c'
        serial = b'000123456789'
        t = securid.Token(serial=serial, seed=seed)
        self.assertEqual(t.at(T0), '078264')

    def test_number_of_digits(self):
        seed = '967863726e4a54c7cec668012e7302a6'
        serial = '432342'
        for i in range(1, 16):
            t = securid.Token(serial=serial, seed=seed, digits=i)
            self.assertEqual(len(t.at(T0)), i)

    def test_interval_30s(self):
        seed = '967863726e4a54c7cec668012e7302a6'
        serial = b'000123456789'
        t30 = securid.Token(serial=serial, seed=seed, interval=30)
        self.assertEqual(t30.at(T0), t30.at(T0 + s1))
        self.assertNotEqual(t30.at(T0), t30.at(T0 + s30))
        t60 = securid.Token(serial=serial, seed=seed, interval=60)
        self.assertNotEqual(t30.at(T0), t60.at(T0))

    def test_exp_date(self):
        serial = b'000123456789'
        t1 = securid.Token().random(serial=serial, exp_date=date(2123,1,2))
        t2 = securid.Token().random(serial=serial, exp_date='2123-01-02')
        self.assertEqual(t1.exp_date, date(2123,1,2))
        self.assertEqual(t2.exp_date, date(2123,1,2))

    def test_random(self):
        serial = b'000123456789'
        t1 = securid.Token().random()
        self.assertEqual(t1.at(T2), t1.at(T2 + s1))
        t2 = securid.Token().random(serial=serial)
        self.assertEqual(t2.at(T2), t2.at(T2 + s1))
        self.assertNotEqual(t1.at(T2), t2.at(T2))
        date1 = date(2050, 1, 1)
        t3 = securid.Token.random(exp_date=date1)
        self.assertEqual(t3.exp_date, date1)
        self.assertNotEqual(t1.now(), t3.now())

    def test_exceptions(self):
        def test_none_seed():
            serial = b'000123456789'
            t = securid.Token(serial=serial, seed=None)
            t.now()
        self.assertRaises(Exception, test_none_seed)

    def test_repl(self):
        seed = '967863726e4a54c7cec668012e7302a6'
        serial = b'000123456789'
        t = securid.Token(serial=serial, seed=seed, interval=30)
        self.assertEqual(repr(t), "{'digits': '6', 'exp_date': 'None', 'interval': '30', 'seed': '3936373836333732366534613534633763656336363830313265373330326136', 'serial': '000123456789'}")


class StokenTest(unittest.TestCase):

    def test_stoken_file(self):
        f = StokenFile()
        print(f.get_token())
        print(f.get_token().now())

    def test__numinput_to_bits(self):
        data = b'234231272577213035237547203121302447410465225375115521144150107256772170000036371'
        n_bits = 15
        offset = 76
        d_ok = b'y\xf2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        d = StokenFile._numinput_to_bits(data, n_bits, offset)
        self.assertEqual(d, d_ok)
        d1 = StokenFile._bits_to_numoutput(d, n_bits)
        self.assertEqual(data[offset:offset+len(d1)], d1)

        n_bits = 189
        offset = 13
        d = StokenFile._numinput_to_bits(data, n_bits, offset)
        d2 = StokenFile._bits_to_numoutput(d, n_bits)
        self.assertEqual(data[offset:offset+len(d2)], d2)

    def test_get_bits(self):
        data = b']OZXO\x18\x9e\xde\x11\xf9fZ\x86\xab\xfb\xb6v\xa6|\xadZ\xe6\xe5\xb4\xee@\x90\xe4m\xf3\xecJ\xf5'
        start = 0
        n_bits = 15
        d1 = StokenFile._get_bits(data, start, n_bits)
        self.assertEqual(d1, 11943)
        test1 = bytearray(data)
        StokenFile._set_bits(test1, start, n_bits, d1)
        self.assertEqual(data, test1)

        d2 = d1 + 1
        test2 = bytearray(data)
        StokenFile._set_bits(test2, start, n_bits, d2)
        self.assertNotEqual(data, test2)

        start3 = 159
        n_bits3 = 15
        d3 = StokenFile._get_bits(data, start3, n_bits3)
        self.assertEqual(d3, 22201)
        test3 = bytearray(data)
        StokenFile._set_bits(test3, start3, n_bits3, d3)
        self.assertEqual(data, test3)

        start4 = 128
        n_bits4 = 16
        d4 = StokenFile._get_bits(data, start4, n_bits4)
        self.assertEqual(d4, 30374)
        test4 = bytearray(data)
        StokenFile._set_bits(test4, start4, n_bits4, d4)
        self.assertEqual(data, test4)

        start5 = 13
        n_bits5 = 32
        d5 = StokenFile._get_bits(data, start5, n_bits5)
        self.assertEqual(d5, 3947563491)
        test5 = bytearray(data)
        StokenFile._set_bits(test5, start5, n_bits5, d5)
        self.assertEqual(data, test5)

    def test_v2_encode_token(self):
        token = securid.Token.random(exp_date=date(2050, 1, 1))
        seed = token.seed
        serial = token.serial
        digits = token.digits
        interval = token.interval
        exp_date = token.exp_date

        token1 = securid.Token(seed=seed, serial=serial, digits=digits, interval=interval, exp_date=exp_date)
        sf1 = StokenFile(token=token1)
        sf1.v2_encode_token()
        self.assertEqual(token1.serial, serial)
        self.assertEqual(token1.seed, seed)
        self.assertEqual(token1.digits, digits)
        self.assertEqual(token1.interval, interval)

        sf2 = StokenFile(data=sf1.data)
        self.assertEqual(sf2.get_token().serial, serial)
        self.assertEqual(sf2.get_token().seed, seed)
        self.assertEqual(sf2.get_token().digits, digits)
        self.assertEqual(sf2.get_token().interval, interval)

        for i in range(0, 10):
            self.assertEqual(sf2.get_token().at(i * 1000), token.at(i * 1000))

class UtilTest(unittest.TestCase):

    def test_arrayset(self):
        a = bytearray(6)
        arrayset(a, 0xff, n=2, dest_offset=3)
        self.assertEqual(a, bytes([0,0,0,0xff,0xff,0]))

    def test_aes_ecb(self):
        random = Random.new()
        key = random.read(AES_KEY_SIZE)
        data = random.read(AES_KEY_SIZE * 10)
        t = aes_ecb_encrypt(key, data)
        self.assertNotEqual(data, t)
        d = aes_ecb_decrypt(key, t)
        self.assertEqual(data, d)

    def test_cbc_hash(self):
        key = bytes([196, 176, 202, 238, 230, 207, 220, 103, 77, 214, 173, 81, 38, 75, 94, 221])
        iv = bytes([ 0x1b, 0xb6, 0x7a, 0xe8, 0x58, 0x4c, 0xaa, 0x73,
                     0xb2, 0x57, 0x42, 0xd7, 0x07, 0x8b, 0x83, 0xb8 ])
        h = bytes([0, 154, 82, 250, 182, 234, 117, 60, 149, 75, 56, 40, 13, 72, 139, 18])
        self.assertEqual(cbc_hash(key, iv, b'test'), h)
        self.assertNotEqual(cbc_hash(key, iv, b'TEST'), h)

if __name__ == '__main__':
    unittest.main()