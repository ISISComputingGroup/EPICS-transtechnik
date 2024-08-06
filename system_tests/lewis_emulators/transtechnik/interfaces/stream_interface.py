from lewis.adapters.stream import StreamInterface
from lewis.core.logging import has_log
from lewis.utils.command_builder import CmdBuilder
from lewis.utils.replies import conditional_reply

from ..device import INTERLOCKS


@has_log
class TranstechnikStreamInterface(StreamInterface):
    commands = {
        CmdBuilder("set_adr").escape("ADR ").int().eos().build(),
        CmdBuilder("off").escape("F").eos().build(),
        CmdBuilder("on").escape("N").eos().build(),
        CmdBuilder("read_curr").escape("AD 1").eos().build(),
        CmdBuilder("read_volt").escape("AD 2").eos().build(),
        CmdBuilder("read_curr_sp").escape("RA").eos().build(),
        CmdBuilder("set_curr").escape("WA ").int().eos().build(),
        CmdBuilder("get_status").escape("S0").eos().build(),
        CmdBuilder("reset").escape("RS").eos().build(),
    }

    in_terminator = "\r"
    out_terminator = "\r"

    def __init__(self):
        super().__init__()

    @conditional_reply("connected")
    def set_adr(self, adr):
        self.device.address = int(adr)

    @conditional_reply("connected")
    def off(self):
        self.device.supply().power = False

    @conditional_reply("connected")
    def on(self):
        self.device.supply().power = True

    @conditional_reply("connected")
    def reset(self):
        self.device.supply().reset()

    @conditional_reply("connected")
    def read_curr(self):
        return int(
            (self.device.supply().current / self.device.supply().fullscale_current) * 100_000.0
        )

    @conditional_reply("connected")
    def read_volt(self):
        return int(
            (self.device.supply().voltage / self.device.supply().fullscale_voltage) * 100_000.0
        )

    @conditional_reply("connected")
    def read_curr_sp(self):
        return int(
            (self.device.supply().current / self.device.supply().fullscale_current) * 100_000.0
        )

    @conditional_reply("connected")
    def set_curr(self, val):
        self.device.supply().current = (val / 1_000_000.0) * self.device.supply().fullscale_current

    @conditional_reply("connected")
    def get_status(self):
        def bit_to_str(b):
            return "!" if b else "."

        vals = [not self.device.supply().power] + [
            self.device.supply().interlocks[k] for k in INTERLOCKS
        ]
        reply = "".join(bit_to_str(b) for b in vals)
        print(f"status reply: {reply}")
        return reply

    @conditional_reply("connected")
    def reset(self):
        for ilk in INTERLOCKS:
            self.device.supply().interlocks[ilk] = False
