from lewis.devices import StateMachineDevice
from lewis.core.logging import has_log
from .states import DefaultState
from collections import OrderedDict


class Supply:
    def __init__(self):
        self.power = False
        self.interlock = False
        self.current = 0
        self.voltage = 0

        self.fullscale_volts = 100
        self.fullscale_amps = 500

    def reset(self):
        pass

    def set_dac(self, adc_num, value):
        if adc_num == 0:
            self.current = (value / 1000000) * self.fullscale_amps
        elif adc_num == 1:
            self.voltage = (value / 1000000) * self.fullscale_volts
        else:
            raise ValueError(f"Unknown dac {adc_num}")

    def read_adc(self, adc_num):
        if adc_num == 0:
            return int((self.current / self.fullscale_amps) * 1000000)
        elif adc_num == 1:
            return int((self.voltage / self.fullscale_volts) * 1000000)
        else:
            raise ValueError(f"Unknown adc {adc_num}")


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

    def set_interlock(self, addr, status):
        self.supplies[addr].interlock = status
