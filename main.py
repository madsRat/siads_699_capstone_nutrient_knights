from datetime import time
import pandas as pd

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from aiohttp import worker

from nutrient_analysis import Ui_main_window
from GetJsonFromLlm import get_json_plaintext, get_json
from calculator_nutrient_intake import calculate_nutrient_intake, compare_nutrient_intake_and_needs
from calculator_nutrient_needs import preprocess_anthropometrics, calculate_patient_needs

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
        self.ui.pushButton_calculate.clicked.connect(self.calculate)
        self.ui.tabWidget.tabBarClicked.connect(self.tab_results)
        self.ui.browse_pdf_file.clicked.connect(self.load_pdf_file)

    def load_pdf_file(self):
        print('Loading pdf file.')
        # clear previous filepath
        self.ui.file_path_selected_pdf.setText('file path')

        #load file dialog
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select PDF file")
        if file_path != (None or ''):
            self.ui.file_path_selected_pdf.setText(file_path)
            # clear plain text input
            self.ui.plainTextEdit_dietary_recall.setPlainText("")
            self.ui.plainTextEdit_dietary_recall.setDisabled(True)
        else:
            # cover edge case so textbox is available if user changes mind about inputs
            self.ui.plainTextEdit_dietary_recall.setDisabled(False)


    def tab_results(self):

        # LLM parsed data
        # print('self.output_json_str:  \n', self.output_json_str)
        print('Tab changed.')

    def calculate(self):

        # remove existing json ouput file if already exists
        file_path = 'results/llm_output_data.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file_path} deleted successfully.")
        else:
            print('STARTED: calculate push button')

        # Step 1: Intialize RD Chatbot.
        self.start_rd_chatbot_thread()

        # Step 2: Extract data from RD Inputs AND Run Nutrition Calculators
        self.start_DRI_calculator_thread()
        # self.start_nutrient_intake_calculator_thread()

        print('COMPLETED: calculate push button')

    def DRI_calculator(self):

        # run calculator based on input data (option 1 or option 2)
        if self.ui.file_path_selected_pdf.toPlainText() == '':
            # user chooses option 1. to input freetext data
            print('filepath:\n', self.ui.file_path_selected_pdf.toPlainText())
            get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText()) # returns json file in results directory
        else:
            # user chooses option 2. to input pdf file
            print('filepath:\n', self.ui.file_path_selected_pdf.toPlainText())
            get_json(self.ui.file_path_selected_pdf.toPlainText())

        # compute DRI, patient nutrition needs
        patient_anthropometrics = preprocess_anthropometrics()
        result_dri_df = calculate_patient_needs(patient_anthropometrics)

        # compute nutrition intake
        # AND create nutrition tables in results directory
        calculate_nutrient_intake()
        compare_nutrient_intake_and_needs(result_dri_df) # produces 'Nutrition_Intake_vs_Needs.csv'
        print('DRI and intake calculations completed')

        # read results table from 'Nutrition_Intake_vs_Needs.csv'
        results_df = pd.read_csv(r'results/Nutrition_Intake_vs_Needs.csv')

        df_macronutrients = results_df.iloc[0:10][['Nutrition', 'Intake_Amount', 'Need_Amount']]
        df_vitamins = results_df.iloc[11:24][['Nutrition', 'Intake_Amount', 'Need_Amount']]
        df_essential_minerals = results_df.iloc[24:39][['Nutrition', 'Intake_Amount', 'Need_Amount']]

        # Set Table for Macronutrients in GUI
        for row in range(df_macronutrients.shape[0]):
            for col in range(df_macronutrients.shape[1]):
                item = QTableWidgetItem(str(df_macronutrients.iloc[row, col]))
                self.ui.tableWidget_macronutrients.setItem(row, col, item)
        self.ui.tableWidget_macronutrients.update()

        # Set Table for Vitamins in GUI
        for row in range(df_vitamins.shape[0]):
            for col in range(df_vitamins.shape[1]):
                item = QTableWidgetItem(str(df_vitamins.iloc[row, col]))
                self.ui.tableWidget_micronutrients.setItem(row, col, item)
        self.ui.tableWidget_micronutrients.update()

        # Set Table for Essential Minerals in GUI
        for row in range(df_essential_minerals.shape[0]):
            for col in range(df_essential_minerals.shape[1]):
                item = QTableWidgetItem(str(df_essential_minerals.iloc[row, col]))
                self.ui.tableWidget_essential_minerals.setItem(row, col, item)
        self.ui.tableWidget_essential_minerals.update()

    def start_DRI_calculator_thread(self):
        worker = self.Worker_DRI_calculator(self, self.ui)
        self.threadpool.start(worker)
        print('DRI calculator thread started')

    # def start_nutrient_intake_calculator_thread(self):
    #     worker = self.Worker_nutrient_intake_calculator()
    #     self.threadpool.start(worker)
    #     print('STARTED: nutrient intake calculator thread')

    # def start_llm_parser_thread(self):
    #     worker = self.Worker_llm_parser(self, self.ui)
    #     self.threadpool.start(worker)
    #     print('STARTED: start_llm_parser_thread')

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

    class Worker_DRI_calculator(QRunnable):
        def __init__(self, main, ui):
            super().__init__()
            self.main = main
            self.ui = ui
        @pyqtSlot()
        def run(self):
            print('STARTED: DRI calculator')
            self.main.DRI_calculator()

    # class Worker_nutrient_intake_calculator(QRunnable):
    #     def __init__(self):
    #         super().__init__()
    #     @pyqtSlot()
    #     def run(self):
    #         print('STARTED: nutrient intake calculator')
    #         calculate_nutrient_intake("Intake.txt")
    #         print('COMPLETED: nutrient intake calculator')

    # class Worker_llm_parser(QRunnable):
    #     def __init__(self, main, ui):
    #         super().__init__()
    #         self.main = main
    #         self.ui = ui
    #     @pyqtSlot()
    #     def run(self):
    #         print('STARTED: Worker_llm_parser')
    #         # pass output back to man gui.
    #         self.main.output_json_str = get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText())
    #         print('COMPLETED: Worker_llm_parser')

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
