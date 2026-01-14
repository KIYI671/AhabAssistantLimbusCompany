# DEV 标识水印组件
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QFont, QRegion, QTransform
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


class DevWatermark(QWidget):
    """开发模式水印，显示在窗口左上角的斜带"""
    
    RIBBON_CENTER_DIST = 40
    RIBBON_WIDTH = 24
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 透明度效果和动画
        self._op = QGraphicsOpacityEffect(self)
        self._op.setOpacity(1.0)
        self.setGraphicsEffect(self._op)
        
        self.anim_opacity = QPropertyAnimation(self._op, b"opacity")
        self.anim_opacity.setDuration(300)
        self.anim_opacity.setEasingCurve(QEasingCurve.OutCubic)
        
        self._updateMask()

    def _getRibbonRect(self) -> QRect:
        """获取丝带矩形"""
        return QRect(-100, self.RIBBON_CENTER_DIST - self.RIBBON_WIDTH // 2, 200, self.RIBBON_WIDTH)
    
    def _updateMask(self):
        """设置鼠标检测区域为丝带形状"""
        transform = QTransform()
        transform.rotate(-45)
        self.setMask(QRegion(transform.mapToPolygon(self._getRibbonRect())))

    def _animateOpacity(self, target: float):
        """动画过渡透明度"""
        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(self._op.opacity())
        self.anim_opacity.setEndValue(target)
        self.anim_opacity.start()

    def enterEvent(self, event):
        self._animateOpacity(0.05)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animateOpacity(1.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.rotate(-45)
        
        rect = self._getRibbonRect()
        
        # 绘制丝带背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#135b7d"))
        painter.drawRect(rect)
        
        # 绘制文字
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(rect, Qt.AlignCenter, "DEV")
