from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
from database import DatabaseHandler
import json

class Uncategorised(QtWidgets.QWidget):
    def __init__(self, transaction):
        super(Uncategorised, self).__init__()
        uic.loadUi("ui/uncategorised.ui", self)

        self.date.setText(transaction['timestamp'])
        self.description.setText(transaction['description'])
        self.amount.setText(f"£ {transaction['amount']:,.2f}")

class Categorised(QtWidgets.QWidget):
    def __init__(self, transaction):
        super(Categorised, self).__init__()
        uic.loadUi("ui/categorised.ui", self)

        self.date.setText(transaction['timestamp'])
        self.merchantName.setText(transaction['merchant_name'])
        self.amount.setText(f"£ {transaction['amount']:,.2f}")

        if transaction['classification']:
            cat1, cat2 = transaction['classification']
            self.category.setText(cat1)
            self.subcategory.setText(cat2)


class EditTransactionDialog(QtWidgets.QDialog):
    def __init__(self, row, transaction, listView):
        super(EditTransactionDialog, self).__init__()
        uic.loadUi("ui/transactionEditDialog.ui", self)

        self.row = row
        self.listView = listView

        self.id = transaction['id']
        self.date.setText(transaction['timestamp'])
        self.merchantName.setText(transaction['merchant_name'])
        self.description.setText(transaction['description'])
        self.amount.setText(f"£ {transaction['amount']:,.2f}")

        with open("categories.json", "r") as f:
            self.categoryData = json.load(f)
        self.mainCategories = [cat["classification_category"] for cat in self.categoryData]
        self.mainCategories.insert(0, "")

        self.mainCategory.addItems(self.mainCategories)
        
        if transaction['classification']:
            main, sub = transaction['classification']
            self.setComboBoxCategory(main)
            self.setComboBoxSubCategory(sub)
            
        self.mainCategory.currentTextChanged.connect(self.setComboBoxCategory)

        self.buttonBox.accepted.connect(self.accepted)

    def setComboBoxCategory(self, category):
        index = self.mainCategories.index(category)

        self.mainCategory.setCurrentIndex(index)

        subs = [""] + self.categoryData[index-1]["sub_classification_categories"]
        self.subCategory.clear()
        self.subCategory.addItems(subs)

    def setComboBoxSubCategory(self, sub):
        index = self.mainCategory.currentIndex()
        subs = self.categoryData[index-1]["sub_classification_categories"]

        index = subs.index(sub)
        self.subCategory.setCurrentIndex(index+1)

    def accepted(self):
        mainCat = self.mainCategory.currentText()
        subCat = self.subCategory.currentText()

        update = {
            'id': self.id,
            'merchant_name': self.merchantName.text(),
            'classification': [mainCat, subCat] if mainCat and subCat else [],
            'description': self.description.toPlainText(),
        }

        self.listView.updateRow(self.row, update)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi("ui/transactionList.ui", self)
        
        self.editButton.clicked.connect(self.editClick)

        self.db = DatabaseHandler("test.db")
        account_id = self.db.getAccounts()[0]['account_id']
        transactions = self.db.getTransactions(account_id, "2022-08-01", "2022-08-31")

        for transaction in transactions[::-1]:
            self.addTransaction(transaction)


    def addTransaction(self, transaction, row=-1):
        if transaction['merchant_name']:
            object =  Categorised(transaction)
        else:
            object =  Uncategorised(transaction)

        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, transaction['id'])
        item.setSizeHint(object.sizeHint())

        if row == -1:
            self.transactionListWidget.addItem(item)
            self.transactionListWidget.setItemWidget(item, object)
        else:
            print(row)
            self.transactionListWidget.insertItem(row, item)
            self.transactionListWidget.setItemWidget(item, object)
    
    def updateRow(self, row, update):
        print(row, update)
        self.transactionListWidget.takeItem(row)
        self.db.updateTransaction(**update)
        transaction = self.db.getTransaction(id=update['id'])
        self.addTransaction(transaction, row=row)
        self.transactionListWidget.setCurrentRow(row)

    def editClick(self):
        listWidget = self.transactionListWidget
        selected = listWidget.selectedItems()
        if selected:
            row = listWidget.currentRow()
            id = selected[0].data(QtCore.Qt.UserRole)
            transaction = self.db.getTransaction(id = id)

            self.dialog = EditTransactionDialog(row, transaction, self)
            self.dialog.show()
            


app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec_()