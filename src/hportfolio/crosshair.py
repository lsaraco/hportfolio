"""Graphic enhancement items."""
from PyQt5.QtChart import QAbstractSeries, QChart
from PyQt5.QtCore import QDateTime, QLineF, QPointF
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsScene, QGraphicsTextItem

from hportfolio.tickers_data import TickersData


class Crosshairs:
    """Class to implement dynamic crosshair on top of qchartview."""

    def __init__(self, chart: QChart, scene: QGraphicsScene, tickers_data: TickersData):
        """Constructor."""
        self.m_x_line = QGraphicsLineItem()
        self.m_y_line = QGraphicsLineItem()
        self.m_x_text = QGraphicsTextItem()
        self.m_y_text_list = [QGraphicsTextItem() for i in range(0, 3)]
        self.m_chart = chart

        self.m_x_line.setPen(QPen(QColor("red")))
        self.m_y_line.setPen(QPen(QColor("red")))

        self.m_x_text.setZValue(11)
        self.m_x_text.document().setDocumentMargin(0.0)
        self.m_x_text.setDefaultTextColor(QColor("white"))

        for text_item in self.m_y_text_list:
            text_item.setZValue(11)
            text_item.document().setDocumentMargin(0.0)
            text_item.setDefaultTextColor(QColor("white"))
            scene.addItem(text_item)

        # Tickers data
        self.tickers_data = tickers_data

        # add lines and text to scene
        scene.addItem(self.m_x_line)
        scene.addItem(self.m_y_line)
        scene.addItem(self.m_x_text)

        # Hysteresis for horizontal snap
        self.hyst = 1.0

    def get_y_value_of_series(self, series: QAbstractSeries, x: float | int) -> float:
        """Get Y value of a Q Line Series."""
        for qpoint in series.pointsVector():
            if qpoint.x() == x:
                return qpoint.y()
        return 0.0

    def update_position(self, position: float | int):
        """Update position based on mouse event."""
        # print(f'updating to : {position} for {self.m_chart}')

        x_ = self.m_chart.mapToValue(position).x() / 1000.0
        compare_val = (x_ % 86400) / 86400
        if compare_val > 0.5 * self.hyst:
            x_ = ((x_ // 86400) + 1) * 86400
            self.hyst = 0.9
        else:
            x_ = int(x_ / 86400) * 86400
            self.hyst = 1.1
        x_ = (x_ + 10800) * 1000
        position_x = self.m_chart.mapToPosition(QPointF(x_, 200)).x()

        x_line = QLineF(position_x, self.m_chart.plotArea().top(), position_x, self.m_chart.plotArea().bottom())
        y_line = QLineF(self.m_chart.plotArea().left(), position.y(), self.m_chart.plotArea().right(), position.y())
        self.m_x_line.setLine(x_line)
        self.m_y_line.setLine(y_line)

        portfolio_series: QAbstractSeries = self.m_chart.series()[1]
        x_date = QDateTime()
        x_date.setMSecsSinceEpoch(int(x_))
        x_date_str = x_date.toString("MM-dd-yy")
        x_date_str_2 = x_date.toString("yyyy-MM-dd")

        portfolio_value = round(self.get_y_value_of_series(portfolio_series, x_))
        invested_value = round(self.tickers_data.get_invested_cash(x_date_str_2))

        x_text = f"{x_date_str}"
        self.m_x_text.setHtml(f"<div style='background-color: #ff0000;'> {x_text} </div>")
        self.m_x_text.setPos(position.x() - self.m_x_text.boundingRect().width() / 2.0, self.m_chart.plotArea().bottom())

        if not (self.m_chart.plotArea().contains(position)):
            self.m_x_line.hide()
            self.m_x_text.hide()
            self.m_y_line.hide()
            for obj in self.m_y_text_list:
                obj.hide()
        else:
            self.m_x_line.show()
            self.m_x_text.show()
            self.m_y_line.show()
            y_labels = ["" for i in range(0, 3)]
            y_labels[0] = f"{portfolio_value}"
            y_labels[1] = f"${portfolio_value-invested_value:.0f}"
            y_labels[2] = f"{portfolio_value/invested_value*100.0-100:.1f}%"
            for i, obj in enumerate(self.m_y_text_list):
                obj.setHtml(f"<div style='background-color: #ff0000;'> {y_labels[i]} </div>")
                obj.setPos(self.m_chart.plotArea().right(), position.y() - obj.boundingRect().height() / 2.0 + i * 20)
                obj.show()
