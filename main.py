# project has been discontinued. you can try to fix it.
# OpenDraw - Streamer desktop drawing overlay for Windows 11
# Requires: pip install PyQt5 Pillow
import sys, os, ctypes
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QColorDialog, QSpinBox, QHBoxLayout
)

IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020

def set_clickthrough(hwnd, enable):
    if not IS_WINDOWS:
        return
    ex = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if enable:
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    else:
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex & ~WS_EX_TRANSPARENT)

class DrawOverlay(QWidget):
    def __init__(self, geometry):
        super().__init__()
        self.setGeometry(geometry)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        self.image = QPixmap(self.size())
        self.image.fill(Qt.transparent)
        self.brush_color = QColor(255, 0, 0)
        self.brush_size = 6
        self.drawing = False
        self.last_point = QPoint()
        self.eraser = False
        self.click_through = False
        self.undo_stack, self.redo_stack = [], []

        self.show()

    def paintEvent(self, e):
        qp = QPainter(self)
        qp.drawPixmap(0, 0, self.image)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.click_through:
            self.drawing = True
            self.last_point = e.pos()
            self._draw_line(e.pos())

    def mouseMoveEvent(self, e):
        if self.drawing and not self.click_through:
            self._draw_line(e.pos())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.undo_stack.append(self.image.copy())
            self.redo_stack.clear()

    def _draw_line(self, pos):
        p = QPainter(self.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.eraser:
            p.setCompositionMode(QPainter.CompositionMode_Clear)
        pen = QPen(self.brush_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(self.last_point, pos)
        self.last_point = pos
        self.update()

    def clear(self):
        self.image.fill(Qt.transparent)
        self.update()

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        self.update()

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.update()

    def toggle_click(self):
        self.click_through = not self.click_through
        set_clickthrough(self.winId().__int__(), self.click_through)

class ControlPanel(QWidget):
    def __init__(self, overlays):
        super().__init__()
        self.overlays = overlays
        self.setWindowTitle("OpenDraw")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setGeometry(100, 100, 260, 130)

        self.brush_size = QSpinBox()
        self.brush_size.setRange(1, 100)
        self.brush_size.setValue(6)
        self.brush_size.valueChanged.connect(self.update_size)

        color_btn = QPushButton("Color")
        color_btn.clicked.connect(self.pick_color)

        erase_btn = QPushButton("Eraser")
        erase_btn.clicked.connect(self.toggle_eraser)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)

        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self.undo)

        redo_btn = QPushButton("Redo")
        redo_btn.clicked.connect(self.redo)

        click_btn = QPushButton("Click-through")
        click_btn.clicked.connect(self.toggle_click)

        layout = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(color_btn)
        top.addWidget(self.brush_size)
        layout.addLayout(top)
        layout.addWidget(erase_btn)
        layout.addWidget(clear_btn)
        layout.addWidget(undo_btn)
        layout.addWidget(redo_btn)
        layout.addWidget(click_btn)
        self.setLayout(layout)

    def each(self, func):
        for o in self.overlays:
            func(o)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.each(lambda o: setattr(o, "brush_color", color))

    def update_size(self, v):
        self.each(lambda o: setattr(o, "brush_size", v))

    def toggle_eraser(self):
        for o in self.overlays:
            o.eraser = not o.eraser

    def clear(self):
        self.each(lambda o: o.clear())

    def undo(self):
        self.each(lambda o: o.undo())

    def redo(self):
        self.each(lambda o: o.redo())

    def toggle_click(self):
        self.each(lambda o: o.toggle_click())

def main():
    app = QApplication(sys.argv)
    screens = QGuiApplication.screens()
    overlays = [DrawOverlay(s.geometry()) for s in screens]
    ctrl = ControlPanel(overlays)
    ctrl.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
