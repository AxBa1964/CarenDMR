import unittest

from carendmr.application.radio_state_machine import RadioState, RadioStateMachine


class RadioStateMachineTests(unittest.TestCase):
    def test_normal_cycle_controls_permissions(self):
        machine = RadioStateMachine()
        self.assertTrue(machine.snapshot().can_edit_parameters)
        self.assertFalse(machine.snapshot().can_transmit)

        machine.transition(RadioState.CONNECTING)
        machine.transition(RadioState.CONNECTED)
        self.assertTrue(machine.snapshot().can_transmit)
        self.assertFalse(machine.snapshot().can_edit_parameters)

        machine.transition(RadioState.TRANSMITTING)
        self.assertFalse(machine.snapshot().can_transmit)
        machine.transition(RadioState.CONNECTED)
        machine.transition(RadioState.DISCONNECTING)
        machine.transition(RadioState.DISCONNECTED)
        self.assertTrue(machine.snapshot().can_edit_parameters)

    def test_invalid_transition_is_rejected(self):
        machine = RadioStateMachine()
        with self.assertRaises(RuntimeError):
            machine.transition(RadioState.TRANSMITTING)

    def test_synchronize_recovers_from_external_state(self):
        machine = RadioStateMachine(RadioState.CONNECTING)
        machine.synchronize(RadioState.DISCONNECTED)
        self.assertEqual(machine.state, RadioState.DISCONNECTED)
