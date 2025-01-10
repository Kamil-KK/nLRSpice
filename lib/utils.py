import numpy as np
from os import linesep
from PySpice.Spice.Netlist import Circuit

from scipy.interpolate import CubicSpline 



class LRCircuit(Circuit):

    def __init__(self, title):
        super().__init__(title)

    def add_options(self, options):
        self.raw_spice += '.option ' + options + linesep


def define_function(name='func', data=np.array([]), order=1, odd=True, write_params=True):
    """
    :param name: name of function to be created
    :param data: ndarray of [x,y] pairs defining characteristic curve
    :param order: order of spline polynomial (1st or 3rd are allowed only)
    :param odd: True if odd-like function has to be created
    :param write_params: if True .PARAM block will be written
    :return: string containing .PARAM and .FUNC blocks to be inserted in NgSpice code
    """
    assert type(data) == np.ndarray, "characteristic data should be passed in numpy array: [[x1,y1],[x2,y2],...]"
    assert order == 1 or order == 3, "only linear and cubic splines are implemented"
    if odd:
        assert np.amin(data[:, 0]) > 0, "in case of odd=True all function arguments should be positive"
    data = data[data[:, 0].argsort()].astype(np.float32)  # sort points by x-value
    if odd:
        data = np.concatenate((data[::-1]*(-1), [[0., 0.]], data))
    no_points = data.shape[0]
    assert no_points > 1, "too few data points, at last 2 points needed"
    # define parameters
    param_str = ".PARAM {" + linesep
    funct_str = ".FUNC " + name + "(x) {" + linesep
    for i in range(no_points):
        param_str += "+ "
        param_str += "xl" + str(i) + "=" + f"{data[i, 0]:.15}" + linesep
        # param_str += "y" + str(i) + "=" + str(data[i, 1]) + linesep
    param_str += "+ }" + linesep
    # define function
    if order == 1:
        a = [(data[i + 1, 1] - data[i, 1]) / (data[i + 1, 0] - data[i, 0]) for i in range(no_points-1)]
        b = [data[i + 1, 1] - a[i] * data[i + 1, 0] for i in range(no_points-1)]
        y = [f"{a[i]:.15f}*x{b[i]:+.15f}" for i in range(no_points-1)]
    else:
        #cs= Akima1DInterpolator(data[:, 0], data[:, 1])
        cs = CubicSpline(data[:, 0], data[:, 1])
        y = [f"{cs.c[0,i]:.8e}*(x-xl{i})^3{cs.c[1,i]:+.8e}*(x-xl{i})^2{cs.c[2,i]:+.8e}*(x-xl{i}){cs.c[3,i]:+.8e}" for i in range(no_points-1)]
    funct_str += "+ x<xl0 ? " + y[0] + " : (" + linesep
    for i in range(no_points-1):
        funct_str += "+ "
        funct_str += "x<xl" + str(i+1) + " ? " + y[i] + " : (" + linesep
    funct_str += "+ " + y[no_points-2] + ")"*no_points
    funct_str += linesep + "+ }" + linesep
    if write_params:
        return param_str + funct_str
    else:
        return funct_str


def create_nonlinear_device(element_name='nlindv2', func_name_Phi='func_Phi', func_name_Ur='func_Ur'):
    """
    :param element_name: name of the defined element as viewed in NgSpice
    :param func_name: name of the characteristic function \Phi defined as:
    * nonlinear inductor equations:
    * U = -L df(I)/dt = -L df(I)/dI dI/dt = -L'(I) dI/dt,
    * L'(I) = L df(I)/dI -> f(I) = 1/L int dI L'(I) => f(I) = \Phi(I)
    :param scaling: characteristics scaling, default = no scaling
    :return: string containing .SUBCKT blocks to be inserted in NgSpice code
    """
    sub_str = ".SUBCKT " + element_name + " pos neg "  + linesep
    sub_str += "Vm pos pos1 DC 0V" + linesep
    sub_str += "Bx 1 0 i = " + func_name_Phi + "(i(Vm))" + linesep
    sub_str += "Lx 1 4 1H IC=1A" + linesep
    sub_str += "VmL 4 0 DC 0V" + linesep  
    
    sub_str += "Rs 3 0 1"+ linesep
    sub_str += "VmR 1 2 DC 0V" + linesep
    sub_str += "BxR 2 3 v = " + func_name_Ur + "(i(Vm))/"+func_name_Phi + "(i(Vm))*i(VmR)" + linesep

    sub_str += "Ex pos1 neg 0 1 1" + linesep

    sub_str += ".ENDS " + element_name + linesep
    return sub_str

def create_nonlinear_inductor_debuged(element_name='nlind', func_name_Phi='func_Phi', func_name_Ur='func_Ur', scaling=1. , omega=1.):
    """
    :param element_name: name of the defined element as viewed in NgSpice
    :param func_name: name of the characteristic function \Phi defined as:
    * nonlinear inductor equations:
    * U = -L df(I)/dt = -L df(I)/dI dI/dt = -L'(I) dI/dt,
    * L'(I) = L df(I)/dI -> f(I) = 1/L int dI L'(I) => f(I) = \Phi(I)
    :param scaling: characteristics scaling, default = no scaling
    :return: string containing .SUBCKT blocks to be inserted in NgSpice code
    """
    sub_str = ".SUBCKT " + element_name + " pos neg k_L k_R i_phi i_i is = " + str(scaling) + linesep
    sub_str += "Vm pos pos1 DC 0V" + linesep
    sub_str += "Bx 1 0 i = " + func_name_Phi + "(i(Vm)/{is})" + linesep
    sub_str += "Lx 1 4 1H IC=1A" + linesep
    sub_str += "VmL 4 0 DC 0V" + linesep  # do pomiaru pradu Lx
    
    sub_str += "Rs 3 0 1"+ linesep
    sub_str += "VmR 1 2 DC 0V" + linesep
    sub_str += "BxR 2 3 v = " + func_name_Ur + "(i(Vm))/"+func_name_Phi + "(i(Vm))*i(VmR)" + linesep

    sub_str += "Ex pos1 neg 0 1 1" + linesep

    sub_str += "BxL k_L 0 i = i(VmL)/"+func_name_Phi + "(i(Vm)/{is})" + linesep # pomiar testowy pradu przez cewke
    sub_str += "RxL k_L 0 1" + linesep # pomiar testowy
    sub_str += "BxE k_R 0 i = i(VmR)/"+func_name_Phi + "(i(Vm)/{is})" + linesep # pomiar testowy - energia zmagazynowana w cewce
    sub_str += "RxE k_R 0 1" + linesep # pomiar testowy

    sub_str += "BxP i_Phi 0 i = " + func_name_Phi + "(i(Vm)/{is})" + linesep # pomiar testowy -
    sub_str += "RxP i_Phi 0 1" + linesep # pomiar testowy

    sub_str += "Bxi i_i 0 i =  i(Vm)/{is} " + linesep # pomiar testowy -
    sub_str += "Rxi i_i 0 1" + linesep # pomiar testowy
    sub_str += ".ENDS " + element_name + linesep
    return sub_str
