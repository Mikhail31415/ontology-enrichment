class StateManager:
    def __init__(self):
        self._callbacks = {}
        self._states = {}

    def register_callback(self, name, callback):
        self._callbacks[name] = callback

    def trigger_callback(self, name, value):
        if name in self._callbacks:
            self._callbacks[name](value)

    def set_state(self, name, value):
        self._states[name] = value

    def get_state(self, name):
        return self._states[name]


global_state_manager = StateManager()
