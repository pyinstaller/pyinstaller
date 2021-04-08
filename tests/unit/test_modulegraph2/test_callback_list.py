import unittest

import modulegraph2._callback_list as callback_list


class TestCallbackList(unittest.TestCase):
    def test_empty_list(self):
        cb = callback_list.CallbackList()
        self.assertIs(cb(1, 2, 3), None)

        cb = callback_list.FirstNotNone()
        self.assertIs(cb(1, 2, 3), None)

    def test_one_callback(self):

        args = []

        def cb1(a, b):
            args.append((a, b))

        cb = callback_list.CallbackList()
        cb.add(cb1)
        self.assertIs(cb(1, 2), None)
        self.assertEqual(args, [(1, 2)])
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [(1, 2), (3, 4)])

        args = []
        cb.clear()
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [])

        args = []
        cb = callback_list.FirstNotNone()
        cb.add(cb1)
        self.assertIs(cb(1, 2), None)
        self.assertEqual(args, [(1, 2)])
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [(1, 2), (3, 4)])

        args = []
        cb.clear()
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [])

    def test_multiple_callbacks(self):

        args = []

        def cb1(a, b):
            args.append((a, b))

        def cb2(a, b):
            args.append(a + b)

        cb = callback_list.CallbackList()
        cb.add(cb1)
        cb.add(cb2)
        self.assertIs(cb(1, 2), None)
        self.assertEqual(args, [3, (1, 2)])
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [3, (1, 2), 7, (3, 4)])

        args = []
        cb = callback_list.FirstNotNone()
        cb.add(cb1)
        cb.add(cb2)
        self.assertIs(cb(1, 2), None)
        self.assertEqual(args, [3, (1, 2)])
        self.assertIs(cb(3, 4), None)
        self.assertEqual(args, [3, (1, 2), 7, (3, 4)])

    def test_first_not_none(self):
        def cb1(a):
            if a % 2 == 0:
                return a / 2

        def cb2(a):
            if a % 3 == 0:
                return a + 1

        def cb3(a):
            if a % 6 == 0:
                return a * a

        cb = callback_list.FirstNotNone()
        cb.add(cb1)
        cb.add(cb2)
        cb.add(cb3)

        self.assertEqual(cb(6), 36)
        self.assertEqual(cb(3), 4)
        self.assertEqual(cb(4), 2)
        self.assertEqual(cb(1), None)
