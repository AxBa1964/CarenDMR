import sys
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QImage, QFont, QColor
from PyQt5.QtCore import Qt

class LedTextWidget(QWidget):
    def __init__(self, text="Empfang aktiv"):
        super().__init__()
        self.text = text
        self.dot_size = 6       # kleinere LEDs → schärfer
        self.spacing = 3        # engeres Raster
        self.threshold = 80     # früher LED-An
        self.setMinimumSize(600, 150)
        self.setWindowTitle("LED Schrift – Optimiert")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        # 1. Text in Graustufen-Image rendern
        img = QImage(self.width(), self.height(), QImage.Format_Grayscale8)
        img.fill(Qt.black)

        p = QPainter(img)
        p.setPen(Qt.white)
        p.setFont(QFont("Arial", 40, QFont.Bold))  # kleinerer Font → schärfer
        p.drawText(img.rect(), Qt.AlignCenter, self.text)
        p.end()

        # 2. LED-Punkte zeichnen
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 255, 0))

        step = self.dot_size + self.spacing

        for y in range(0, img.height(), step):
            for x in range(0, img.width(), step):
                gray = img.pixelColor(x, y).value()
                if gray > self.threshold:
                    # Punkt zentrieren
                    cx = x + self.dot_size / 2
                    cy = y + self.dot_size / 2
                    painter.drawEllipse(cx, cy, self.dot_size, self.dot_size)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LedTextWidget("Empfang aktiv")
    w.show()
    sys.exit(app.exec_())
