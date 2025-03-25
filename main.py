from datetime import time

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from aiohttp import worker

from nutrient_analysis import Ui_main_window
from GetJsonFromLlm import get_json_plaintext
from calculator_nutrient_intake import calculate_nutrient_intake, compare_nutrient_intake_and_needs

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
        plain_text = """Name: Jane Doe 
                        Date: 3/9/2025
                        Telephone: 214.920.9999
                        Physician: Sarah Connor
                        Physician phone: 888.777.6666
                        Height: 180 inches
                        Weight: 172 lbs
                        DOB: 09/09/1979
                        Age: 46 years
                        Sex: Female
                        Activity Level: Active
                        
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
        self.output_json_str = None # LLM output from user input

        # define user inputs and responses in gui
        self.ui.pushButton_calculate.clicked.connect(self.calculate_nutrition_needs)
        self.ui.tabWidget.tabBarClicked.connect(self.tab_results)

    def tab_results(self):

        # LLM parsed data
        print('self.output_json_str:  \n', self.output_json_str)

        # Wei code output available as csv in results directory

        # TODO Complete calculator_nutrient_needs.py
        # TODO calculator_nutrient_needs.py output goes into Wei's compare_nutrient_intake_needs() function.



    def calculate_nutrition_needs(self):
        print('STARTED: calculate push button')

        # Step 1: Intialize RD Chatbot.
        self.start_rd_chatbot_thread()

        # Step 2: Extract data from RD Inputs.
        self.start_llm_parser_thread()

        # Step 3: Run Nutrition Calculators
        # self.DRI_calculator()
        self.start_nutrient_intake_calculator_thread()

        print('COMPLETED: calculate push button')

    def DRI_calculator(self):
        print('STARTED: DRI_calculator')
        import json
        llm_output_dict = json.loads(self.output_json_str)
        print('llm_output_dict:', llm_output_dict)

        age = llm_output_dict['patient']['age']
        weight = llm_output_dict['patient']['weight']
        height = llm_output_dict['patient']['height']
        sex = llm_output_dict['patient']['sex'].lower()
        activity_level = llm_output_dict['patient']['activity level'].lower()

        # # feed in fake data
        # age = 30 # years
        # weight = 160 # lbs
        # height = 72 # inches
        # sex = 'male'
        # activity_level = 'Active'

        print('sex', sex)
        print('age:', age)
        print('weight:', weight)
        print('height:', height)
        print('activity_level:', activity_level)
        print('\n')

        import pandas as pd
        if sex == 'male':
            df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
        if sex == 'female':
            df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')

        print('Loaded', sex, 'dataset.')
        print(df)
        print('COMPLETED: DRI_calculator')

    def start_nutrient_intake_calculator_thread(self):
        worker = self.Worker_nutrient_intake_calculator()
        self.threadpool.start(worker)
        print('STARTED: nutrient intake calculator thread')

    def start_llm_parser_thread(self):
        worker = self.Worker_llm_parser(self, self.ui)
        self.threadpool.start(worker)
        print('STARTED: start_llm_parser_thread')

    def start_rd_chatbot_thread(self):
        worker = self.Worker_rd_chatbot()
        self.threadpool.start(worker)

        #allow streamlit (chatbot) thread to load before connecting to GUI
        import time
        time.sleep(0.5)

        print('Loading chatbot into gui.')
        from PyQt5.QtCore import QUrl
        self.ui.webEngineView_rd_chatbot.load(QUrl("http://localhost:8515"))
        self.ui.webEngineView_rd_chatbot.setZoomFactor(0.75)
        print('loaded chatbot successfully into gui.')

    class Worker_nutrient_intake_calculator(QRunnable):
        def __init__(self):
            super().__init__()
        @pyqtSlot()
        def run(self):
            print('STARTED: nutrient intake calculator')
            calculate_nutrient_intake("Intake.txt")
            print('COMPLETED: nutrient intake calculator')

    class Worker_llm_parser(QRunnable):
        def __init__(self, main, ui):
            super().__init__()
            self.main = main
            self.ui = ui
        @pyqtSlot()
        def run(self):
            print('STARTED: Worker_llm_parser')
            # pass output back to man gui.
            self.main.output_json_str = get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText())
            print('COMPLETED: Worker_llm_parser')

    class Worker_rd_chatbot(QRunnable):
        def __init__(self):
            super().__init__()
        @pyqtSlot()
        def run(self):

            # run streamlit RD chatbot
            print('STARTED: Robo_dietitian')
            # rd_chatbot = "python -m streamlit run robo_dietician.py --server.headless true"
            # os.system(rd_chatbot)

            import subprocess
            # cmd_string = "python -m streamlit run robo_dietician.py --theme.base='dark' --server.headless=true"
            # process = subprocess.run(cmd_string, shell=True)
            process = subprocess.run(
                ["python", "-m", "streamlit", "run", "robo_dietician.py", "--theme.base=dark", "--server.headless=true",
                 "--server.port=8515"],)

            print('COMPLETED: Robo_dietitian')

    # def closeEvent(self):
    #     print('Closing Robo_dietitian')
    #     self.threadpool.terminate()
    #     print('Closed Robo_dietitian')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
