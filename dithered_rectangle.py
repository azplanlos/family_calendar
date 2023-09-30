try:
    from typing import Optional
except ImportError:
    pass

import displayio
import bitmaptools
import adafruit_display_shapes.rect

matrix = [
    [1, 0, 2],
    [8, 5, 6],
    [4, 7, 3],
]

class dithered_rectangle(displayio.TileGrid):

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: Optional[int] = None,
        outline: Optional[int] = None,
        opacity: Optional[float] = 1.0,
        stroke: int = 1,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Rectangle dimensions must be larger than 0.")

        self._bitmap = displayio.Bitmap(width, height, 3)
        self._palette = displayio.Palette(3)

        if outline is not None:
            self._palette[1] = outline
            self._palette.make_opaque(1)
            for w in range(width):
                for line in range(stroke):
                    self._bitmap[w, line] = 1
                    self._bitmap[w, height - 1 - line] = 1
            for _h in range(height):
                for line in range(stroke):
                    self._bitmap[line, _h] = 1
                    self._bitmap[width - 1 - line, _h] = 1

        if fill is not None:
            offset = stroke
            if outline is None:
                offset = 0
            if opacity is not None:
                val = 8 - (opacity * 8)
                print("val: " + str(val))
                for l in range(offset, height-offset):
                    for w in range(offset, width-offset):
                        if matrix[l % 3][w % 3] > val:
                            self._bitmap[w, l] = 2
            self._palette[2] = fill
            self._palette.make_opaque(2)
            self._palette[0] = 0
            self._palette.make_transparent(0)
        else:
            self._palette[0] = 0
            self._palette.make_transparent(0)
        super().__init__(self._bitmap, pixel_shader=self._palette, x=x, y=y)

    @property
    def fill(self) -> Optional[int]:
        """The fill of the rectangle. Can be a hex value for a color or ``None`` for
        transparent."""
        return self._palette[0]

    @fill.setter
    def fill(self, color: Optional[int]) -> None:
        if color is None:
            self._palette[0] = 0
            self._palette.make_transparent(0)
        else:
            self._palette[0] = color
            self._palette.make_opaque(0)

    @property
    def outline(self) -> Optional[int]:
        """The outline of the rectangle. Can be a hex value for a color or ``None``
        for no outline."""
        return self._palette[1]

    @outline.setter
    def outline(self, color: Optional[int]) -> None:
        if color is None:
            self._palette[1] = 0
            self._palette.make_transparent(1)
        else:
            self._palette[1] = color
            self._palette.make_opaque(1)

    @property
    def width(self) -> int:
        """
        :return: the width of the rectangle in pixels
        """
        return self._bitmap.width

    @property
    def height(self) -> int:
        """
        :return: the height of the rectangle in pixels
        """
        return self._bitmap.height