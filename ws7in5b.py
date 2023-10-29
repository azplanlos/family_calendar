import displayio

_START_SEQUENCE = (
    b"\x01\x04\x07\x07\x3f\x3f"
    b"\x04\x80\xc8"
    b"\x00\x01\x0f"
    b"\x61\x04\x03\x20\x01\xe0"
    b"\x15\x01\x00"
    b"\x50\x02\x11\x07"
    b"\x60\x01\x22"
    b"\x65\x04\x00\x00\x00\x00"
)

_STOP_SEQUENCE = (
    b"\x02\x00"
    b"\x07\x01\xa5"
)


# pylint: disable=too-few-public-methods
class WS7IN5B(displayio.EPaperDisplay):
    def __init__(self, bus: displayio.FourWire, **kwargs) -> None:
        write_black_ram_command = 0x10
        write_color_ram_command = 0x13
        super().__init__(
            bus,
            _START_SEQUENCE,
            _STOP_SEQUENCE,
            **kwargs,
            ram_width=800,
            ram_height=480,
#            ram_width=160,
#            ram_height=296,
            busy_state=False,
            write_black_ram_command=write_black_ram_command,
            write_color_ram_command=write_color_ram_command,
            color_bits_inverted=False,
            refresh_display_command=0x12,
        )
