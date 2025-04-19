import sys
import os
import json
import time
import subprocess
import requests
import pandas as pd

from openai import OpenAI
from openai import AuthenticationError, OpenAIError

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable, QUrl
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from nutrient_analysis import Ui_main_window
from GetJsonFromLlm import get_json_plaintext, get_json
from calculator_nutrient_intake import calculate_nutrient_intake, compare_nutrient_intake_and_needs, extract_nutrition
from calculator_nutrient_needs import preprocess_anthropometrics, calculate_patient_needs
# from code_profiler import timeit

class ApplicationWindow(QtWidgets.QMainWindow):

    """
    Main application window for RoboDietitian.
    RoboDietitian is an application that can calculate nutrient deficiencies for healthy individuals over the age of 1.
    RoboDietitian is not intended for personal health or medical applications.
    RoboDietitian should only be used in academic setting; Created for University of Michigan, SIADS 699 Capstone class.
    Developed by Daniel Torrecampo, Ayan Banerjee, Richard Chaulker, and Wei Liu.
    """
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        # import user interface class
        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        # enable multithreading to allow multiple process to occur at one time.
        self.threadpool = QThreadPool()
        self.max_threads = QThread.idealThreadCount()
        self.threadpool.setMaxThreadCount(self.max_threads)

        # create a separate thread pool for querying USDA food database. Ensures threads are independent and safe.
        self.threadpool_extract_nutrients = QThreadPool()
        self.threadpool_extract_nutrients.setMaxThreadCount(self.max_threads)

        # provide example 24-hour diet recall for user
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
                8 oz	Water
                
                """

        # pre-populate text input to provide user with an example 24-hr diet recall
        self.ui.plainTextEdit_dietary_recall.setPlainText(plain_text)
        self.output_json_str = None # LLM output from user input

        # define user inputs and responses in gui
        self.ui.pushButton_calculate.clicked.connect(self.calculate)
        self.ui.browse_pdf_file.clicked.connect(self.load_pdf_file)

        # set chatbot port
        self.streamlit_port= 8515
        self.summary_string = ''
        self.streamlit_worker = None

        # ask users to present API keys
        self.openAI_key = ''
        self.fda_key = ''

        # Make sure API keys are valid before proceeding to the program.
        while (self.openAI_key=='' or self.fda_key==''):

            self.load_API_keys_popup()
            self.check_API_keys()

    def check_API_keys(self):

        """
        Checks if API keys for OpenAI and USDA Food datasets are valid.
        If keys are valid, then they are saved to the main gui.
        """

        def is_api_key_valid(api_key):

            # check OpenAI API key
            client = OpenAI(api_key=api_key)
            try:
                client.models.list()  # Uses new SDK method
                return True
            except AuthenticationError:
                return False
            except OpenAIError as e:
                print("Other OpenAI error:", str(e))
                return False

        # check USDA API key
        def is_fdc_api_key_valid(api_key):

            url = "https://api.nal.usda.gov/fdc/v1/foods/search"
            params = {
                "query": "apple",
                "api_key": api_key
            }

            try:
                # send quick query to see if api key is valid
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    print("❌ Unauthorized: Invalid API key.")
                    return False
                else:
                    print(f"⚠️ Unexpected status code: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"Error during request: {e}")
                return False

        # save OpenAI API key if valid
        if is_api_key_valid(self.openAI_key):
            print("✅ OpenAI API key is valid!")
            os.environ["OPENAI_API_KEY"] = self.openAI_key
        else:
            error_msg = "❌ Invalid OpenAI API key. Please try again."
            print(error_msg)
            self.openAI_key = ''
            self.show_popup(error_msg)

        # save USDA FoodData Central API key if valid
        if is_fdc_api_key_valid(self.fda_key):
            print("✅ USDA FoodData Central API key is valid!")
            # self.fda_key already referenced in calculator_nutrient_table.py
        else:
            error_msg = "❌ Invalid USDA FoodData Central API key. Please try again."
            print(error_msg)
            self.fda_key = ''
            self.show_popup(error_msg)

    def load_API_keys_popup(self):

        """
        A Pop-up window upon program start that requires users to enter API keys.
        :return: self.openAI_key, self.fda_key
        """

        part_1 = "Welcome! Please enter your API keys below to use RoboDietitian: \n\n"
        part_2 = "Don't have API Keys? No problem, you can create them here: \n\n"
        part_3 = "https://openai.com/api/\n"
        part_4 = "https://fdc.nal.usda.gov/api-guide\n"
        message = part_1 + part_2 + part_3 + part_4

        dialog = QDialog()
        dialog.setWindowTitle("RoboDietitian")

        layout = QVBoxLayout()

        # Message Header
        message_label = QLabel(message)
        layout.addWidget(message_label)

        # OpenAI header
        label1 = QLabel("OpenAI")
        self.openAI_API_key = QLineEdit()
        self.openAI_API_key.setText(self.openAI_key)
        self.openAI_API_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(label1)
        layout.addWidget(self.openAI_API_key)

        # USDA Food Dataset header
        label2 = QLabel("USDA FoodData Central")
        self.fda_API_key = QLineEdit()
        self.fda_API_key.setText(self.fda_key)
        self.fda_API_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(label2)
        layout.addWidget(self.fda_API_key)

        # OK Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            # save api keys to main gui
            self.openAI_key = self.openAI_API_key.text()
            self.fda_key = self.fda_API_key.text()

    def load_pdf_file(self):

        """
        loads 24-hour diet recall (pdf format)
        :return: file path of pdf file
        """

        # clear previous filepath
        self.ui.file_path_selected_pdf.setText('')

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

    def show_popup(self, message):

        """
        Generic popup window to display error messages
        :param message:
        :return: popup window
        """

        msg = QMessageBox()
        msg.setWindowTitle("Pop-up Message")
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)  # Optional: Set icon
        msg.setStandardButtons(QMessageBox.Ok)  # Optional: Set buttons

        ret = msg.exec_()

        if ret == QMessageBox.Ok:
            print("Acknowledged.")
        elif ret == QMessageBox.Cancel:
            print("Cancelled.")

    def calculate(self):

        """
        Starts chain of events prior to calculating nutrient intake and patient recommended intake.
        1. modifies GUI interface
        2. clears old data and threads
        3. starts multi-threaded calculation.
        """

        # check if user put in inputs.
        if (self.ui.plainTextEdit_dietary_recall.toPlainText() == "" and
                self.ui.file_path_selected_pdf.toPlainText() == ""):
            self.show_popup("Please input Patient's 24 hr Diet Recall.")
            return None

        # change color of button to indicate work in progress
        self.ui.pushButton_calculate.setEnabled(False)  # prevent user from double clicking
        self.ui.pushButton_calculate.setText('Calculating...')
        self.ui.pushButton_calculate.setStyleSheet("background-color: green;")

        # keep user in analysis tab so tables can populate correctly
        self.ui.tabWidget.setTabEnabled(1, False)
        self.ui.tabWidget.setCurrentIndex(0) # automatically show to analysis tab

        # clear previous results page
        self.ui.textBrowser_is_patient_nutrient_deficient.setText('')
        self.ui.tableWidget_macronutrients.clearContents()
        self.ui.tableWidget_micronutrients.clearContents()
        self.ui.tableWidget_essential_minerals.clearContents()

        remove_files = ['results/llm_output_data.json',
                     'results/food_nutrition_table.csv',
                     'results/food_summary.csv',
                     'results/nutrition_table.csv',
                    'results/nutrition_total_intake.csv',
                    'results/Nutrition_Intake_vs_Needs.csv'
                     ]

        # remove existing json ouput file if already exists
        for file in remove_files:
            if os.path.exists(file):
                os.remove(file)

        # remove streamlit chatbot threads from previous runs
        if self.streamlit_worker != None:
            self.streamlit_worker.stop()

        # Extract data from RD Inputs AND Run Nutrition Calculators
        self.start_DRI_calculator_thread()

    # @timeit
    def DRI_calculator(self, signals_error):

        """
        1. Extracts patient data and diet recall from user input.
        2. Calculates nutrient intake and patient recommended intake.
        3. Modifies GUI interface to present data and results.
        :param signals_error:
        :return: excel files in results directory
        """

        try:
            # run calculator based on input data (option 1 or option 2)
            if self.ui.file_path_selected_pdf.toPlainText() == '':
                # user chooses option 1. to input freetext data
                get_json_plaintext(self.ui.plainTextEdit_dietary_recall.toPlainText()) # returns json in results dir
            else:
                # user chooses option 2. to input pdf file
                get_json(self.ui.file_path_selected_pdf.toPlainText())
        except Exception as e:
            error_str = 'No internet connection found: Please ensure you have internet connection for API calls.'
            print(error_str)
            signals_error.finished.emit(error_str)
            return None

        try:
            # compute DRI, patient nutrition needs
            patient_anthropometrics = preprocess_anthropometrics()
        except Exception as e:
            error_msg = 'Error: Invalid 24-hour diet recall. Please retry.'
            signals_error.finished.emit(error_msg)
            print(error_msg)
            return None

        try:
            # calculate patient nutrient needs
            result_dri_df = calculate_patient_needs(patient_anthropometrics)
        except Exception as e:
            print(e)
            return None

        # compute nutrition intake and create nutrition tables in results directory
        calculate_nutrient_intake(self) # creates all necessary excel tables for below.
        compare_nutrient_intake_and_needs(result_dri_df) # produces 'Nutrition_Intake_vs_Needs.csv'

        # read results table from 'Nutrition_Intake_vs_Needs.csv'
        results_df = pd.read_csv(r'results/Nutrition_Intake_vs_Needs.csv')
        results_df = results_df.fillna(0)

        results_df['Deviation'] = results_df['Deviation'].astype(float) # needed to identify deficiencies and tagging

        # add units to table
        results_df['intake'] = results_df.apply(lambda row: f"{row['Intake_Amount']} {row['Intake_Unit']}", axis=1)
        results_df['need'] = results_df.apply(lambda row: f"{row['Need_Amount']} {row['Need_Unit']}", axis=1)

        # organize results to put into GUI tables
        df_macronutrients = results_df.iloc[0:10][['Nutrition', 'intake', 'need', 'Deviation']]
        df_vitamins = results_df.iloc[10:24][['Nutrition', 'intake', 'need', 'Deviation']]
        df_essential_minerals = results_df.iloc[24:39][['Nutrition', 'intake', 'need', 'Deviation']]
        df_calories = results_df.iloc[39][['Nutrition', 'intake', 'need', 'Deviation']]

        from PyQt5.QtGui import QColor

        # Set Table for Macronutrients in GUI
        for row in range(df_macronutrients.shape[0]):
            for col in range(df_macronutrients.shape[1]-1): # minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_macronutrients.iloc[row, col]))
                self.ui.tableWidget_macronutrients.setItem(row, col, item)
                if df_macronutrients['Deviation'].iloc[row] > 0:# change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))

        self.ui.tableWidget_macronutrients.update()

        # Set Table for Vitamins in GUI
        for row in range(df_vitamins.shape[0]):
            for col in range(df_vitamins.shape[1]-1):# minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_vitamins.iloc[row, col]))
                self.ui.tableWidget_micronutrients.setItem(row, col, item)
                if df_vitamins['Deviation'].iloc[row] > 0:# change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))

        self.ui.tableWidget_micronutrients.update()

        # Set Table for Essential Minerals in GUI
        for row in range(df_essential_minerals.shape[0]):
            for col in range(df_essential_minerals.shape[1]-1):# minus -1 to ignore deviation col, but use to color row
                item = QTableWidgetItem(str(df_essential_minerals.iloc[row, col]))
                self.ui.tableWidget_essential_minerals.setItem(row, col, item)
                if df_essential_minerals['Deviation'].iloc[row] > 0: # change color to red if nutrient deficient
                    item.setBackground(QColor(139, 0, 0))

        self.ui.tableWidget_essential_minerals.update()

        # populate Summary of Results section
        with open('results/llm_output_data.json', 'r') as file:
            patient_dict = json.load(file)

        patient_name = patient_dict['patient']['name']

        # gather all data for summary block
        patient_caloric_intake = str(df_calories['intake'])
        patient_caloric_need = str(df_calories['need'])

        # find deficient nutrients and feed into patient summary
        deficient_bool_mask = results_df['Deviation'] > 0
        deficient_rows = results_df[deficient_bool_mask]
        deficient_nutrients = deficient_rows['Nutrition'].tolist()

        summary_of_results_str = (f"Based on the 24 hr dietary recall, {patient_name} consumed {patient_caloric_intake}"
                                  f"of the recommended {patient_caloric_need}. {patient_name} is deficient in "
                                  f"{deficient_nutrients}.")

        # send a signal back to update GUI summary page
        self.summary_string = summary_of_results_str

        # Enable results tab
        self.ui.tabWidget.setTabEnabled(1, True)
        self.ui.tabWidget.setCurrentIndex(1) # automatically show to results tab
        self.ui.pushButton_calculate.setEnabled(True) # re enable calculate push button

    class WorkerSignals(QObject):
        """"
        pyqt5 signal that allows GUI to communicate when task is completed.
        """
        finished = pyqtSignal(str)

    def update_result_summary_page(self, result):

        # update text box with results
        self.ui.textBrowser_is_patient_nutrient_deficient.setText(result)
        self.ui.textBrowser_is_patient_nutrient_deficient.update()

        # change color of push button to indicate work is complete
        self.ui.pushButton_calculate.setText('Calculate')
        self.ui.pushButton_calculate.setStyleSheet("background-color: gray;")

        # start RD chatbot after calculations are complete.
        self.start_rd_chatbot_thread()

    def show_internet_connection_error(self, error):
        # show pop up in internet connection not present. internet required for USDA and OpenAI endpoints.
        self.show_popup(error)

        # Enable results tab
        self.ui.tabWidget.setTabEnabled(1, False)
        self.ui.pushButton_calculate.setEnabled(True) # re enable calculate push button

    def start_DRI_calculator_thread(self):

        # create worker thread for DRI and intake calculators
        worker = self.Worker_DRI_calculator(self, self.ui)
        self.threadpool.start(worker)

        # connect finished signal to outside function
        worker.signals.finished.connect(self.update_result_summary_page)
        worker.signals_error.finished.connect(self.show_internet_connection_error)

    def start_rd_chatbot_thread(self):

        # create worker thread for RD chatbot
        self.streamlit_worker = self.Worker_rd_chatbot(self)
        self.threadpool.start(self.streamlit_worker)

        time.sleep(1) # provide time for gui to start up. will not start correctly without this.

        # connect GUI to RD Chatbot instance (streamlit)
        streamlit_url = "http://localhost:" + str(self.streamlit_port)
        self.ui.webEngineView_rd_chatbot.load(QUrl(streamlit_url))
        self.ui.webEngineView_rd_chatbot.setZoomFactor(0.75)

    class Worker_DRI_calculator(QRunnable):
        def __init__(self, main, ui):
            super().__init__()
            self.main = main
            self.ui = ui
            self.signals = self.main.WorkerSignals()
            self.signals_error = self.main.WorkerSignals()
        @pyqtSlot()
        def run(self):

            try:
                self.main.DRI_calculator(self.signals_error)
            except Exception as e:
                print(e)

            # send signal to populate summary page
            self.signals.finished.emit(self.main.summary_string)

    class Worker_rd_chatbot(QRunnable):
        def __init__(self, main):
            super().__init__()
            self.main = main
            self.signals = self.main.WorkerSignals()
            self.process = None
            self._is_interrupted = False
        @pyqtSlot()
        def run(self):

            # run streamlit RD chatbot
            user_input = self.main.summary_string
            server_input = "--server.port=" + str(self.main.streamlit_port)

            try:
                self.process = subprocess.Popen(["python3", "-m", "streamlit", "run", "robo_dietician.py",
                                                 "--theme.base=dark", "--server.headless=true", server_input, "--" ,
                                                 user_input])
            except Exception as e:
                print("Error running subprocesses", e)

        def stop(self):

            # stop RD chatbot running in subprocess thread
            self._is_interrupted = True
            if self.process != None:
                self.process.terminate()

    def closeEvent(self, event):

        # close RD chatbot
        if self.streamlit_worker != None:
            self.streamlit_worker.stop()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    application = ApplicationWindow()
    application.show()
    sys.exit(app.exec_())
