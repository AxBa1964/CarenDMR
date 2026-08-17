from carendmr.application.operating_controller import OperatingController
from carendmr.application.radio_state_machine import RadioState
from carendmr.domain.models import ApplicationState, ConnectionState


class Store:
    def subscribe(self, listener): self.listener = listener


class Receive:
    def __init__(self):
        self.state_store = Store(); self.is_running = False


class Manager:
    def __init__(self, receive): self.receive = receive; self.calls=[]
    def connect(self, tg, ts, call_type):
        self.calls.append((tg, ts, call_type)); self.receive.is_running=True; return True
    def disconnect(self): self.receive.is_running=False


def test_receiving_state_becomes_connected():
    receive=Receive(); controller=OperatingController(Manager(receive), receive)
    receive.state_store.listener(ApplicationState(connection=ConnectionState.RECEIVING))
    assert controller.snapshot().state is RadioState.CONNECTED


def test_connect_delegates_to_existing_manager():
    receive=Receive(); manager=Manager(receive); controller=OperatingController(manager, receive)
    assert controller.connect(91, 2, 'group') is True
    assert manager.calls == [(91, 2, 'group')]
    assert controller.snapshot().state is RadioState.CONNECTING
