import qtpy
import re

import logging
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QSplitter, QFrame, QTabWidget, QGroupBox, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QLayout, QSpacerItem, QSizePolicy, QSlider
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from core.mcm import MCM
import numpy as np
from ui.conditional import ConditionalProbabilitiesDialog, CostVariablesDialog
from ui.dialogs import NotificationDialog

logger = logging.getLogger(__name__)


def get_width(text):
    width = QLabel("").fontMetrics().boundingRect(text).width()
    return width


class EnableableWidget(QWidget):
    def __init__(self):
        super().__init__()

    def set_enabled(self, enabled):
        """
        Enable of disable widget elements
        """
        # enable or disable elements in the layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.widget():
                item.widget().setEnabled(enabled)


class HLayout(QHBoxLayout):
    """
    Groups some items in a QHBoxLayout
    """

    def __init__(self, items, stretch=None):
        super(QHBoxLayout, self).__init__()
        # Add widgets
        if stretch is None:
            stretch = [0] * len(items)
        else:
            if len(items) != len(stretch):
                raise ValueError("Number of given items is not equal to number of given stretchfactors")

        for item, stretchfactor in zip(items, stretch):
            if isinstance(item, str) and item.lower() == "stretch":
                self.addStretch(stretchfactor)
            if isinstance(item, QLayout):
                self.addLayout(item, stretchfactor)
            elif isinstance(item, QWidget):
                self.addWidget(item, stretchfactor)
            else:
                TypeError("Item type not understood.")


class VLayout(QVBoxLayout):
    """
    Groups some items in a QVBoxLayout
    """

    def __init__(self, items, stretch=None):
        super(QVBoxLayout, self).__init__()
        # Add widgets
        if stretch is None:
            stretch = [0] * len(items)
        else:
            if len(items) != len(stretch):
                raise ValueError("Number of given items is not equal to number of given stretchfactors")

        for item, stretchfactor in zip(items, stretch):
            if isinstance(item, str) and item.lower() == "stretch":
                self.addStretch(stretchfactor)
            if isinstance(item, QLayout):
                self.addLayout(item, stretchfactor)
            elif isinstance(item, QWidget):
                self.addWidget(item, stretchfactor)
            else:
                TypeError("Item type not understood.")


class LogoSplitter(QSplitter):
    """
    Splitter that shows an arrow icon when it is collapsd to one side.
    """

    def __init__(self, topwidget, bottomwidget, toptext="", bottomtext=""):
        """Constructs the widget

        Parameters
        ----------
        topwidget : QWidget
            Widget to display on top
        bottomwidget : QWidget
            Widget to display on bottom
        toptext : str, optional
            Text to display when top is collapsed, by default ''
        bottomtext : str, optional
            Text to display when bottom is collapsed, by default ''
        """
        # Create child class
        QSplitter.__init__(self, Qt.Vertical)

        self.addWidget(topwidget)
        self.addWidget(bottomwidget)

        self.toptext = toptext
        self.bottomtext = bottomtext

        self.splitterMoved.connect(self.on_moved)

        handle_layout = QVBoxLayout()
        handle_layout.setContentsMargins(0, 0, 0, 0)
        self.setHandleWidth(5)

        self.button = QToolButton()
        self.button.setStyleSheet("background-color: rgba(255, 255, 255, 0)")

        uplogo = self.style().standardIcon(QStyle.SP_TitleBarShadeButton)
        downlogo = self.style().standardIcon(QStyle.SP_TitleBarUnshadeButton)
        self.upicon = QIcon(uplogo)
        self.downicon = QIcon(downlogo)
        self.noicon = QIcon()
        self.icon = self.noicon

        self.button.setIcon(self.icon)
        self.button.clicked.connect(self.handleSplitterButton)
        self.button.setCursor(QCursor(Qt.PointingHandCursor))

        self.label = QLabel("")

        handle_layout.addLayout(HLayout([self.button, self.label]))
        handle_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Maximum, QSizePolicy.Expanding)
        )

        handle = self.handle(1)
        handle.setLayout(handle_layout)

    def setSizes(self, *args, **kwargs):
        """
        Override the default method to also check the sizes and change label and logo accordingly.
        """
        super().setSizes(*args, **kwargs)
        self.on_moved()

    def handleSplitterButton(self):
        """
        When button is clicked
        """
        # Open and set right icon
        self.setSizes([1, 1])
        self.on_moved()

    def on_moved(self):
        """
        Method to call when splitter is moved. This method
        updates the icon, but it can be extended to update for example a canvs
        """

        sizes = self.sizes()

        # If one is collapsed
        if not sizes[0]:
            icon = self.downicon
            self.label.setText(self.toptext)
            self.setHandleWidth(22 if self.toptext else 5)

        elif not sizes[1]:
            icon = self.upicon
            self.label.setText(self.bottomtext)
            self.setHandleWidth(22 if self.bottomtext else 5)
        # If both are open
        else:
            icon = self.noicon
            self.label.setText("")
            self.setHandleWidth(5)

        if self.icon is not icon:
            self.icon = icon
            self.button.setIcon(self.icon)


class ComboboxInputLine(QWidget):
    """
    A widget that combines a label and a combo box with several items
    """

    def __init__(self, label, labelwidth=None, items=None, default=None, spacer=True):
        """
        LineEdit class extended with a label in front (description)
        and behind (unit).

        Parameters
        ----------
        label : str
            label for the line edit
        labelwidth : int
            width (points) of label
        items : list
            List with items to add to the combobox
        default : str, optional
            Default item, by default None
        spacer : bool, optional
            Whether or not to add a spacer on the right, by default True
        """

        super(QWidget, self).__init__()

        self.label = label
        self.labelwidth = labelwidth
        self.items = items
        self.default = default

        self.init_ui(spacer)

        # Add default value
        if self.default is not None:
            if not self.default in self.items:
                raise ValueError("{} not in {}".format(self.default, ", ".join(self.items)))
            else:
                self.combobox.setCurrentText(self.default)

    def init_ui(self, spacer):
        """
        Build ui layout
        """
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(5, 0, 5, 0)

        # Add label
        self.Label = QLabel()
        self.Label.setText(self.label)
        if self.labelwidth:
            self.Label.setFixedWidth(self.labelwidth)
        self.layout().addWidget(self.Label)

        # Add line edit
        self.combobox = QComboBox()
        self.combobox.setMaximumWidth(200)
        self.combobox.addItems(self.items)
        self.layout().addWidget(self.combobox)

        # Add spacer to the right
        if spacer:
            self.layout().addItem(
                QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Maximum)
            )

    def get_value(self):
        """
        Get value from combobox
        """
        return self.combobox.currentText()

    def set_value(self, value):
        """
        Set value to combobox
        """
        if not isinstance(value, str):
            value = str(value)
        self.combobox.setCurrentText(value)


class ExtendedLineEdit(QWidget):
    def __init__(self, label, labelwidth=None, browsebutton=False):
        """
        Extended LineEdit class. A browse button can be added, as well as an
        infomessage.

        Parameters
        ----------
        label : str
            label for the line edit
        labelwidth : int
            width (points) of label
        browsebutton : boolean
            Whether to add ad browse button
        info : str
            infomessage to display (not implemented)
        """

        super(QWidget, self).__init__()
        self.label = label
        self.labelwidth = labelwidth
        self.browsebutton = browsebutton

        self.init_ui()

    def init_ui(self):
        """
        Build ui element
        """

        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(5, 0, 5, 0)

        self.Label = QLabel()
        self.Label.setText(self.label)
        if self.labelwidth is not None:
            self.Label.setFixedWidth(self.labelwidth)
        self.layout().addWidget(self.Label)

        self.LineEdit = QLineEdit()
        self.LineEdit.setMinimumWidth(200)
        # self.LineEdit.setReadOnly(True)
        self.layout().addWidget(self.LineEdit)

        if self.browsebutton:
            self.BrowseButton = self.browsebutton
            self.BrowseButton.setFixedWidth(25)
            self.layout().addWidget(self.BrowseButton)

    def get_value(self):
        """
        Get value from line edit
        """
        return self.LineEdit.text()

    def set_value(self, value):
        """
        Set value to line edit
        """
        if not isinstance(value, str):
            value = str(value)
        self.LineEdit.setText(value)


class CheckBoxInput(QWidget):
    """
    A widget that combines a label and a checkbox
    """

    def __init__(self, label, labelwidth=None, spacer=True, default=False):
        """
        LineEdit class extended with a label in front (description)
        and behind (unit).

        Parameters
        ----------
        label : str
            label for the line edit
        labelwidth : int
            width (points) of label
        items : list
            List with items to add to the combobox
        """
        super(QWidget, self).__init__()

        self.label = label
        self.labelwidth = labelwidth
        self.init_ui(spacer, default)

    def init_ui(self, spacer, default):
        """
        Build ui layout
        """
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(5, 0, 5, 0)

        # Add label
        self.Label = QLabel()
        self.Label.setText(self.label)
        if self.labelwidth:
            self.Label.setFixedWidth(self.labelwidth)
        self.layout().addWidget(self.Label)

        # Add line edit
        self.checkbox = QCheckBox()
        self.set_value(default)
        self.layout().addWidget(self.checkbox)

        # Add spacer to the right
        if spacer:
            self.layout().addItem(
                QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Maximum)
            )

    def get_value(self):
        """
        Get value from combobox
        """
        return self.checkbox.isChecked()

    def set_value(self, value):
        """
        Set value to combobox
        """
        return self.checkbox.setChecked(value)


class HLine(QFrame):
    """
    Adds a horizontal line
    """

    def __init__(self):
        """
        Constructs the line
        """
        super(QFrame, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class ParameterInputLine(QWidget):
    """
    A widget that combines a label, input field and unit label
    """

    def __init__(self, label, labelwidth=None, unitlabel=None, validator=None, default=None):
        """
        LineEdit class extended with a label in front (description)
        and behind (unit).

        Parameters
        ----------
        label : str
            label for the line edit
        labelwidth : int
            width (points) of label
        unitlabel : str
            text to add behind line edit
        info : str
            infomessage to display (not implemented)
        """

        super(QWidget, self).__init__()

        self.label = label
        self.labelwidth = labelwidth
        self.unitlabel = unitlabel
        self.validator = validator
        self.default_value = default
        if default is not None:
            if not isinstance(default, str):
                self.default_value = str(default)

        self.init_ui()

    def init_ui(self):
        """
        Build ui layout
        """
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(5, 0, 5, 0)

        # Add label
        self.Label = QLabel()
        self.Label.setText(self.label)
        if self.labelwidth:
            self.Label.setFixedWidth(self.labelwidth)
        self.layout().addWidget(self.Label)

        # Add line edit
        self.LineEdit = QLineEdit(self.default_value)
        self.LineEdit.setMinimumWidth(40)
        self.LineEdit.setMaximumWidth(150)
        self.LineEdit.setAlignment(Qt.AlignRight)
        self.layout().addWidget(self.LineEdit)

        if self.validator is not None:
            self.LineEdit.setValidator(self.validator)

        # Add unit label
        if self.unitlabel is not None:
            self.Label = QLabel()
            self.Label.setText(self.unitlabel)
            self.layout().addWidget(self.Label)

        # Add spacer to the right
        self.layout().addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Maximum)
        )

    def get_value(self):
        """
        Get value from line edit
        """
        return self.LineEdit.text()

    def set_value(self, value):
        """
        Set value to line edit
        """
        if not isinstance(value, str):
            value = str(value)
        self.LineEdit.setText(value)

    def set_enabled(self, enabled):
        """
        Enable of disable widget elements
        """
        # enable or disable elements in the layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.widget():
                item.widget().setEnabled(enabled)

class TabWidget(QWidget):
    def __init__(self, widgets, t_title, w_titles=None):
        super().__init__()
        self.main_tab_layout = QVBoxLayout()

        self.main_tab = QTabWidget()
        self.main_tab_layout.addWidget(self.main_tab)

        self.tab_label = QWidget()
        self.main_tab.addTab(self.tab_label, t_title)

        self.tab_layout = QGridLayout()
        self.tab_label.setLayout(self.tab_layout)

        for i in range(len(widgets)):
            if w_titles:
                group = QGroupBox(w_titles[i])
            else:
                group = QGroupBox()
            layout = QVBoxLayout()
            group.setLayout(layout)
            self.tab_layout.addWidget(group)

            widget = widgets[i]
            layout.addWidget(widget)

        self.setLayout(self.main_tab_layout)

class InputForm(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.project = mainwindow.project
        self.signals = mainwindow.signals
        self.bn = self.project.bn
        # Create a layout
        self.main_layout = QVBoxLayout()

        # Tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Project Information tab
        self.project_info_tab = QWidget()
        self.tab_widget.addTab(self.project_info_tab, "Project Information")

        self.info_layout = QGridLayout()
        self.project_info_tab.setLayout(self.info_layout)

        # Left: Project Input Fields
        self.left_group = QGroupBox()
        self.left_layout = QVBoxLayout()
        self.left_group.setLayout(self.left_layout)
        self.info_layout.addWidget(self.left_group)

        self.project_name_label = QLabel("Project name")
        self.project_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.project_name_input = QLineEdit()
        self.left_layout.addWidget(self.project_name_label)
        self.left_layout.addWidget(self.project_name_input)

        self.project_characteristics_label = QLabel("Project requirements")
        self.project_characteristics_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.left_layout.addWidget(self.project_characteristics_label)

        # Critical AC code
        self.ac_code_input = QHBoxLayout()
        self.ac_code_input.setAlignment(Qt.AlignLeft)
        self.ac_code_label = QLabel("Critical aircraft code")
        self.ac_code_label.setFixedWidth(200)
        self.ac_code = QComboBox()
        ac_code_options = ["Select aircraft code", "Code A/B", "Code C", "Code D", "Code E", "Code F"]
        for code in ac_code_options:
            self.ac_code.addItem(code)
        self.ac_code.setFixedWidth(200)

        self.ac_code_input.addWidget(self.ac_code_label)
        self.ac_code_input.addWidget(self.ac_code)
        self.left_layout.addLayout(self.ac_code_input)

        # Typed parameters
        self.inputs = {
            "Projected annual operations": None,
            "Projected annual passengers": None,
            "Runway length": None,
            "Number of runways": None,
            "Number of entries/exits": None,
            "Relative taxiway length": None,
            "Apron surface area": None
        }

        # Create labels and textboxes for each input
        for field in self.inputs:
            input_layout = QHBoxLayout()
            input_layout.setAlignment(Qt.AlignLeft)
            label = QLabel(field)
            label.setFixedWidth(200)
            input_field = QLineEdit()
            input_field.setFixedWidth(200)

            self.inputs[field] = input_field

            unit = QLabel(" ")
            if field == "Runway length":
                unit.setText("m")
            elif field == "Relative taxiway length":
                unit.setText("%")
            elif field == "Apron surface area":
                unit.setText("m^2")
            elif field == "Projected annual operations":
                unit.setText("movements")

            input_layout.addWidget(label)
            input_layout.addWidget(input_field)
            input_layout.addWidget(unit)
            self.left_layout.addLayout(input_layout)

        # Add prices
        self.material_price_label = QLabel("Construction Material Prices")
        self.material_price_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.left_layout.addWidget(self.material_price_label)

        # Define input fields
        self.materials = {
            "Concrete": None,
            "Asphalt": None,
            "Cement Treated Base (CTB)": None,
            "Sand": None
        }

        # Create labels and textboxes for each input
        for field in self.materials:
            input_layout = QHBoxLayout()
            input_layout.setAlignment(Qt.AlignLeft)
            label = QLabel(field)
            label.setFixedWidth(200)
            input_field = QLineEdit()
            input_field.setFixedWidth(200)

            self.materials[field] = input_field

            input_layout.addWidget(label)
            input_layout.addWidget(input_field)
            input_layout.addWidget(QLabel("€"))
            self.left_layout.addLayout(input_layout)

        # Add input for add-ons (unit price)
        self.addons_label = QLabel("Add-ons")
        self.addons_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.left_layout.addWidget(self.addons_label)

        self.addons = {"ILS": None,
                       "Control Tower": None,
                       "Turnpads": None
                       }

        for addon in self.addons:
            checkbox = QCheckBox(addon)
            checkbox.setChecked(False)
            checkbox.setFixedWidth(200)
            if addon == "ILS":
                self.ils_cat_input = QComboBox()
                self.ils_cat_input.setFixedWidth(200)
                ils_cats = ["Select an ILS CAT", "CAT I", "CAT II", "CAT III"]
                for cat in ils_cats:
                    self.ils_cat_input.addItem(cat)
                self.ils_cat_input.setVisible(False)

                checkbox_layout = QHBoxLayout()
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.addWidget(self.ils_cat_input)
                checkbox_layout.setAlignment(Qt.AlignLeft)

                checkbox.stateChanged.connect(self.ils_check)
                self.left_layout.addLayout(checkbox_layout)

            elif addon == "Turnpads":

                self.no_turnpads = QLineEdit()
                self.no_turnpads.setFixedWidth(200)
                self.no_turnpads.setVisible(False)

                checkbox_layout = QHBoxLayout()
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.addWidget(self.no_turnpads)
                checkbox_layout.setAlignment(Qt.AlignLeft)

                checkbox.stateChanged.connect(self.turnpad_check)

                self.left_layout.addLayout(checkbox_layout)

            else:
                self.left_layout.addWidget(checkbox)

            self.addons[addon] = checkbox

        # Add a submit button
        self.submit_button = QPushButton("Calculate Cost", self)
        self.submit_button.clicked.connect(self.on_submit)
        self.info_layout.addWidget(self.submit_button)

        # Set the layout
        self.setLayout(self.main_layout)


    def on_submit(self):
        if self.ac_code.currentText() == "Select aircraft code":
            NotificationDialog(text="Select an aircraft code", severity="critical")
            return
        else:
            ac_code = {"AC code": self.ac_code.currentText()}

        try:
            int(self.inputs["Projected annual operations"].text())

        except:
            NotificationDialog(text="The projected number of annual operations must be an integer.", severity="critical")
            return

        try:
            int(self.inputs["Projected annual passengers"].text())
        except:
            NotificationDialog(text="The projected number of annual passengers must be an integer.", severity="critical")
            return

        self.project_name = self.project_name_input.text()
        self.mainwindow.update_projectname(self.project_name)
        self.signals.cond_val_about_to_change.emit('project_name', str(self.project_name))

        # Gather project parameters
        self.project_parameters = {label: textbox.text() for label, textbox in self.inputs.items()}
        self.prices = {label: textbox.text() for label, textbox in self.materials.items()}
        self.additions = {label: checkbox.checkState() for label, checkbox in self.addons.items()}

        if self.additions["ILS"] == 2:
            self.additions["ILS"] = self.ils_cat_input.currentText()

        if self.additions["Turnpads"] == 2:
            if len(self.no_turnpads.text()) == 'n.a.':
                print("Number of turnpads not specified")
                self.additions["Turnpads"] = False
            else:
                self.additions["Turnpads"] = self.no_turnpads.text()

        self.conditions = ac_code | self.project_parameters | self.prices | self.additions

        logger.info('Conditionalising...')
        self.conditionalise()

    def ils_check(self, state):
        self.ils_cat_input.setVisible(state == 2)

    def turnpad_check(self, state):
        self.no_turnpads.setVisible(state==2)

    def conditionalise(self):
        vars = {'AC code': 'AC code',
                'Projected annual operations': 'Mvts',
                'Projected annual passengers': 'pax',
                'Runway length': 'L_RWY',
                'Relative taxiway length': 'L_TWY',
                'Apron surface area': 'A_Apron',
                'Turnpads': '#Tpds',
                'Number of runways': '#RWY',
                'Number of entries/exits': '#Exits',
                'Concrete': 'c_concrete',
                'Asphalt': 'c_asphalt',
                'Cement Treated Base (CTB)': 'c_ctb',
                'Sand': 'c_sand',
                'ILS': 'ils',
                'Control Tower': 'atc'
               }

        # self.signals.cond_val_about_to_change('project_name', self.project_name)
        for key, value in self.conditions.items():
            if key == '#Tpds':
                if value == False:
                    value = '0'
            if value == '' or value == False:
                value = 'n.a.'

            self.signals.cond_val_about_to_change.emit(vars[key], str(value))

        MCM.define_bn(self)
        logger.info('Calculating conditional probabilities.')
        MCM.conditional_probabilities(self)
        logger.info('Starting design simulations.')
        MCM.pavement_design(self)

        if self.mainwindow.thirdwindow is not None:
            self.mainwindow.thirdwindow.charge_widget.calc_WACC()
            self.mainwindow.thirdwindow.charge_widget.define_ac_mix()
            self.mainwindow.thirdwindow.charge_widget.update_payback()


class AirportCharges(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.signals = self.mainwindow.signals
        self.signals.airportcharges_changed.connect(lambda: self.set_window_modified.emit(True))
        self.mvts = self.mainwindow.no_mvts / 2
        self.pax = self.mainwindow.no_pax / 2
        self.conditions = self.mainwindow.input_form.conditions
        self.calc_WACC()

        self.ac_mix_layout = QVBoxLayout()
        self.ac_mix_title = QLabel("Mix of aircraft types:")
        self.ac_mix_title.setFont(QFont("Arial", 10, QFont.Bold))
        self.ac_mix_layout.addWidget(self.ac_mix_title)
        self.ac_mix = {'Code A/B': None, 'Code C': None, 'Code D': None, 'Code E': None, 'Code F': None}

        for type in self.ac_mix.keys():
            layout = QHBoxLayout()
            label = QLabel(type)
            label.setFixedWidth(100)
            self.ac_mix[type] = QLineEdit()
            self.ac_mix[type].setText('0')
            self.ac_mix[type].setFixedWidth(50)
            perc = QLabel('%')
            layout.addWidget(label)
            layout.addWidget(self.ac_mix[type])
            layout.addWidget(perc)

            self.ac_mix_layout.addLayout(layout)
            if type == self.mainwindow.mainwindow.input_form.ac_code.currentText():
                self.ac_mix[type].setText('100')
                break

        self.confirm_ac_mix = QPushButton("Confirm mix of aircraft types")
        self.confirm_ac_mix.clicked.connect(self.define_ac_mix)

        self.ac_mix_layout.addWidget(self.confirm_ac_mix)

        self.note_confirm = QLabel("* Note that the generated charges are in \nline with the average WACC constraint.")
        self.note_confirm.setFont(QFont("Arial", 8, QFont.StyleItalic))
        self.ac_mix_layout.addWidget(self.note_confirm)

        self.define_ac_mix()

        self.charges_layout = QVBoxLayout()

        self.charge_mvts_label = QLabel("Landing charge per tonne MTOW:")
        self.charge_mvts_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.charge_mvts_label.setFixedHeight(40)
        self.charge_mvts = QSlider(Qt.Horizontal)
        self.charge_mvts.setRange(0, 10000) # Define charge per tonne MTOW
        self.charge_mvts.setValue(int(np.average(self.base_charge)*100))
        self.charge_mvts_input = QLineEdit(str(self.charge_mvts.value()/100))
        self.charge_mvts_input.setAlignment(Qt.AlignHCenter)

        self.charge_pax_label = QLabel("Passenger charge per D passenger:")
        self.charge_pax_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.charge_pax_label.setFixedHeight(40)
        self.charge_pax = QSlider(Qt.Horizontal)
        self.charge_pax.setRange(0, 10000)  # Define charge per passenger
        self.charge_pax.setValue(int(2 * np.average(self.base_charge) * 100))
        self.charge_pax_input = QLineEdit(str(self.charge_pax.value() / 100))
        self.charge_pax_input.setAlignment(Qt.AlignHCenter)

        self.opex_label = QLabel("OPEX:")
        self.opex_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.opex_label.setFixedHeight(40)
        self.opex_input = QSlider(Qt.Horizontal)
        self.opex_input.setRange(0, 10000)
        self.opex_value_label = QLineEdit()
        self.opex_value_label.setText('€ 0')
        self.opex_value_label.setAlignment(Qt.AlignHCenter)

        self.slider_mvts_layout = QVBoxLayout()
        self.slider_mvts_layout.setAlignment(Qt.AlignHCenter)
        self.slider_mvts_layout.addWidget(self.charge_mvts_label)
        self.slider_mvts_layout.addWidget(self.charge_mvts)
        self.slider_mvts_layout.addWidget(self.charge_mvts_input)

        self.slider_pax_layout = QVBoxLayout()
        self.slider_pax_layout.setAlignment(Qt.AlignHCenter)
        self.slider_pax_layout.addWidget(self.charge_pax_label)
        self.slider_pax_layout.addWidget(self.charge_pax)
        self.slider_pax_layout.addWidget(self.charge_pax_input)

        self.opex_layout = QVBoxLayout()
        self.opex_layout.setAlignment(Qt.AlignHCenter)
        self.opex_layout.addWidget(self.opex_label)
        self.opex_layout.addWidget(self.opex_input)
        self.opex_layout.addWidget(self.opex_value_label)

        self.charges_layout.addLayout(self.ac_mix_layout)
        self.charges_layout.addLayout(self.slider_mvts_layout)
        self.charges_layout.addLayout(self.slider_pax_layout)
        self.charges_layout.addLayout(self.opex_layout)

        self.charges_layout.setAlignment(Qt.AlignCenter)

        self.calc_payback()

        self.setLayout(self.charges_layout)

        self.charge_mvts.valueChanged.connect(self.charge_mvts_changed)
        self.charge_mvts_input.editingFinished.connect(self.charge_mvts_input_changed)
        self.charge_pax.valueChanged.connect(self.charge_pax_changed)
        self.charge_pax_input.editingFinished.connect(self.charge_pax_input_changed)
        self.opex_input.valueChanged.connect(self.opex_input_changed)
        self.opex_value_label.editingFinished.connect(self.opex_input_value_changed)

    def define_ac_mix(self):
        MTOW = []
        percentage = 0
        for type in self.ac_mix.keys():
            if type == 'Code A/B':
                MTOW.append(float(self.ac_mix[type].text()) / 100 * np.average([3.2, 3.83, 21.523, 5.67]))                               # Based on PIPER PA-31, CESSNA 404 Titan, CRJ-200, and DHC-6
            elif type == 'Code C':
                MTOW.append(float(self.ac_mix[type].text()) / 100 * np.average([66.32, 73.5, 47.79]))                                     # Based on B737-700, A320, and ERJ190-100
            elif type == 'Code D':
                MTOW.append(float(self.ac_mix[type].text()) / 100 * np.average([179.17, 186.88, 204.12, 150]))                            # Based on B767 series and A310
            elif type == 'Code E':
                MTOW.append(float(self.ac_mix[type].text()) / 100 * np.average([247.2, 299.37, 351.53, 228, 253, 251, 251, 230, 230]))    # Based on B777 series, B787 series, and A330 family
            elif type == 'Code F':
                MTOW.append(float(self.ac_mix[type].text()) / 100 * np.average([447.696, 560]))                                           # Based on B747 and A380
            percentage += float(self.ac_mix[type].text())

            if type == self.mainwindow.mainwindow.input_form.ac_code.currentText():
                break

        if percentage != 100:
            NotificationDialog(text='Total mix of aircraft types does not add to 100%.', severity='critical')
            return
        self.mvts_MTOW = np.average(MTOW) * self.mvts

        # Base scenario, 100% WACC split 1:2 between tonne MTOW and pax
        self.base_charge = []
        for sim in self.capex:
            self.base_charge.append((self.wacc * sim) / (self.mvts_MTOW + 2 * self.pax))

        try:
            self.charge_mvts.setValue(int(np.average(self.base_charge) * 100))
            self.charge_mvts_input.setText(str(self.charge_mvts.value() / 100))
            self.charge_pax.setValue(int(2 * np.average(self.base_charge) * 100))
            self.charge_pax_input.setText(str(self.charge_pax.value() / 100))
            logger.info('New base charge determined.')

            self.update_payback()
        except:
            logger.info('Initial base charge determined.')

    def charge_mvts_changed(self):
        value = self.charge_mvts.value()
        self.charge_mvts_input.setText(str(value / 100))
        self.update_payback()

    def charge_mvts_input_changed(self):
        try:
            value =  float(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?', self.charge_mvts_input.text())[0])
            if 0 <= value <= 50:
                self.charge_mvts.setValue(int(value * 100))
            else:
                self.charge_mvts.setValue(int(np.average(self.base_charge)*100))
        except ValueError:
            self.charge_mvts.setValue(int(np.average(self.base_charge)*100))

    def charge_pax_changed(self):
        value = self.charge_pax.value()
        self.charge_pax_input.setText(str(value/100))
        self.update_payback()


    def charge_pax_input_changed(self):
        try:
            value = float(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?', self.charge_pax_input.text())[0])
            if 0 <= value <= 50:
                self.charge_pax.setValue(int(value*100))
            else:
                self.charge_pax.setValue(int(2 * np.average(self.base_charge)*100))
        except ValueError:
            self.charge_pax.setValue(int(2 * np.average(self.base_charge)*100))


    def opex_input_changed(self):
        self.opex_value_label.setText(f'€ {int(self.opex_input.value()) * 1000:,}')
        self.update_payback()

    def opex_input_value_changed(self):
        try:
            value = float(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?', self.opex_value_label.text())[0])
            self.opex_input.setValue(int(value / 1000))
        except ValueError:
            self.opex_input.setValue(0)
            self.opex_value_label.setText('€ 0')

    def calc_WACC(self):
        self.capex = self.mainwindow.input_form.sim_data['Simulation']
        g = 0.4
        K_d = 0.07
        T = 0.258
        R_f = 0.04
        EMRP = 0.05
        EquityBeta = 0.7
        self.wacc = g * K_d * (1 + T) + (1 - g) * (R_f + EMRP * EquityBeta)
        self.max_revenue = []
        for sim in self.capex:
            self.max_revenue.append(self.wacc * sim)

    def calc_revenue(self):
        logger.info('Calculating airport charges and revenue')
        self.revenue = float(re.findall(r'[-+]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:e[-+]?\d+)?', self.charge_mvts_input.text())[0].replace(',','')) * self.mvts + float(re.findall(r'[-+]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:e[-+]?\d+)?', self.charge_pax_input.text())[0].replace(',','')) * self.pax

    def calc_payback(self):
        self.calc_revenue()
        self.opex = float(re.findall(r'[-+]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:e[-+]?\d+)?', self.opex_value_label.text())[0].replace(',',''))

        self.payback_period = []
        for sim in self.capex:
            self.payback_period.append(sim / (self.revenue - self.opex))

        logger.info("Payback period calculated")

    def update_payback(self):
        self.calc_payback()
        self.mainwindow.mainwindow.signals.airportcharges_about_to_change.emit(self.payback_period)

class SimulationBreakdown(QWidget):
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.project = self.mainwindow.project
        self.bn = self.project.bn
        self.variables_layout = QHBoxLayout()

        self.design_vars_button = QPushButton("Simulated Design Variables")
        self.design_vars_button.setMinimumWidth(300)
        self.design_vars_button.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.design_vars_button.clicked.connect(self.open_conditional_vars)

        self.cost_vars_button = QPushButton("Simulated Cost Breakdown")
        self.cost_vars_button.setMinimumWidth(300)
        self.cost_vars_button.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.cost_vars_button.clicked.connect(self.open_cost_vars)

        self.spacer = QSpacerItem(50, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.variables_layout.addWidget(self.design_vars_button)
        self.variables_layout.addItem(self.spacer)
        self.variables_layout.addWidget(self.cost_vars_button)
        self.variables_layout.setAlignment(Qt.AlignHCenter)

        self.setLayout(self.variables_layout)

    def open_conditional_vars(self):
        try:
            len(self.mainwindow.input_form.conditions) > 0
        except:
            NotificationDialog(
                text="No cost estimates have been found.",
                severity="critical")
            return
        try:
            self.conditions = self.mainwindow.input_form.conditions
        except:
            pass
        MCM.define_bn(self)
        MCM.conditional_probabilities(self)
        for node in self.bn.nodes:
            if node.condition == 'n.a.':
                self.plot_conditional_dialog = ConditionalProbabilitiesDialog(self, node.name)
                break
        self.plot_conditional_dialog.setWindowTitle("Estimates for Design Variables")
        self.plot_conditional_dialog.exec_()

    def open_cost_vars(self):
        try:
            len(self.mainwindow.input_form.conditions) > 0
        except:
            NotificationDialog(
                text="No cost estimates have been found.",
                severity="critical")
            return
        self.plot_cost_vars = CostVariablesDialog(self, 'Runway')
        self.plot_cost_vars.exec_()