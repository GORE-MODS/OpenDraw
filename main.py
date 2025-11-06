# OpenDraw this will kinda help you understand.
"""
OpenDraw — Streamer-style multi-monitor desktop annotation tool (single-file).
Features:
 - Multi-monitor overlays (one overlay per screen)
 - Small always-on-top control window (tray icon included)
 - Undo/redo stack (configurable depth)
 - Smoother stroke smoothing (quadratic midpoint smoothing)
 - Pressure / pen tablet support (uses tabletEvent pressure if available)
 - Color picker, brush size slider, eraser toggle, clear, save, undo/redo, click-through per overlay

Dependencies:
    pip install PyQt5 Pillow

Usage:
    python main.py
"""
import sys
import os
import ctypes
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QPixmap, QGuiApplication, QPainterPath, QIcon, QTabletEvent
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QColorDialog,
    QVBoxLayout, QHBoxLayout, QSlider, QSystemTrayIcon, QMenu,
    QAction, QFileDialog, QMessageBox, QComboBox
)

IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    SetWindowLongPtr = user32.SetWindowLongPtrW
    GetWindowLongPtr = user32.GetWindowLongPtrW

MAX_UNDO = 30


def save_pixmap_to_file(pixmap, filename=None):
    if filename is None:
        save_dir = os.path.expanduser("~/Desktop")
        if not os.path.isdir(save_dir):
            save_dir = os.getcwd()
        idx = 1
        filename = os.path.join(save_dir, f"opendraw_{idx}.png")
        while os.path.exists(filename):
            idx += 1
            filename = os.path.join(save_dir, f"opendraw_{idx}.png")
    ok = pixmap.save(filename, "PNG")
    return ok, filename


class Overlay(QWidget):
    """A transparent overlay tied to one screen."""

    def __init__(self, screen, name=""):
        super().__init__()
        self.screen = screen
        geo = screen.geometry()
        self.name = name or f"Monitor {geo.width()}x{geo.height()}"
        self.setGeometry(geo)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CrossCursor)

        size = QSize(geo.width(), geo.height())
        self.image = QPixmap(size)
        self.image.fill(Qt.transparent)

        # Drawing state
        self.drawing = False
        self.points = []  # list of (QPoint, pressure)
        self.brush_color = QColor(255, 0, 0, 220)
        self.brush_size = 8
        self.eraser = False
        self.click_through = False
        self.pressure = 1.0

        # Undo/Redo
        self.undo_stack = []
        self.redo_stack = []

        # small status label
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet("color: white; background: rgba(0,0,0,140); padding:6px; border-radius:6px;")
        self.info_label.move(10, 10)
        self.update_info()

        # preview pixmap while drawing
        self.image_preview = None

        self.show()

    def update_info(self):
        mode = "Eraser" if self.eraser else "Brush"
        ct = "ON" if self.click_through else "OFF"
        self.info_label.setText(f"{self.name} | {mode} | Size: {self.brush_size} | Click-through: {ct}\nKeys: B/E/C/S +/- T Q H | Ctrl+Z/Y undo/redo")
        self.info_label.adjustSize()

    def set_click_through(self, enable: bool):
        if not IS_WINDOWS:
            # Other platforms need platform-specific handling; set flag for UI consistency.
            self.click_through = enable
            self.update_info()
            return
        hwnd = self.winId().__int__()
        ex = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
        if enable:
            new_ex = ex | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            new_ex = ex & (~WS_EX_TRANSPARENT)
        SetWindowLongPtr(hwnd, GWL_EXSTYLE, new_ex)
        self.click_through = enable
        self.update_info()

    # --- Input handling (mouse & tablet) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.click_through:
            self.push_undo()
            self.drawing = True
            self.points = []
            self.points.append((event.pos(), self.pressure))
            self.image_preview = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and not self.click_through:
            self.points.append((event.pos(), self.pressure))
            self.redraw_preview()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.commit_points_to_image()
            self.points = []
            self.image_preview = None
            self.update()

    def tabletEvent(self, event: QTabletEvent):
        # handle pen pressure (Qt supports tablet events if a tablet is present)
        try:
            p = float(event.pressure()) if event.pressure() is not None else 1.0
            self.pressure = max(0.01, p)
            if event.type() == QTabletEvent.TabletPress:
                self.push_undo()
                self.drawing = True
                self.points = []
                self.points.append((event.pos(), self.pressure))
                self.update()
            elif event.type() == QTabletEvent.TabletMove and self.drawing:
                self.points.append((event.pos(), self.pressure))
                self.redraw_preview()
            elif event.type() == QTabletEvent.TabletRelease:
                self.drawing = False
                self.commit_points_to_image()
                self.points = []
                self.image_preview = None
                self.update()
            event.accept()
        except Exception:
            # If tabletEvent API isn't fully supported, ignore gracefully.
            pass

    # --- Drawing & smoothing ---
    def points_to_path(self, pts):
        """Convert list of QPoint to a smoothed QPainterPath using midpoint quadratic smoothing."""
        if not pts:
            return QPainterPath()
        path = QPainterPath()
        path.moveTo(pts[0][0])
        if len(pts) == 1:
            return path
        for i in range(1, len(pts) - 1):
            p_curr = pts[i][0]
            p_next = pts[i + 1][0]
            mid_x = (p_curr.x() + p_next.x()) / 2.0
            mid_y = (p_curr.y() + p_next.y()) / 2.0
            mid = QPoint(int(mid_x), int(mid_y))
            path.quadTo(p_curr, mid)
        path.lineTo(pts[-1][0])
        return path

    def redraw_preview(self):
        """Draw a temporary preview combining base image + current stroke for immediate feedback."""
        preview = QPixmap(self.image)
        painter = QPainter(preview)
        painter.setRenderHint(QPainter.Antialiasing)
        if len(self.points) >= 2:
            for i in range(1, len(self.points)):
                p0, pr0 = self.points[i - 1]
                p1, pr1 = self.points[i]
                width = max(1.0, self.brush_size * ((pr0 + pr1) / 2.0))
                pen = QPen(self.brush_color if not self.eraser else QColor(0, 0, 0, 0), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                if self.eraser:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                else:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.drawLine(p0, p1)
        painter.end()
        self.image_preview = preview
        self.update()

    def commit_points_to_image(self):
        """Commit the current points (stroke) into the main image pixmap."""
        if not self.points:
            return
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw variable-width segments approximating pressure
        if len(self.points) >= 2:
            for i in range(1, len(self.points)):
                p0, pr0 = self.points[i - 1]
                p1, pr1 = self.points[i]
                width = max(1.0, int(self.brush_size * ((pr0 + pr1) / 2.0)))
                pen = QPen(self.brush_color if not self.eraser else QColor(0, 0, 0, 0), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                if self.eraser:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                else:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.drawLine(p0, p1)
        else:
            # single point
            pen = QPen(self.brush_color if not self.eraser else QColor(0, 0, 0, 0), max(1, int(self.brush_size * self.pressure)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            if self.eraser:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(pen)
            painter.drawPoint(self.points[0][0])
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.drawing and self.image_preview is not None:
            painter.drawPixmap(0, 0, self.image_preview)
        else:
            painter.drawPixmap(0, 0, self.image)

    # --- Undo / Redo ---
    def push_undo(self):
        if len(self.undo_stack) >= MAX_UNDO:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        self.update()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.update()

    # --- Keyboard shortcuts (per-overlay) ---
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_B:
            self.eraser = False
            self.update_info()
        elif key == Qt.Key_E:
            self.eraser = True
            self.update_info()
        elif key == Qt.Key_C:
            self.push_undo()
            self.image.fill(Qt.transparent)
            self.update()
        elif key == Qt.Key_S:
            ok, p = save_pixmap_to_file(self.image)
            if ok:
                print("Saved:", p)
            else:
                print("Save failed")
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self.brush_size = min(300, self.brush_size + 2)
            self.update_info()
        elif key in (Qt.Key_Minus, Qt.Key_Underscore):
            self.brush_size = max(1, self.brush_size - 2)
            self.update_info()
        elif key == Qt.Key_T:
            self.set_click_through(not self.click_through)
        elif key == Qt.Key_Q:
            QApplication.quit()
        elif key == Qt.Key_H:
            self.info_label.setVisible(not self.info_label.isVisible())
        elif key == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo()
        elif key == Qt.Key_Y and (event.modifiers() & Qt.ControlModifier):
            self.redo()
        else:
            super().keyPressEvent(event)


class ControlWindow(QWidget):
    """Small always-on-top control window for managing overlays."""

    def __init__(self, overlays):
        super().__init__()
        self.overlays = overlays
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("OpenDraw Controls")
        self.setFixedSize(380, 150)

        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        self.monitor_select = QComboBox()
        for o in overlays:
            self.monitor_select.addItem(o.name, userData=o)
        top_row.addWidget(self.monitor_select)

        self.ct_button = QPushButton("Toggle Click-through")
        self.ct_button.clicked.connect(self.toggle_click_through_selected)
        top_row.addWidget(self.ct_button)
        layout.addLayout(top_row)

        row2 = QHBoxLayout()
        self.brush_btn = QPushButton("Brush")
        self.brush_btn.clicked.connect(self.set_brush)
        row2.addWidget(self.brush_btn)
        self.eraser_btn = QPushButton("Eraser")
        self.eraser_btn.clicked.connect(self.set_eraser)
        row2.addWidget(self.eraser_btn)
        self.color_btn = QPushButton("Color")
        self.color_btn.clicked.connect(self.pick_color)
        row2.addWidget(self.color_btn)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        size_label = QLabelFixedWidth("Size", 40)
        row3.addWidget(size_label)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 150)
        self.size_slider.setValue(8)
        self.size_slider.valueChanged.connect(self.change_size)
        row3.addWidget(self.size_slider)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo_selected)
        row4.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.clicked.connect(self.redo_selected)
        row4.addWidget(self.redo_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_selected)
        row4.addWidget(self.clear_btn)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_selected)
        row4.addWidget(self.save_btn)
        layout.addLayout(row4)

        self.setLayout(layout)

        # System tray (optional)
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray_icon = QSystemTrayIcon(QIcon.fromTheme("applications-graphics"), self)
            menu = QMenu()
            show_action = QAction("Show Controls", self)
            show_action.triggered.connect(self.show)
            menu.addAction(show_action)
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.quit)
            menu.addAction(quit_action)
            tray_icon.setContextMenu(menu)
            tray_icon.activated.connect(self._tray_activated)
            tray_icon.show()
            self.tray_icon = tray_icon

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()

    def selected_overlay(self):
        idx = self.monitor_select.currentIndex()
        return self.monitor_select.itemData(idx)

    def toggle_click_through_selected(self):
        o = self.selected_overlay()
        if o:
            o.set_click_through(not o.click_through)

    def set_brush(self):
        o = self.selected_overlay()
        if o:
            o.eraser = False
            o.update_info()

    def set_eraser(self):
        o = self.selected_overlay()
        if o:
            o.eraser = True
            o.update_info()

    def pick_color(self):
        o = self.selected_overlay()
        if o:
            color = QColorDialog.getColor(initial=o.brush_color, parent=self, title="Pick brush color")
            if color.isValid():
                o.brush_color = color
                o.update_info()

    def change_size(self, val):
        o = self.selected_overlay()
        if o:
            o.brush_size = val
            o.update_info()

    def undo_selected(self):
        o = self.selected_overlay()
        if o:
            o.undo()

    def redo_selected(self):
        o = self.selected_overlay()
        if o:
            o.redo()

    def clear_selected(self):
        o = self.selected_overlay()
        if o:
            o.push_undo()
            o.image.fill(Qt.transparent)
            o.update()

    def save_selected(self):
        o = self.selected_overlay()
        if o:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save PNG", os.path.expanduser("~/Desktop/opendraw.png"), "PNG Files (*.png)")
            if save_path:
                ok = o.image.save(save_path, "PNG")
                if ok:
                    QMessageBox.information(self, "Saved", f"Saved to: {save_path}")
                else:
                    QMessageBox.warning(self, "Failed", "Failed to save image.")


class QLabelFixedWidth(QLabel):
    def __init__(self, text, width):
        super().__init__(text)
        self.setFixedWidth(width)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    screens = QGuiApplication.screens()
    overlays = []
    for i, screen in enumerate(screens):
        name = f"Monitor {i + 1} ({screen.geometry().width()}x{screen.geometry().height()})"
        o = Overlay(screen, name=name)
        overlays.append(o)
    control = ControlWindow(overlays)
    control.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
