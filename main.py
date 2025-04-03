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
from calculator_nutrient_intake import calculate_nutrient_intake, compare_nutrient_intake_and_needs, extract_nutrition
from calculator_nutrient_needs import preprocess_anthropometrics, calculate_patient_needs
from code_profiler import timeit

import sys
import os

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()
        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        self.threadpool = QThreadPool()
        self.max_threads = QThread.idealThreadCount()
        self.threadpool.setMaxThreadCount(self.max_threads)

        self.threadpool_extract_nutrients = QThreadPool()
        self.threadpool_extract_nutrients.setMaxThreadCount(self.max_threads)

        print(f'Running with max {self.max_threads} threads.')

        # set default inputs for testing code
        plain_text = """
        Name: Jane Doe 
        Date: 3/9/2025
        Telephone: 214.920.9999
        Physician: Sarah Connor
        Physician phone: 888.777.6666
        Height: 69 inches
        Weight: 150 lbs
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

    def calculate(self):

        # change color of button to indicate work in progress
        self.ui.pushButton_calculate.setText('Calculating...')
        self.ui.pushButton_calculate.setStyleSheet("background-color: green;")

        # clear previous results page
        self.ui.textBrowser_is_patient_nutrient_deficient.setText('')
        self.ui.tableWidget_macronutrients.clearContents()
        self.ui.tableWidget_micronutrients.clearContents()
        self.ui.tableWidget_essential_minerals.clearContents()

        # remove existing json ouput file if already exists
        file_path = 'results/llm_output_data.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file_path} deleted successfully.")

        # Step 1: Intialize RD Chatbot.
        self.start_rd_chatbot_thread()

        # Step 2: Extract data from RD Inputs AND Run Nutrition Calculators
        self.start_DRI_calculator_thread()
        # self.start_nutrient_intake_calculator_thread()

    @timeit
    def DRI_calculator(self):

        # run calculator based on input data (option 1 or option 2)
        if self.ui.file_path_selected_pdf.toPlainText() == '':
            # user chooses option 1. to input freetext data
            get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText()) # returns json file in results directory
        else:
            # user chooses option 2. to input pdf file
            get_json(self.ui.file_path_selected_pdf.toPlainText())

        # compute DRI, patient nutrition needs
        patient_anthropometrics = preprocess_anthropometrics()

        print('STARTED: DRI calculator')
        result_dri_df = calculate_patient_needs(patient_anthropometrics)
        print('COMPLETED: DRI calculator')

        # compute nutrition intake
        # AND create nutrition tables in results directory
        print('STARTED: Intake calculator')
        calculate_nutrient_intake(self) # creates all necessary excel tables for below.
        compare_nutrient_intake_and_needs(result_dri_df) # produces 'Nutrition_Intake_vs_Needs.csv'
        print('COMPLETED: Intake calculator')

        # read results table from 'Nutrition_Intake_vs_Needs.csv'
        results_df = pd.read_csv(r'results/Nutrition_Intake_vs_Needs.csv')

        results_df['Deviation'] = results_df['Deviation'].astype(float) # needed for identifying deficiencies and tagging

        # add units to table
        results_df['intake'] = results_df.apply(lambda row: f"{row['Intake_Amount']} {row['Intake_Unit']}", axis=1)
        results_df['need'] = results_df.apply(lambda row: f"{row['Need_Amount']} {row['Need_Unit']}", axis=1)

        df_macronutrients = results_df.iloc[0:10][['Nutrition', 'intake', 'need', 'Deviation']]
        df_vitamins = results_df.iloc[11:24][['Nutrition', 'intake', 'need', 'Deviation']]
        df_essential_minerals = results_df.iloc[24:39][['Nutrition', 'intake', 'need', 'Deviation']]
        df_calories = results_df.iloc[39][['Nutrition', 'intake', 'need', 'Deviation']]

        from PyQt5.QtGui import QColor

        # Set Table for Macronutrients in GUI
        for row in range(df_macronutrients.shape[0]):
            for col in range(df_macronutrients.shape[1]-1): # minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_macronutrients.iloc[row, col]))
                self.ui.tableWidget_macronutrients.setItem(row, col, item)
                if df_macronutrients['Deviation'].iloc[row] < 0:# change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))

        self.ui.tableWidget_macronutrients.update()

        # Set Table for Vitamins in GUI
        for row in range(df_vitamins.shape[0]):
            for col in range(df_vitamins.shape[1]-1):# minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_vitamins.iloc[row, col]))
                self.ui.tableWidget_micronutrients.setItem(row, col, item)
                if df_vitamins['Deviation'].iloc[row] < 0:# change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))
        self.ui.tableWidget_micronutrients.update()

        # Set Table for Essential Minerals in GUI
        for row in range(df_essential_minerals.shape[0]):
            for col in range(df_essential_minerals.shape[1]-1):# minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_essential_minerals.iloc[row, col]))
                self.ui.tableWidget_essential_minerals.setItem(row, col, item)
                if df_essential_minerals['Deviation'].iloc[row] < 0: # change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))
        self.ui.tableWidget_essential_minerals.update()

        # populate Summary of Results section
        import json
        with open('results/llm_output_data.json', 'r') as file:
            patient_dict = json.load(file)

        patient_name = patient_dict['patient']['name']

        # gather all data for summary block
        patient_caloric_intake = str(df_calories['intake'])
        patient_caloric_need = str(df_calories['need'])

        deficient_bool_mask = results_df['Deviation'] < 0
        deficient_rows = results_df[deficient_bool_mask]
        deficient_nutrients = deficient_rows['Nutrition'].tolist()

        summary_of_results_str = (f"Based on the 24 hr dietary recall, {patient_name} consumed {patient_caloric_intake} "
                                  f"of the recommended {patient_caloric_need}. {patient_name} is deficient in "
                                  f"{deficient_nutrients}.")

        # send a signal back to update GUI summary page
        self.summary_string = summary_of_results_str

        # Enable results tab
        self.ui.tabWidget.setTabEnabled(1, True)
        self.ui.tabWidget.setCurrentIndex(1) # automatically show to results tab

        print('COMPLETED: Analysis')

    class WorkerSignals(QObject):
        finished = pyqtSignal(str)

    def update_result_summary_page(self, result):

        self.ui.textBrowser_is_patient_nutrient_deficient.setText(result)
        self.ui.textBrowser_is_patient_nutrient_deficient.update()

        # change color of push button to indicate work is complete
        self.ui.pushButton_calculate.setText('Calculate')
        self.ui.pushButton_calculate.setStyleSheet("background-color: gray;")

    def start_DRI_calculator_thread(self):
        worker = self.Worker_DRI_calculator(self, self.ui)
        self.threadpool.start(worker)

        # connect finished singal to outside function
        worker.signals.finished.connect(self.update_result_summary_page)


    def start_rd_chatbot_thread(self):
        worker = self.Worker_rd_chatbot()
        self.threadpool.start(worker)

        #allow streamlit (chatbot) thread to load before connecting to GUI
        import time
        time.sleep(1)

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
            self.signals = self.main.WorkerSignals()
        @pyqtSlot()
        def run(self):

            self.main.DRI_calculator()

            # send signal to populate summary page
            self.signals.finished.emit(self.main.summary_string)

    class Worker_rd_chatbot(QRunnable):
        def __init__(self):
            super().__init__()
        @pyqtSlot()
        def run(self):
            # run streamlit RD chatbot
            print('STARTED: Robo_dietitian')
            import subprocess
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
