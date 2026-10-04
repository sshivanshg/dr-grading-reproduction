"""Matplotlib renderer with the same drawing API as build_slides.py, producing a multi-page PDF."""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

plt.rcParams["font.family"] = ["Arial", "Arial Unicode MS", "DejaVu Sans"]
W, H = 13.333, 7.5
CHAR_W = 0.50  # average glyph width in em for Arial
LINE = 1.2


def hexc(rgb):
    return "#" + str(rgb)


class Deck:
    def __init__(self, path):
        self.pdf = PdfPages(path)
        self.fig = None

    def new(self):
        self.flush()
        self.fig = plt.figure(figsize=(W, H))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        return self.ax

    def flush(self):
        if self.fig is not None:
            self.pdf.savefig(self.fig)
            plt.close(self.fig)
            self.fig = None

    def close(self):
        self.flush()
        self.pdf.close()


def wrap(txt, width_in, size):
    cpl = max(4, int(width_in * 72 / (size * CHAR_W)))
    out = []
    for part in txt.split("\n"):
        out.extend(textwrap.wrap(part, cpl) or [""])
    return out


def draw_paragraphs(ax, x, y, w, h, paras, align="left", anchor="top"):
    """paras: list of (text, size, color, bold, space_after_pt, indent_in)."""
    blocks, total = [], 0.0
    for txt, size, color, bold, space, indent in paras:
        lines = wrap(txt, w - indent - 0.1, size)
        ph = len(lines) * size * LINE / 72
        blocks.append((lines, size, color, bold, ph, indent))
        total += ph + space / 72
    total -= paras[-1][4] / 72 if paras else 0
    cy = y + 0.05
    if anchor == "middle":
        cy = y + (h - total) / 2
    for (lines, size, color, bold, ph, indent), p in zip(blocks, paras):
        if align == "center":
            tx, ha = x + w / 2, "center"
        elif align == "right":
            tx, ha = x + w - 0.05, "right"
        else:
            tx, ha = x + 0.05 + indent, "left"
        ax.text(tx, cy, "\n".join(lines), fontsize=size, color=color, fontweight="bold" if bold else "normal",
                ha=ha, va="top", linespacing=LINE)
        cy += ph + p[4] / 72


def rect(ax, x, y, w, h, fill, rounded=True, edge=None):
    if rounded:
        r = 0.08 * min(w, h)
        p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fill,
                           ec=edge or "none", lw=1.25)
    else:
        p = Rectangle((x, y), w, h, fc=fill, ec=edge or "none", lw=1.25)
    ax.add_patch(p)


def picture(ax, path, x, y, w=None, h=None):
    img = mpimg.imread(str(path))
    ih, iw = img.shape[:2]
    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    ax.imshow(img, extent=[x, x + w, y + h, y], interpolation="antialiased", zorder=2)
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)


def grid(ax, x, y, rows, col_w, size, header_fill, row_h, highlight, colors):
    ink, light, white = colors
    cy = y
    for i, row in enumerate(rows):
        wrapped = [wrap(str(v), cw - 0.14, size) for v, cw in zip(row, col_w)]
        rh = max(row_h, max(len(l) for l in wrapped) * size * LINE / 72 + 0.1)
        cx = x
        for j, (lines, cw) in enumerate(zip(wrapped, col_w)):
            if i == 0:
                fill, fg, bold = header_fill, "#FFFFFF", True
            else:
                hl = highlight and i in highlight
                fill = highlight[i] if hl else (light if i % 2 else white)
                fg, bold = ink, bool(hl)
            ax.add_patch(Rectangle((cx, cy), cw, rh, fc=fill, ec="#FFFFFF", lw=1.0))
            if j == 0:
                ax.text(cx + 0.07, cy + rh / 2, "\n".join(lines), fontsize=size, color=fg, va="center", ha="left",
                        fontweight="bold" if bold else "normal", linespacing=LINE)
            else:
                ax.text(cx + cw / 2, cy + rh / 2, "\n".join(lines), fontsize=size, color=fg, va="center",
                        ha="center", fontweight="bold" if bold else "normal", linespacing=LINE)
            cx += cw
        cy += rh


def line_arrow(ax, x1, y1, x2, y2, color):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.25, mutation_scale=18))
