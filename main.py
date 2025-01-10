
import numpy as np
from scipy import integrate
import matplotlib.pyplot as plt

from lib.utils import  LRCircuit, define_function , create_nonlinear_device



def L_model(x,a,b,c,d):
    # inductance model
    ret = (a / b) * (1 - np.tanh((x-c) / b)**2) 
    ret[x<c] = a/b
    ret += d
    return ret 

def R_model(x,a,b,c,sigma,amp, mu ,r0):
    # resistance model
    ret = (a / b) * (1 - np.tanh((x-c) / b)**2) 
    ret[x<c] = a/b
    
    ret = ret + ret* amp / (np.sqrt(2 * np.pi) * sigma)*np.exp(-0.5 * ((x - mu) / sigma)**2) + r0

    return 1/ret 

# some example current array
current_array = np.array([  0. ,   6.2,  12.4,  27.9,  52.8,  80.7,  96.2, 114.9, 133.5,#-
       155.2, 166.3, 174.5, 186.3, 191.7, 200.4, 204. , 208. , 210. ,#-
       212. , 217.3, 222. , 227.5, 248.4, 279.4, 310.4, 341.5, 372.5,#-
       403.6, 434.7, 496.7, 620.9, 800. ])

# L,R(i) - for f=10**5
L   = L_model(current_array , a=0.0001,b=40,c=170,d=10**-7)
R   = R_model(current_array , a=7,b=110,c=190,sigma=40,amp=50,mu=185,r0=3*10**-5)

Phi = integrate.cumulative_trapezoid( y = L ,x=current_array, initial = 0 )
Ur  = integrate.cumulative_trapezoid( y = R ,x=current_array, initial = 0 )

Phin = np.stack((current_array[1:], Phi[1:]), axis=1)
Urn = np.stack((current_array[1:], Ur[1:]), axis=1)


plt.figure(figsize= (3, 2))
plt.title('R(i)')
plt.xlabel('Current (A)')
plt.ylabel(r'Resistance ($\Omega$)')
plt.semilogy(current_array, R,'*-' )
plt.grid()
plt.savefig('R.png', bbox_inches='tight')

plt.figure(figsize= (3, 2))
plt.title('L(i)')
plt.xlabel('Current (A)')
plt.ylabel('Inductance (H)')
plt.semilogy(current_array, L ,'*-')
plt.grid()
plt.savefig('L.png', bbox_inches='tight')



# define nonlinear functions 
raw_spice_function_Phi = define_function(name='Phi',
                                    data=Phin, order=3, odd=True,
                                    write_params=True)

raw_spice_function_Ur= define_function(name='Ur',
                                    data=Urn, order=3, odd=True,
                                    write_params=True)


# define nonlinear .SUBCKT 
lr_name = 'nlindv2'
raw_spice_nonlinear_device = create_nonlinear_device(element_name = lr_name, func_name_Phi='Phi', func_name_Ur='Ur')

raw_spice_all = ""
raw_spice_all +=raw_spice_function_Phi
raw_spice_all +=raw_spice_function_Ur
raw_spice_all +=raw_spice_nonlinear_device

with open("raw_spice_all.txt", "w") as file:
    file.write(raw_spice_all)



#######################################################
# EXAMPLE OF USE WITH Pyspice
#######################################################

from PySpice.Unit import *

#start building the circuit using Pyspice

circuit = LRCircuit('NonLinearDev')

circuit.raw_spice+= raw_spice_all

source_frequency = 10**5
current_max = 900

source = circuit.SinusoidalCurrentSource('uin', 'in0', circuit.gnd,
                                            amplitude = current_max,
                                            frequency = source_frequency,
                                            damping_factor = 1*0.55*source_frequency)
circuit.R('almost_zero', 'in0', 'Ring_in', 10**-9 @u_Ohm)
circuit.R('rin', 'Ring_in', 1 , 10**-9 @u_Ohm)
circuit.X(lr_name, lr_name,  1, 2)
circuit.R('rout', 2,'Ring_out', 10**-9 @u_Ohm)
r_current_measure_value = 1
circuit.R('r0', 'Ring_out', circuit.gnd, r_current_measure_value)
circuit.add_options('rshunt=1.0e11  rseries=1.0e-12' )  

# save Spice code to file
with open("circuit_elements.txt", "w") as file:
    file.write(circuit.raw_spice)
with open("circuit_netlist.txt", "w") as file:
    file.write(circuit._str_elements())


simulator   = circuit.simulator()
analysis    = simulator.transient(step_time=source.period/9000, end_time=source.period*4.0)


current_sim =   np.array(-(analysis['Ring_out'])/r_current_measure_value)
voltage_sim =   np.array(analysis['Ring_out']- analysis['Ring_in'])
time_sim    =   np.array(analysis.time)

figure      =   plt.figure(figsize= (20/4, 10/3))

plt.xlabel('Time (us)')
plt.ylabel('Voltage (V)/Current (A)')
plt.grid()

plt.plot(time_sim*10**6 ,voltage_sim ,label='voltage on LR',color='red',linewidth=2)
plt.plot(time_sim*10**6 ,current_sim ,label='current',color='black',linewidth=2)
plt.legend(loc='best')
plt.savefig('uit.png', bbox_inches='tight')