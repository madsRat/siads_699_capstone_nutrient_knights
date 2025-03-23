from datetime import time

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from aiohttp import worker

from nutrient_analysis import Ui_main_window
from GetJsonFromLlm import get_json_plaintext
import sys
import os

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_main_window()
        self.ui.setupUi(self)
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(4)

        # set default inputs for testing code
        plain_text = """Name: Jane Doe Date: 3/9/2025
                        Telephone: 214.920.9999
                        Physician: Sarah Connor
                        Physician phone: 888.777.6666
                        Height: 180 inches
                        Weight: 172 lbs
                        DOB: 09/09/1979
                        Age: 46 years
                        24-hr Diet Recall
                        Time	Place	Amount	Food Description	Notes
                        8 am	Kitchen	¾ cup	Raisin Bran
                                ½ cup	Apple juice
                                1 medium	Fresh peach
                        12 pm	Dining table	½ cup	Ground beef
                                1 cup	Mushroom stew
                                ½ cup	Rice
                                ¼ cup	Green beans
                                8 oz	Water
                        4 pm	Kitchen	½ cup	Pretzels
                                1 oz	Chocolate
                        7 pm	Dining table	1 cup	Spaghetti
                                ½ cup	Ground beef
                                8 oz	Water"""
        self.ui.plainTextEdit_dietary_recall.setPlainText(plain_text)

        # define user inputs and responses in gui
        self.ui.pushButton_calculate.clicked.connect(self.calculate_nutrition_needs)

    def calculate_nutrition_needs(self):
        print('STARTED: calculate_nutrition_needs')
        json_str = get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText())
        self.start_rd_chatbot_thread()
        print('COMPLETED: calculate_nutrition_needs')

    def start_rd_chatbot_thread(self):
        worker = self.Worker_rd_chatbot()
        self.threadpool.start(worker)
        print('started thread.')

        # allow streamlit (chatbot) thread to load before connecting to GUI
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
            # self.running = running
        @pyqtSlot()
        def run(self):

            # run streamlit RD chatbot
            print('Initialiizing Robo_dietitian')
            # rd_chatbot = "python -m streamlit run robo_dietician.py --server.headless true"
            # os.system(rd_chatbot)

            import subprocess
            process = subprocess.run(["python", "-m", "streamlit", "run", "robo_dietician.py", "--server.headless", "true"])

            # # close chatbot when GUI closed
            # while self.running:
            #     import time
            #     time.sleep(0.25)


            print('Completed Robo_dietitian')

    # def closeEvent(self):
    #     print('Closing Robo_dietitian')
    #     self.threadpool.terminate()
    #     print('Closed Robo_dietitian')


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
