from lewis.adapters.stream import StreamInterface
from lewis.utils.command_builder import CmdBuilder
from lewis.core.logging import has_log
from lewis.utils.replies import conditional_reply


@has_log
class TranstechnikStreamInterface(StreamInterface):
    commands = {
        CmdBuilder("set_adr").escape("ADR ").int().build(),
        CmdBuilder("off").escape("F").build(),
        CmdBuilder("on").escape("N").build(),
        CmdBuilder("read_adc").escape("AD ").int().build(),
        CmdBuilder("set_dac").escape("DA ").int().escape(" ").int().build(),
        CmdBuilder("get_status").escape("S1").build(),
        CmdBuilder("reset").escape("RS").build(),
    }

    in_terminator = "\r"
    out_terminator = "\r"

    def __init__(self):
        super().__init__()

    @conditional_reply("connected")
    def set_adr(self, adr):
        self.device.address = adr

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
    def read_adc(self, adc_num):
        return self.device.supply().read_adc(adc_num)

    @conditional_reply("connected")
    def set_dac(self, dac_num, val):
        self.device.supply().set_dac(dac_num, val)

    @conditional_reply("connected")
    def get_status(self):
        def bit_to_str(b):
            return "." if b else "!"

        # Currently do not know what the status bits represent or what order they're in. Take a guess below and
        # update once we've tested with hardware.
        reply = "".join(bit_to_str(b) for b in [
            self.device.supply().interlock,
            self.device.supply().power,
        ])
        return reply

    @conditional_reply("connected")
    def reset(self):
        self.device.supply().interlock = False
