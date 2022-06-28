import contextlib
import unittest

from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.testing import get_running_lewis_and_ioc, assert_log_messages, skip_if_recsim, parameterized_list
from parameterized import parameterized

# Device prefix
DEVICE_PREFIX = "TRANTECH_01"

EMULATOR_DEVICE = "transtechnik"

VOLT_FULLSCALE = 125
CURR_FULLSCALE = 500

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("TRANTECH"),
        "emulator": EMULATOR_DEVICE,
        "macros": {
            "VOLT_FULLSCALE": VOLT_FULLSCALE,
            "CURR_FULLSCALE": CURR_FULLSCALE,
            "PS_ADDR": "000",
        }
    },
]

TEST_MODES = [TestModes.DEVSIM, TestModes.RECSIM]

TEST_VOLTAGES = [0, 0.1, VOLT_FULLSCALE/2, VOLT_FULLSCALE]
TEST_CURRENTS = [0, 0.1, CURR_FULLSCALE/2, CURR_FULLSCALE]


class TranstechnikTests(unittest.TestCase):

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_DEVICE, DEVICE_PREFIX)
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_wait_time=0., default_timeout=5)
        self.ca.assert_that_pv_is_number("VOLT:FULLSCALE", VOLT_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_is_number("CURR:FULLSCALE", CURR_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_exists("DISABLE", timeout=30)

    def test_disable_exists(self):
        self.ca.assert_that_pv_is("DISABLE", "COMMS ENABLED")

    @parameterized.expand(parameterized_list(TEST_VOLTAGES))
    def test_WHEN_voltage_is_set_THEN_voltage_updates(self, _, val):
        self.ca.set_pv_value("VOLT:SP", val)
        self.ca.assert_that_pv_is_number("VOLT", val, tolerance=0.01)

    @parameterized.expand(parameterized_list(TEST_CURRENTS))
    def test_WHEN_curr_is_set_THEN_voltage_updates(self, _, val):
        self.ca.set_pv_value("CURR:SP", val)
        self.ca.assert_that_pv_is_number("CURR", val, tolerance=0.01)

    @contextlib.contextmanager
    def _disconnect_device(self):
        self._lewis.backdoor_set_and_assert_set("connected", False)
        try:
            yield
        finally:
            self._lewis.backdoor_set_and_assert_set("connected", True)

    @parameterized.expand(parameterized_list(["VOLT", "CURR", "VOLT:RAW", "CURR:RAW", "STATUS"]))
    @skip_if_recsim("testing disconnection requires emulator")
    def test_WHEN_device_disconnected_THEN_pvs_in_alarm(self, _, pv):
        self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.NONE)

        with self._disconnect_device():
            self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.INVALID, timeout=15)

        self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.NONE, timeout=15)

    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_power_is_set_THEN_status_bit_changes(self):
        self.ca.set_pv_value("POWER:SP", "On")
        # Don't yet know *which* status bit refers to POWER - guess B0 for the moment.
        self.ca.assert_that_pv_is("STATUS.B0", "1")

        self.ca.set_pv_value("POWER:SP", "Off")
        self.ca.assert_that_pv_is("STATUS.B0", "0")

    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_interlock_is_set_THEN_status_bit_changes(self):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, True])
        # Don't yet know *which* status bit refers to interlock(s) - guess B1 for the moment.
        self.ca.assert_that_pv_is("STATUS.B1", "1")

        self.ca.process_pv("RESET")
        self.ca.assert_that_pv_is("STATUS.B1", "0")
