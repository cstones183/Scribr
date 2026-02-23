import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF

app = QApplication(sys.argv)

def create_menubar_icon(bg_hex: str, png_path: str, size: int):
    # Determine scaling factor (size = 22 or 44)
    scale = size / 22.0

    # ARGB32_Premultiplied for high quality transparency
    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. Draw the background rounded rectangle
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(bg_hex))
    # rx=5, ry=5 scaled out
    rx = 5.0 * scale
    p.drawRoundedRect(QRectF(0, 0, size, size), rx, rx)

    # 2. Punch out the mic shape using DestinationOut
    # (DestinationOut means where we draw solid white, it becomes transparent)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    p.setBrush(QColor("white"))
    pen = QPen(QColor("white"))
    pen.setWidthF(1.5 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    # Mic Body (rect x="8.5" y="1.5" width="5" height="10" rx="2.5")
    p.setPen(Qt.PenStyle.NoPen)
    body_x = 8.5 * scale
    body_y = 1.5 * scale
    body_w = 5.0 * scale
    body_h = 10.0 * scale
    body_r = 2.5 * scale
    p.drawRoundedRect(QRectF(body_x, body_y, body_w, body_h), body_r, body_r)

    # Mic Arc (path d="M4.5 9.5 Q4.5 15 11 15 Q17.5 15 17.5 9.5")
    # Using a simple arc or bezier curve.
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    arc_path = QPainterPath()
    arc_path.moveTo(4.5 * scale, 9.5 * scale)
    arc_path.quadTo(4.5 * scale, 15.0 * scale, 11.0 * scale, 15.0 * scale)
    arc_path.quadTo(17.5 * scale, 15.0 * scale, 17.5 * scale, 9.5 * scale)
    p.drawPath(arc_path)

    # Stand (line x1="11" y1="15" x2="11" y2="18.5")
    p.drawLine(QRectF(11.0 * scale, 15.0 * scale, 0, 3.5 * scale).center(), QRectF(11.0 * scale, 18.5 * scale, 0, 0).center())
    # Wait, better to draw lines with precise floats
    p.drawLine(int(11.0 * scale), int(15.0 * scale), int(11.0 * scale), int(18.5 * scale))

    # Base (line x1="8" y1="18.5" x2="14" y2="18.5")
    p.drawLine(int(8.0 * scale), int(18.5 * scale), int(14.0 * scale), int(18.5 * scale))

    p.end()
    image.save(png_path, "PNG")
    print(f"Saved {png_path} ({size}x{size})")

create_menubar_icon("#FFFFFF", "assets/menubar_idle.png", 22)
create_menubar_icon("#FFFFFF", "assets/menubar_idle@2x.png", 44)

create_menubar_icon("#D94F3D", "assets/menubar_recording.png", 22)
create_menubar_icon("#D94F3D", "assets/menubar_recording@2x.png", 44)

print("Done exporting PNGs.")
