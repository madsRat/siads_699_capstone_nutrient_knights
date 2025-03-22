from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from aiohttp import worker

from nutrient_analysis import Ui_main_window
import sys
import os

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_main_window()
        self.ui.setupUi(self)
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(4)

        self.ui.pushButton_calculate.clicked.connect(self.start_rd_chatbot_thread)

    def start_rd_chatbot_thread(self):
        worker = Worker_rd_chatbot()
        self.threadpool.start(worker)
        print('started thread.')

        import time
        time.sleep(0.5)

        print('Loading chatbot into gui.')
        from PyQt5.QtCore import QUrl
        self.ui.webEngineView_rd_chatbot.load(QUrl("http://localhost:8501"))
        self.ui.webEngineView_rd_chatbot.setZoomFactor(0.75)
        print('loaded chatbot successfully into gui.')



class Worker_rd_chatbot(QRunnable):
    def __init__(self):
        super().__init__()
    @pyqtSlot()
    def run(self):
        # run streamlit RD chatbot
        print('Initialiizing Robo_dietitian')
        rd_chatbot = "python -m streamlit run robo_dietician.py --server.headless true" #
        os.system(rd_chatbot)
        print('Completed Robo_dietitian')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
