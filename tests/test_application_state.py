import unittest

from carendmr.application import ApplicationStateStore
from carendmr.domain import ConnectionState


class ApplicationStateTests(unittest.TestCase):
    def test_state_store_notifies_with_immutable_state(self):
        store = ApplicationStateStore()
        received = []
        store.subscribe(received.append)
        state = store.update(connection=ConnectionState.CONNECTING, message="Test")
        self.assertEqual(ConnectionState.CONNECTING, state.connection)
        self.assertEqual("Test", received[-1].message)
        self.assertEqual(ConnectionState.DISCONNECTED, type(state)().connection)
        self.assertFalse(type(state)().brandmeister_connected)
        self.assertFalse(type(state)().receive_active)


if __name__ == "__main__":
    unittest.main()
