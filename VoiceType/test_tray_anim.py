import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import QTimer, Qt, QSize

app = QApplication(sys.argv)
tray = QSystemTrayIcon()
tray.show()

# Create idle and rec
pix_idle = QPixmap(22, 22)
pix_idle.fill(Qt.GlobalColor.transparent)
p1 = QPainter(pix_idle)
p1.setBrush(Qt.GlobalColor.black)
p1.drawRect(5, 5, 12, 12)
p1.end()
icon_idle = QIcon(pix_idle)
icon_idle.setIsMask(True)

pix_rec = QPixmap(22, 22)
pix_rec.fill(Qt.GlobalColor.transparent)
p2 = QPainter(pix_rec)
p2.setBrush(QColor('#D94F3D'))
p2.drawRect(5, 5, 12, 12)
p2.end()

phase = 0.0
def update_tray():
    global phase
    phase += 0.05
    if phase > 1.0:
        phase = 0.0
    
    # Just to test we can push pixel updates
    p = QPixmap(22, 22)
    p.fill(Qt.GlobalColor.transparent)
    painter = QPainter(p)
    painter.setOpacity(phase)
    painter.drawPixmap(0, 0, pix_rec)
    painter.end()
    icon = QIcon(p)
    tray.setIcon(icon)

timer = QTimer()
timer.timeout.connect(update_tray)
timer.start(16)

QTimer.singleShot(2000, app.quit)
app.exec()
