import py_banshee
import numpy as np
import re
import scipy.stats as stats

class MCM:
    def __init__(self, mainwindow):
        self.mainwindow = mainwindow
        self.signals = self.mainwindow.signals
        self.project = self.mainwindow.project

        self.bn = self.mainwindow.bn

    def define_bn(self):
        self.ids = {key.name: i for i, key in enumerate(self.bn.nodes)}

        self.names = []
        self.distributions = []
        self.parameters = []
        self.ParentCell = []
        self.RankCorr = []
        self.condition_nodes = []
        self.condition_values = []

        if self.conditions['AC code'] in ['Code A/B', 'Code C']:
            self.size = 'small'
        else:
            self.size = 'large'

        for node in self.bn.nodes:
            self.names.append(node.name)
            self.distributions.append(node.distribution)

            if self.size == 'small':
                parameters = node.parameters_small
            else:
                parameters = node.parameters_large

            if node.distribution == 'triang':
                c_min, c_mode, c_max = parameters
                c = (c_mode - c_min) / (c_max - c_min)
                loc = c_min
                scale = c_max - c_min
                self.parameters.append([c, loc, scale])
            else:
                self.parameters.append(parameters)

            parents = []
            rank_corrs = []
            for edge in node.edges:
                parents.append(self.ids[edge.parent])
                rank_corrs.append(edge.cond_rank_corr)

            self.ParentCell.append(parents)
            self.RankCorr.append(rank_corrs)

            if node.condition != 'n.a.':
                self.condition_nodes.append(self.ids[node.name])

                if node.name == 'AC code':
                    if node.condition == "Code F":
                        self.W_RWY, self.d_sep, self.W_TWY, self.A_tpd = [60, 190, 25, 0]             # No known turnpads for code F traffic
                    elif node.condition == "Code E":
                        self.W_RWY, self.d_sep, self.W_TWY, self.A_tpd = [45, 182.5, 23, 2520]        # A_tpd from Luton Airport
                    elif node.condition == "Code D":
                        self.W_RWY, self.d_sep, self.W_TWY, self.A_tpd = [45, 176, 23, 2520]          # A_tpd from Luton Airport
                    elif node.condition == "Code C":
                        self.W_RWY, self.d_sep, self.W_TWY, self.A_tpd = [30, 168, 18, 1015]          # A_tpd from Dawson City Airport
                    else:
                        self.W_RWY, self.d_sep, self.W_TWY, self.A_tpd = [23, 87, 10.5, 512]          # A_tpd from Kasos Airport
                    self.condition_values.append(self.W_RWY)
                else:
                    self.condition_values.append(float(node.condition))

        self.L_exit = self.d_sep - (self.W_RWY + self.W_TWY) / 2
        self.design_vars = {key: None for key in self.names}
        for node in self.condition_nodes:
            self.design_vars[self.names[node]] = self.bn.nodes[node].condition
        self.design_vars['AC code'] = self.W_RWY

    def conditional_probabilities(self):
        self.n = 100000
        R = py_banshee.rankcorr.bn_rankcorr(self.ParentCell, self.RankCorr, var_names=self.names, is_data=False, plot=False)

        self.F = py_banshee.prediction.inference(Nodes=self.condition_nodes,
                                            Values=self.condition_values,
                                            R=R,
                                            DATA=[],
                                            SampleSize=self.n,
                                            empirical_data=False,
                                            distributions=self.distributions,
                                            parameters=self.parameters,
                                            Output='full')

        dist_vars = [name for i, name in enumerate(self.names) if i not in self.condition_nodes]

        self.dist_vars = dict(zip(dist_vars, self.F[0]))
        for key in self.dist_vars.keys():
            self.design_vars[key] = self.dist_vars[key]


    def pavement_design(self):
        # Define factors for financial circumstances for SEJ study cases
        c_TWY_ref = [157.9, 148.55, 46.47, 12.15]
        f_TWY = np.sum(c_TWY_ref)
        c_RWY_ref = [157.9, 252, 48, 22.5]
        f_RWY = np.sum(c_RWY_ref)
        c_apron_ref = [433.15, 1612.8, 414.35, 44]
        f_apron = np.sum(c_apron_ref)
        c_af_ref = [575, 252, 414.35, 22.5]
        f_af = np.sum(c_af_ref)

        # Calculate current financial circumstances (if n.a. assumes Dutch prices)
        costs = []
        for i in range(len(self.prices)):
            keys = ['Concrete', 'Asphalt', 'Cement Treated Base (CTB)', 'Sand']
            c = self.prices[keys[i]]

            if c != 'n.a.' and c != '':
                costs.append(float(re.findall(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?', c)[0]))

            else:
                costs.append(float(c_RWY_ref[i]))

        curr_cost = np.sum(costs)
        if curr_cost == 0:
            curr_cost = f_RWY

        # Correct for financial circumstances
        self.f_TWY_c = curr_cost / f_TWY
        self.f_RWY_c = curr_cost / f_RWY
        self.f_apron_c = curr_cost / f_apron
        self.f_af_c = curr_cost / f_af

        # Define the m2 prices and supplements for investment cost and risk reserve according to SEJ study
        SEJ_costs = {'m2_TWY': [12.78, 37.29, 389],
                     'invest_TWY': [10.65, 23.81, 87.44],
                     'm2_RWY': [61.9, 131.4, 445.9],
                     'invest_RWY': [10.71, 28.75, 103.9],
                     'm2_apron': [175, 403.7, 2102],
                     'invest_apron': [10.88, 32.8, 89.28],
                     'airfield': [30220000, 86360000, 528700000],
                     'invest_af': [11.01, 37.47, 91.09],
                     'risk': [10.04, 17.41, 48.87]
                     }

        # Simulate m2 prices and supplements according to triangular probability distribution
        self.cost_sims = {key: None for key in SEJ_costs.keys()}

        for key, item in SEJ_costs.items():
            c_min, c_mode, c_max = item
            c = (c_mode - c_min) / (c_max - c_min)

            self.cost_sims[key] = stats.triang.rvs(c=c, loc=c_min, scale=(c_max-c_min), size=self.n)

        # For defined variables, fill array with n times the conditional value
        for key, item in self.design_vars.items():
            try:
                len(item) < self.n
                self.design_vars[key] = np.full(self.n, float(item))
            except:
                pass

        if self.conditions['ILS'] == False:
            self.c_ILS = np.zeros(self.n)
        else:
            if self.conditions['ILS'] == 'Cat I':
                self.c_ILS = stats.uniform.rvs(size=self.n, loc=1582000, scale=(1685000 - 1582000))
            else:
                self.c_ILS = stats.uniform.rvs(size=self.n, loc=2293000, scale=(2550000 - 2293000))

        if self.conditions['Control Tower'] == 0:
            self.c_ATC = np.zeros(self.n)
        else:
            self.c_ATC = stats.expon.rvs(size=self.n, loc=814307.846885, scale=3706531.633851403)

        self.simulations = {
                       "A_RWY": [self.W_RWY * L_RWY for L_RWY in self.design_vars['L_RWY']],
                       "A_tpds": [self.A_tpd * int(no_tpds) for no_tpds in self.design_vars['#Tpds']],
                       "A_TWY": [self.W_TWY * L_TWY / 100 for L_TWY in self.design_vars['L_TWY']],
                       "A_exits": [self.L_exit * self.W_TWY * int(no_exits) for no_exits in self.design_vars['#Exits']],
                       "c_RWY": [self.f_RWY_c * m2_RWY for m2_RWY in self.cost_sims['m2_RWY']],
                       "c_TWY": [self.f_TWY_c * m2_TWY for m2_TWY in self.cost_sims['m2_TWY']],
                       "c_apron": [self.f_apron_c * m2_apron for m2_apron in self.cost_sims['m2_apron']],
                       "c_airfield": [self.f_af_c * airfield for airfield in self.cost_sims['airfield']],
                       "c_ILS": [self.c_ILS],
                       "c_ATC": [self.c_ATC]
                       }

        self.elements = ['Runway', 'Taxiway', 'Apron', 'Airfield', 'ILS', 'Control Tower']
        self.simulated_cost = {key: [] for key in self.elements}
        self.simulated_cost['ILS'] = self.c_ILS
        self.simulated_cost['Control Tower'] = self.c_ATC
        self.sim_data = {'Simulation': [],
                      'Rough estimate': []}

        for sim in range(self.n):
            rwy = (self.simulations['A_RWY'][sim] + self.simulations['A_tpds'][sim]) * self.simulations['c_RWY'][sim] * (1 + self.cost_sims['invest_RWY'][sim] / 100)
            twy = (self.simulations['A_TWY'][sim] + self.simulations['A_exits'][sim]) * (1 + self.simulations['c_TWY'][sim] * self.cost_sims['invest_TWY'][sim] / 100)
            apron = self.design_vars['A_Apron'][sim] * self.simulations['c_apron'][sim] * (1 + self.cost_sims['invest_apron'][sim] / 100)
            airfield = self.simulations['c_airfield'][sim] * (1 + self.cost_sims['invest_af'][sim] / 100) + self.f_af_c * (self.c_ILS[sim] + self.c_ATC[sim])
            self.simulated_cost['Runway'].append(rwy)
            self.simulated_cost['Taxiway'].append(twy)
            self.simulated_cost['Apron'].append(apron)
            self.simulated_cost['Airfield'].append(airfield)

            self.sim_data['Simulation'].append((np.sum([rwy, twy, apron]) + self.c_ILS[sim] + self.c_ATC[sim]) * (1 + self.cost_sims['risk'][sim] / 100))
            self.sim_data['Rough estimate'].append(airfield * (1 + self.cost_sims['risk'][sim] / 100))

        self.signals.simdata_about_to_be_updated.emit(self.sim_data)
        self.mainwindow.simulated_cost = self.simulated_cost





