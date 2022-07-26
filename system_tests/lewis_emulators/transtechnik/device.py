from lewis.devices import StateMachineDevice
from lewis.core.logging import has_log
from .states import DefaultState
from collections import OrderedDict


INTERLOCKS = [
    "power_on_cmd",
    "pm1_error",
    "pm2_error",
    "pm3_error",
    "pm4_error",
    "pm5_error",
    "in_error",
    "ru_error",
    "pm1_warning",
    "pm2_warning",
    "pm3_warning",
    "pm4_warning",
    "pm5_warning",
    "in_warning",
    "ru_warning",
    "is_remote",
    "magnet_temp_interlock",
    "magnet_water_interlock",
    "interlock_bps1",
    "interlock_bps2",
    "interlock_pps1",
    "interlock_pps2",
    "interlock_spare1",
    "interlock_spare2",
    "output_overvoltage",
    "output_overcurrent",
    "output_unbalanced",
    "em_stop",
    "door_open",
    "control_switch",
    "self_test_failed",
]


class Supply:
    def __init__(self):
        self.power = False
        self.interlock = False
        self.current = 0
        self.voltage = 0

        self.fullscale_voltage = 150
        self.fullscale_current = 500

        self.power = False

        self.interlocks = {key: False for key in INTERLOCKS}

    def reset(self):
        pass


@has_log
class SimulatedTranstechnik(StateMachineDevice):

    def _initialize_data(self):
        self.re_initialise()

    def _get_state_handlers(self):
        return {'default': DefaultState()}

    def _get_initial_state(self):
        return 'default'

    def _get_transition_handlers(self):
        return OrderedDict([])

    def re_initialise(self):
        self.connected = True
        self.address = 0

        # Supplies can, in principle, be daisy chained.
        self.supplies = {
            0: Supply(),
        }

    def supply(self):
        """
        Gets the currently-addressed power supply.
        """
        if self.address not in self.supplies:
            raise ValueError(f"Invalid power supply addressed "
                             f"(address {self.address}, available {self.supplies.keys()}")
        return self.supplies[self.address]

    def set_voltage(self, addr, voltage):
        self.supplies[addr].voltage = voltage

    def set_property(self, addr, prop, val):
        setattr(self.supplies[addr], prop, val)

    def set_interlock(self, addr, key, val):
        assert key in INTERLOCKS
        self.supplies[addr].interlocks[key] = val
