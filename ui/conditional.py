import py_banshee
from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QVBoxLayout, QComboBox
from PyQt5.QtCore import QObject, Qt

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from core.mcm import MCM
from matplotlib.figure import Figure


class CondProbSignals(QObject):

    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog

    def connect_signals(self):
        self.dialog.lineedits[0].LineEdit.textEdited.connect(lambda s: self.dialog._exc_prob_changed(0, s))
        self.dialog.lineedits[1].LineEdit.textEdited.connect(lambda s: self.dialog._exc_prob_changed(1, s))
        self.dialog.lineedits[2].LineEdit.textEdited.connect(lambda s: self.dialog._exc_prob_changed(2, s))

class ConditionalProbabilitiesDialog(QDialog):

    def __init__(self, parent, node):
        """
        Constructor
        """
        super().__init__()

        self.data_path = parent.mainwindow.data_path
        self.bn = parent.mainwindow.project.bn

        self.conditions = parent.mainwindow.input_form.conditions

        MCM.define_bn(self)
        MCM.conditional_probabilities(self)

        self.icon = parent.mainwindow.icon
        self.construct_dialog(node)

        # Increase or decrease fontsize to match changes in mainwindow
        for w in self.children():
            if isinstance(w, QWidget):
                font = w.font()
                font.setPointSize(max(1, font.pointSize() + parent.mainwindow.font_increment))
                w.setFont(font)

    def construct_dialog(self, node):
        """
        Constructs the widget.
        """

        self.setWindowTitle("Conditional probabilities")
        self.setWindowIcon(self.icon)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.plot_layout = QHBoxLayout()
        self.conditionalgraph = ConditionalGraph(self, node)
        self.plot_layout.addWidget(self.conditionalgraph)

        MCM.conditional_probabilities(self)

        self.node_select = QComboBox()
        for node in self.bn.nodes:
            if node.condition != 'n.a.' or node.name == "AC code":
                continue

            self.node_select.addItem(node.name)

        self.node_select.currentIndexChanged.connect(self.plot_cond_prob)

        self.plot_layout.addWidget(self.node_select)

        self.setLayout(self.plot_layout)

        self.setFixedSize(900, 400)

    def plot_cond_prob(self):
        node = self.node_select.currentText()
        self.conditionalgraph.update_plot_distributions(node)

class CostVariablesDialog(QDialog):

    def __init__(self, parent, element):
        """
        Constructor
        """
        super().__init__()
        self.prices = parent.mainwindow.input_form.prices
        self.conditions = parent.mainwindow.input_form.conditions
        self.signals = parent.mainwindow.signals
        self.simulated_cost = parent.mainwindow.simulated_cost

        self.data_path = parent.mainwindow.data_path
        self.bn = parent.mainwindow.project.bn

        self.icon = parent.mainwindow.icon
        self.construct_dialog(element)

        # Increase or decrease fontsize to match changes in mainwindow
        for w in self.children():
            if isinstance(w, QWidget):
                font = w.font()
                font.setPointSize(max(1, font.pointSize() + parent.mainwindow.font_increment))
                w.setFont(font)

    def construct_dialog(self, element):
        """
        Constructs the widget.
        """

        self.setWindowTitle("Estimates for Element Cost")
        self.setWindowIcon(self.icon)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.plot_layout = QHBoxLayout()
        self.costgraph = CostGraph(self, element)
        self.plot_layout.addWidget(self.costgraph)

        elements = ['Runway', 'Taxiway', 'Apron', 'ILS', 'Control Tower']
        self.element_select = QComboBox()
        for element in elements:
            self.element_select.addItem(element)

        self.element_select.currentIndexChanged.connect(self.plot_design_var)

        self.plot_layout.addWidget(self.element_select)

        self.setLayout(self.plot_layout)

        self.setFixedSize(900, 400)

    def plot_design_var(self):
        element = self.element_select.currentText()
        self.costgraph.update_plot_costs(element)

class ConditionalGraph(QWidget):
    def __init__(self, mainwindow, node):
        super().__init__()
        self.mainwindow = mainwindow

        # # Create tab layout for the graph
        self.condgraph_layout = QVBoxLayout()
        self.condgraph_widget = QWidget()
        self.condgraph_widget_layout = QVBoxLayout()
        self.condgraph_widget.setLayout(self.condgraph_widget_layout)
        self.condgraph_layout.addWidget(self.condgraph_widget)

        # Construct graph
        self.plot_distributions(node)

        # Add graph to layout
        self.condgraph_widget_layout.addWidget(self.conditional_graph)

        self.setLayout(self.condgraph_widget_layout)

    def plot_distributions(self, node):
        names = self.mainwindow.names
        distributions = self.mainwindow.distributions
        parameters = self.mainwindow.parameters
        n = self.mainwindow.n
        node_index = names.index(node)
        dist, param = py_banshee.prediction.make_dist([distributions[node_index]], [parameters[node_index]])

        F_cond = self.mainwindow.design_vars[node]

        if len(parameters[node_index]) == 3:
            F_uncond = dist[0].rvs(param[0][0], param[0][1], param[0][2], size=n)
        elif len(parameters[node_index]) == 2:
            F_uncond = dist[0].rvs(param[0][0], param[0][1], size=n)
        else:
            print('Parameters do not match!', parameters[node_index])

        self.conditional_graph = FigureCanvasQTAgg(Figure())
        self.conditional_ax = self.conditional_graph.figure.subplots()

        self.uncond_n, self.uncond_bins, self.uncond_patches = self.conditional_ax.hist(
            F_uncond, bins=100, density=False, color='silver', edgecolor='silver', label=['un-conditionalized\n mean: ' + f'{round(np.mean(F_uncond), 0):,}']
        )
        self.cond_n, self.cond_bins, self.cond_patches = self.conditional_ax.hist(
            F_cond, bins=100, density=False, color='cornflowerblue', edgecolor='cornflowerblue', label=['conditionalized\n mean: ' + f'{round(np.mean(F_cond), 0):,}']
        )

        self.conditional_ax.set_xlabel("x")
        self.conditional_ax.set_ylabel("Count")

        self.conditional_ax.legend()
        self.conditional_graph.draw()

        self.conditional_graph.show()

    def update_plot_distributions(self, node):
        names = self.mainwindow.names
        distributions = self.mainwindow.distributions
        parameters = self.mainwindow.parameters
        n = self.mainwindow.n
        node_index = names.index(node)
        dist, param = py_banshee.prediction.make_dist([distributions[node_index]], [parameters[node_index]])

        F_cond = self.mainwindow.design_vars[node]

        if len(parameters[node_index]) == 3:
            F_uncond = dist[0].rvs(param[0][0], param[0][1], param[0][2], size=n)
        elif len(parameters[node_index]) == 2:
            F_uncond = dist[0].rvs(param[0][0], param[0][1], size=n)
        else:
            print('Parameters do not match!', parameters[node_index])

        self.conditional_ax.clear()

        self.uncond_n, self.uncond_bins, self.uncond_patches = self.conditional_ax.hist(
            F_uncond, bins=100, density=False, color='silver', edgecolor='silver',
            label=['un-conditionalized\n mean: ' + f'{round(np.mean(F_uncond), 0):,}']
        )
        self.cond_n, self.cond_bins, self.cond_patches = self.conditional_ax.hist(
            F_cond, bins=100, density=False, color='cornflowerblue', edgecolor='cornflowerblue',
            label=['conditionalized\n mean: ' + f'{round(np.mean(F_cond), 0):,}']
        )

        self.conditional_ax.set_xlabel("x")
        self.conditional_ax.set_ylabel("Count")

        self.conditional_ax.legend()
        self.conditional_graph.draw()

        self.conditional_graph.show()

class CostGraph(QWidget):
    def __init__(self, mainwindow, element):
        super().__init__()
        self.mainwindow = mainwindow
        # self.prices = self.mainwindow.prices
        # self.n = self.mainwindow.mainwindow.n
        # self.bn = self.mainwindow.bn
        self.conditions = self.mainwindow.conditions
        self.signals = self.mainwindow.signals

        self.simulated_cost = self.mainwindow.simulated_cost
        # # Create tab layout for the graph
        self.costgraph_layout = QVBoxLayout()
        self.costgraph_widget = QWidget()
        self.costgraph_widget_layout = QVBoxLayout()
        self.costgraph_widget.setLayout(self.costgraph_widget_layout)
        self.costgraph_layout.addWidget(self.costgraph_widget)

        self.cost_graph = FigureCanvasQTAgg(Figure())
        self.cost_ax = self.cost_graph.figure.subplots()

        # Add graph to layout
        self.costgraph_widget_layout.addWidget(self.cost_graph)

        self.setLayout(self.costgraph_widget_layout)

        # Construct graph
        self.plot_costs(element)

    def plot_costs(self, element):
        data = self.simulated_cost[element]



        self.cond_n, self.cond_bins, self.cond_patches = self.cost_ax.hist(
            data, bins=100, density=False, color='cornflowerblue', edgecolor='cornflowerblue', label=['mean: ' + f'€{round(np.mean(data), 0):,}']
        )

        self.cost_ax.set_xlabel("x")
        self.cost_ax.set_ylabel("Count")

        self.cost_ax.legend()
        self.cost_graph.draw()

        self.cost_graph.show()

    def update_plot_costs(self, element):
        data = self.simulated_cost[element]
        self.cost_ax.clear()

        self.cond_n, self.cond_bins, self.cond_patches = self.cost_ax.hist(
            data, bins=100, density=False, color='cornflowerblue', edgecolor='cornflowerblue',
            label=['mean: ' + f'€{round(np.mean(data), 0):,}']
        )

        self.cost_ax.set_xlabel("x")
        self.cost_ax.set_ylabel("Count")

        self.cost_ax.legend()
        self.cost_graph.draw()

        self.cost_graph.show()