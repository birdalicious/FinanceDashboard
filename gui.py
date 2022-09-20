from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
from database import DatabaseHandler

db = DatabaseHandler("test.db")


class Step(QtWidgets.QWidget):
    def __init__(self, transaction):
        super(Step, self).__init__()
        uic.loadUi("step.ui", self)
        
        cat = transaction['classification']

        self.date.setText(transaction['timestamp'])
        self.merchantName.setText(transaction['merchant_name'])
        self.amount.setText(f"£ {transaction['amount']:,.2f}")
        self.category.setText(cat[0])
        self.subcategory.setText(cat[1])


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        
        self.scroll = QtWidgets.QScrollArea()             # Scroll Area which contains the widgets, set as the centralWidget
        self.widget = QtWidgets.QWidget()                 # Widget that contains the collection of Vertical Box
        self.vbox = QtWidgets.QVBoxLayout()               # The Vertical Box that contains the Horizontal Boxes of  labels and buttons

        for i in range(10):
            transaction = {
                'timestamp': '20 Jun. 2022',
                'merchant_name': 'Asda',
                'classification': ['Shopping', 'Food'],
                'amount': -10
            }
            object =  Step(transaction)
            self.vbox.addWidget(object)

        self.vbox.setSpacing(0)
        self.widget.setLayout(self.vbox)

        #Scroll Area Properties
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.widget)

        self.setCentralWidget(self.scroll)
        
app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec_()

