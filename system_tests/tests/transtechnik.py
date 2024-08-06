import contextlib
import unittest

from parameterized import parameterized
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import (
    get_running_lewis_and_ioc,
    parameterized_list,
    skip_if_recsim,
)

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
            "LIMIT_ALARM": "MAJOR",
        },
    },
]

ILK = [
    ("magnet_temp_interlock", "ILK:MAGNET_TEMP"),
    ("magnet_water_interlock", "ILK:MAGNET_WATER"),
    ("interlock_bps1", "ILK:BPS1"),
    ("interlock_bps2", "ILK:BPS2"),
    ("interlock_pps1", "ILK:PPS1"),
    ("interlock_pps2", "ILK:PPS2"),
    ("interlock_spare1", "ILK:SPARE1"),
    ("interlock_spare2", "ILK:SPARE2"),
    ("em_stop", "ILK:EM_STOP"),
    ("door_open", "ILK:DOOR"),
    ("control_switch", "ILK:CONTROL_SWITCH"),
    ("self_test_failed", "ILK:SELF_TEST"),
]
OUTPUT_ILK = [
    ("output_overvoltage", "OUTPUT:OVERVOLTAGE"),
    ("output_overcurrent", "OUTPUT:OVERCURRENT"),
    ("output_unbalanced", "OUTPUT:UNBALANCED"),
]
ERRORS = [
    ("pm1_error", "PM1_ERR"),
    ("pm2_error", "PM2_ERR"),
    ("pm3_error", "PM3_ERR"),
    ("pm4_error", "PM4_ERR"),
    ("pm5_error", "PM5_ERR"),
    ("in_error", "IN_ERR"),
    ("ru_error", "RU_ERR"),
]
WARNINGS = [
    ("pm1_warning", "PM1_WARN"),
    ("pm2_warning", "PM2_WARN"),
    ("pm3_warning", "PM3_WARN"),
    ("pm4_warning", "PM4_WARN"),
    ("pm5_warning", "PM5_WARN"),
    ("in_warning", "IN_WARN"),
    ("ru_warning", "RU_WARN"),
]
INTERLOCKS = [("power_on_cmd", "POWER_REQ")] + ERRORS + WARNINGS + ILK + OUTPUT_ILK

TEST_MODES = [TestModes.DEVSIM]

TEST_VOLTAGES = [0, 0.1, VOLT_FULLSCALE / 2, VOLT_FULLSCALE]
TEST_CURRENTS = [0, 0.1, CURR_FULLSCALE / 2, CURR_FULLSCALE]

INRUSH_WAIT_TIME = 10


class TranstechnikTests(unittest.TestCase):
    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_DEVICE, DEVICE_PREFIX)
        self.ca = ChannelAccess(
            device_prefix=DEVICE_PREFIX, default_wait_time=0.0, default_timeout=5
        )
        self.ca.assert_that_pv_is_number("VOLT:FULLSCALE", VOLT_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_is_number("CURR:FULLSCALE", CURR_FULLSCALE, tolerance=0.01)
        self.ca.assert_that_pv_exists("DISABLE", timeout=30)

        # Ensure statemachine is not busy before running each test
        self.ca.assert_that_pv_is("STATEMACHINE:STATE", "idle", timeout=3 * INRUSH_WAIT_TIME)
        self.ca.set_pv_value("STATEMACHINE:INRUSH_WAIT", INRUSH_WAIT_TIME)

        # Set Limits so that all values are within limits
        self.ca.set_pv_value("VOLT.HIGH", VOLT_FULLSCALE + 1)
        self.ca.set_pv_value("VOLT.LOW", -1)
        self.ca.set_pv_value("CURR.HIGH", CURR_FULLSCALE + 1)
        self.ca.set_pv_value("CURR.LOW", -1)

    @parameterized.expand(parameterized_list(TEST_VOLTAGES))
    @skip_if_recsim("requires backdoor")
    def test_WHEN_voltage_is_set_via_backdoor_THEN_voltage_updates(self, _, val):
        self._lewis.backdoor_run_function_on_device("set_voltage", [0, val])
        self.ca.assert_that_pv_is_number("VOLT", val, tolerance=0.01)

    @parameterized.expand(
        [
            ("_within_limits", VOLT_FULLSCALE, TEST_VOLTAGES[-2], 0, "No"),
            ("_outside_limits", TEST_VOLTAGES[-2], VOLT_FULLSCALE, 1, "VOLT LIMIT"),
        ]
    )
    @skip_if_recsim("requires backdoor")
    def test_WHEN_voltage_is_set_via_backdoor_AND_limits_set_THEN_limit_correct(
        self, _, limit, voltage, limit_status, alarm_enum
    ):
        self.ca.set_pv_value("VOLT.HIGH", limit)
        self.ca.set_pv_value("VOLT.LOW", 0)
        self._lewis.backdoor_run_function_on_device("set_voltage", [0, voltage])
        self.ca.assert_that_pv_is_number("VOLT", voltage, tolerance=0.01)
        self.ca.assert_that_pv_is("LIMIT", limit_status)
        self.ca.assert_that_pv_is("ALARM:ENUM", alarm_enum)

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

    @parameterized.expand(
        [
            ("_within_limits", CURR_FULLSCALE, TEST_CURRENTS[-2], 0, "No"),
            ("_outside_limits", TEST_CURRENTS[-2], CURR_FULLSCALE, 2, "CURR LIMIT"),
        ]
    )
    @skip_if_recsim("Requires scaling logic not implemented in recsim")
    def test_WHEN_current_is_set_AND_limits_set_THEN_limit_correct(
        self, _, limit, curr, limit_status, alarm_enum
    ):
        self.ca.set_pv_value("CURR.HIGH", limit)
        self.ca.set_pv_value("CURR.LOW", 0)
        self.ca.set_pv_value("CURR:SP", curr)
        self.ca.assert_that_pv_is_number("CURR", curr, tolerance=0.01)
        self.ca.assert_that_pv_is("LIMIT", limit_status)
        self.ca.assert_that_pv_is("ALARM:ENUM", alarm_enum)

    @contextlib.contextmanager
    def _disconnect_device(self):
        self._lewis.backdoor_set_on_device("connected", False)
        try:
            yield
        finally:
            self._lewis.backdoor_set_on_device("connected", True)

    @parameterized.expand(
        parameterized_list(
            ["VOLT", "CURR", "VOLT:RAW", "CURR:RAW", "STATUS"] + [pv for _, pv in INTERLOCKS]
        )
    )
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

    @parameterized.expand(
        parameterized_list(
            [(emulator_name, pv_name, "ILK") for emulator_name, pv_name in ILK]
            + [(emulator_name, pv_name, "ILK:OUTPUT") for emulator_name, pv_name in OUTPUT_ILK]
        )
    )
    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_interlock_is_set_THEN_ilk_summary_correct(
        self, _, emulator_name, pv_name, summary
    ):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, True])
        self.ca.assert_that_pv_is(pv_name, "Tripped")
        self.ca.assert_that_pv_is(summary, 1)
        self.ca.assert_that_pv_is("ILK:SUMMARY", 1)
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, False])
        self.ca.assert_that_pv_is(pv_name, "Ok")
        self.ca.assert_that_pv_is(summary, 0)
        self.ca.assert_that_pv_is("ILK:SUMMARY", 0)

    @parameterized.expand(
        parameterized_list(
            [(emulator_name, pv_name, "ERROR") for emulator_name, pv_name in ERRORS]
            + [(emulator_name, pv_name, "WARNING") for emulator_name, pv_name in WARNINGS]
        )
    )
    @skip_if_recsim("status bits do not change in recsim")
    def test_WHEN_warning_or_error_is_set_THEN_ilk_summary_correct(
        self, _, emulator_name, pv_name, summary
    ):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, True])
        self.ca.assert_that_pv_is(pv_name, "Tripped")
        self.ca.assert_that_pv_is(f"{summary}:SUMMARY", 1)
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, emulator_name, False])
        self.ca.assert_that_pv_is(pv_name, "Ok")
        self.ca.assert_that_pv_is(f"{summary}:SUMMARY", 0)

    @skip_if_recsim("Requires backdoor")
    def test_WHEN_power_on_via_backdoor_THEN_power_pv_is_on(self):
        self._lewis.backdoor_run_function_on_device("set_property", [0, "power", True])
        self.ca.assert_that_pv_is("POWER", "On")
        self._lewis.backdoor_run_function_on_device("set_property", [0, "power", False])
        self.ca.assert_that_pv_is("POWER", "Off")

    @skip_if_recsim("Requires interpreting status bits, not easy in recsim")
    def test_WHEN_set_power_THEN_power_updates(self):
        initial_power_proccnt = int(self.ca.get_pv_value("POWER:SP:PROC_CNT"))
        self.ca.set_pv_value("POWER:SP", "On")
        self.ca.assert_that_pv_is("POWER:SP:PROC_CNT", initial_power_proccnt + 1)
        self.ca.assert_that_pv_is("POWER", "On")
        self.ca.set_pv_value("POWER:SP", "Off")
        self.ca.assert_that_pv_is("POWER:SP:PROC_CNT", initial_power_proccnt + 2)

        # Since we recently did a set, turning power off should not go through straight away
        self.ca.assert_that_pv_is("POWER", "On")
        self.ca.assert_that_pv_value_is_unchanged("POWER", wait=INRUSH_WAIT_TIME / 2.0)

        # Once we have waited for inrush current from first setpoint to go through, then our power off command
        # should be acted on.
        self.ca.assert_that_pv_is("POWER", "Off", timeout=INRUSH_WAIT_TIME)

    def test_WHEN_reset_sent_THEN_interlocks_cleared(self):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, "interlock_spare1", True])
        self.ca.assert_that_pv_is("ILK:SPARE1", "Tripped")

        self.ca.process_pv("RESET")
        self.ca.assert_that_pv_is("ILK:SPARE1", "Ok")
        self.ca.assert_that_pv_is("ILK:SUMMARY", 0)
        self.ca.assert_that_pv_is("ILK", 0)

    def test_WHEN_sets_all_changed_at_once_THEN_waits_for_inrush_correctly(self):
        self._lewis.backdoor_run_function_on_device("set_interlock", [0, "interlock_spare1", True])
        self.ca.assert_that_pv_is("ILK:SPARE1", "Tripped")

        self._lewis.backdoor_run_function_on_device("set_property", [0, "power", False])
        self.ca.assert_that_pv_is("POWER", "Off")

        self._lewis.backdoor_run_function_on_device("set_property", [0, "current", 0])
        self.ca.assert_that_pv_is("CURR", 0)
        self.ca.assert_that_pv_is("CURR:SP:RBV", 0)

        # Try to send reset/power/current quickly.
        self.ca.process_pv("RESET:SP")
        self.ca.set_pv_value("POWER:SP", "On")
        self.ca.set_pv_value("CURR:SP", 5.4321)

        self.ca.assert_that_pv_is(
            "ILK:SPARE1", "Ok"
        )  # Reset should happen first and relatively quickly

        # Assert that power is not being changed while reset is being waited for
        self.ca.assert_that_pv_is("POWER", "Off")
        self.ca.assert_that_pv_value_is_unchanged("POWER", wait=INRUSH_WAIT_TIME / 2.0)
        # Now assert that power does get turned on once the appropriate wait is complete
        self.ca.assert_that_pv_is("POWER", "On", timeout=INRUSH_WAIT_TIME)

        # Current should still not have been set yet
        self.ca.assert_that_pv_is("CURR", 0)
        self.ca.assert_that_pv_is("CURR:SP:RBV", 0)
        self.ca.assert_that_pv_value_is_unchanged("CURR", wait=INRUSH_WAIT_TIME / 2.0)

        # Then after another appropriate wait (waiting for power) then current is set
        self.ca.assert_that_pv_is_number("CURR", 5.4321, tolerance=0.01, timeout=INRUSH_WAIT_TIME)
        self.ca.assert_that_pv_is_number("CURR:SP:RBV", 5.4321, tolerance=0.01)

        # And now statemachine should be idle and PSU should be in fully correct state
        self.ca.assert_that_pv_is("STATEMACHINE:STATE", "idle")
        self.ca.assert_that_pv_is("ILK:SPARE1", "Ok")
        self.ca.assert_that_pv_is("POWER", "On")
        self.ca.assert_that_pv_is_number("CURR", 5.4321, tolerance=0.01)
        self.ca.assert_that_pv_is_number("CURR:SP:RBV", 5.4321, tolerance=0.01)
