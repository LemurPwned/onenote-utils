from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Tuple
from PIL import Image, ImageDraw
import os


@dataclass
class InkCoords:
    X: int
    Y: int
    F: int  # that seems to be the stroke weight


@dataclass
class Drawable:
    trace: List[InkCoords]

    def plot_on_canvas(self, image: ImageDraw, scale_x: float = 1, scale_y: float = 1):
        line_segs = [
            (
                tr.X*scale_x, tr.Y*scale_y
            ) for tr in self.trace
        ]
        image.line(line_segs, fill='black', width=3)


def read_file(filename: os.PathLike) -> Tuple[List[Drawable], int, int]:
    """Read the .xml InkNode file and return max canvas dims"""
    with open(filename, "r") as f:
        contents = f.read()
    soup = BeautifulSoup(contents, 'xml')
    # locate all the traces
    traces = soup.find_all('inkml:trace')
    trace_objs: List[Drawable] = []
    max_x = 0
    max_y = 0
    for trace in traces:
        trace_text = trace.get_text()
        trace_coords = trace_text.split(',')
        full_trace = []
        for tr in trace_coords:
            tr = tr.strip()
            x, y, f = tr.split(" ")
            x = int(x)
            y = int(y)
            full_trace.append(
                InkCoords(x, y, int(f))
            )
            max_x = max(max_x, x)
            max_y = max(max_y, y)
        trace_objs.append(
            Drawable(full_trace)
        )

    return trace_objs, max_x, max_y


def generate_image_from_xml(filename: os.PathLike,
                            max_pixel_density: int = 10000) -> Image:


trace_objs, max_x, max_y = read_file("test_note.xml")
print(max_x, max_y)
