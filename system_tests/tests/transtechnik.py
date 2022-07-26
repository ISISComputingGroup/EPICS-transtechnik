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

VOLT_FULLSCALE = 150
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

INTERLOCKS = [
    ("power_on_cmd", "POWER_REQ"),
    ("pm1_error", "PM1_ERR"),
    ("pm2_error", "PM2_ERR"),
    ("pm3_error", "PM3_ERR"),
    ("pm4_error", "PM4_ERR"),
    ("pm5_error", "PM5_ERR"),
    ("in_error", "IN_ERR"),
    ("ru_error", "RU_ERR"),
    ("pm1_warning", "PM1_WARN"),
    ("pm2_warning", "PM2_WARN"),
    ("pm3_warning", "PM3_WARN"),
    ("pm4_warning", "PM4_WARN"),
    ("pm5_warning", "PM5_WARN"),
    ("in_warning", "IN_WARN"),
    ("ru_warning", "RU_WARN"),
    ("magnet_temp_interlock", "ILK:MAGNET_TEMP"),
    ("magnet_water_interlock", "ILK:MAGNET_WATER"),
    ("interlock_bps1", "ILK:BPS1"),
    ("interlock_bps2", "ILK:BPS2"),
    ("interlock_pps1", "ILK:PPS1"),
    ("interlock_pps2", "ILK:PPS2"),
    ("interlock_spare1", "ILK:SPARE1"),
    ("interlock_spare2", "ILK:SPARE2"),
    ("output_overvoltage", "OUTPUT:OVERVOLTAGE"),
    ("output_overcurrent", "OUTPUT:OVERCURRENT"),
    ("output_unbalanced", "OUTPUT:UNBALANCED"),
    ("em_stop", "ILK:EM_STOP"),
    ("door_open", "ILK:DOOR"),
    ("control_switch", "ILK:CONTROL_SWITCH"),
    ("self_test_failed", "ILK:SELF_TEST"),
]

TEST_MODES = [TestModes.DEVSIM]

TEST_VOLTAGES = [0, 0.1, VOLT_FULLSCALE/2, VOLT_FULLSCALE]
TEST_CURRENTS = [0, 0.1, CURR_FULLSCALE/2, CURR_FULLSCALE]


class TranstechnikTests(unittest.TestCase):

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_DEVICE, DEVICE_PREFIX)
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_wait_time=0., default_timeout=5)
        self.ca.assert_that_pv_is_number("VOLT:FULLSCALE", VOLT_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_is_number("CURR:FULLSCALE", CURR_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_exists("DISABLE", timeout=30)

    @parameterized.expand(parameterized_list(TEST_VOLTAGES))
    @skip_if_recsim("requires backdoor")
    def test_WHEN_voltage_is_set_via_backdoor_THEN_voltage_updates(self, _, val):
        self._lewis.backdoor_run_function_on_device("set_voltage", [0, val])
        self.ca.assert_that_pv_is_number("VOLT", val, tolerance=0.01)

    @parameterized.expand(parameterized_list(TEST_CURRENTS))
    @skip_if_recsim("Requires scaling logic not implemented in recsim")
    def test_WHEN_curr_is_set_THEN_current_updates(self, _, val):
        self.ca.set_pv_value("CURR:SP", val)
        self.ca.assert_that_pv_is_number("CURR", val, tolerance=0.01)

    @parameterized.expand(parameterized_list(TEST_CURRENTS))
    @skip_if_recsim("Requires scaling logic not implemented in recsim")
    def test_WHEN_curr_is_set_THEN_current_sp_rbv_updates(self, _, val):
        self.ca.set_pv_value("CURR:SP", val)
        self.ca.assert_that_pv_is_number("CURR:SP:RBV", val, tolerance=0.01)

    @contextlib.contextmanager
    def _disconnect_device(self):
        self._lewis.backdoor_set_on_device("connected", False)
        try:
            yield
        finally:
            self._lewis.backdoor_set_on_device("connected", True)

    @parameterized.expand(parameterized_list(
        ["VOLT", "CURR", "VOLT:RAW", "CURR:RAW", "STATUS"] + [pv for _, pv in INTERLOCKS]
    ))
    @skip_if_recsim("testing disconnection requires emulator")
    def test_WHEN_device_disconnected_THEN_pvs_in_alarm(self, _, pv):
        self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.NONE)

        with self._disconnect_device():
            self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.INVALID, timeout=15)

        self.ca.assert_that_pv_alarm_is(pv, self.ca.Alarms.NONE, timeout=15)

    @parameterized.expand(parameterized_list(INTERLOCKS))
    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_interlock_is_set_THEN_status_bit_changes(self, _, emulator_name, pv_name):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, True])
        self.ca.assert_that_pv_is(pv_name, "Tripped")

        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, False])
        self.ca.assert_that_pv_is(pv_name, "Ok")

    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_interlock_is_set_THEN_status_bit_changes(self):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, "is_remote", True])
        self.ca.assert_that_pv_is("MODE", "Remote")

        self._lewis.backdoor_run_function_on_device("set_interlock", [0, "is_remote", False])
        self.ca.assert_that_pv_is("MODE", "Local")

    @skip_if_recsim("Requires backdoor")
    def test_WHEN_power_on_via_backdoor_THEN_power_pv_is_on(self):
        self._lewis.backdoor_run_function_on_device("set_property", [0, "power", True])
        self.ca.assert_that_pv_is("POWER", "On")
        self._lewis.backdoor_run_function_on_device("set_property", [0, "power", False])
        self.ca.assert_that_pv_is("POWER", "Off")

    @skip_if_recsim("Requires interpreting status bits, not easy in recsim")
    def test_WHEN_set_power_THEN_power_updates(self):
        self.ca.set_pv_value("POWER:SP", "On")
        self.ca.assert_that_pv_is("POWER", "On")
        self.ca.set_pv_value("POWER:SP", "Off")
        self.ca.assert_that_pv_is("POWER", "Off")
