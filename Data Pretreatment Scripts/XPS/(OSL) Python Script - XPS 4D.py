###############################################################
## Organic Semiconductor Lab, SAINT, SKKU ##
## Source code copyright to Taewoong Yoon ##
## +++++ Email: TWYoon.rs@gmail.com +++++ ##
## ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ##
## ░░░░░░░█████░░░░███████░░██░░░░░░░░░░░ ##
## ░░░░░██░░░░░██░██░░░░░██░██░░░░░░░░░░░ ##
## ░░░░░█░░░░░░░█░███░░░░░░░██░░░░░░░░░░░ ##
## ░░░░░█░░░░░░░█░░░█████░░░██░░░░░░░░░░░ ##
## ░░░░░█░░░░░░░█░░░░░░░███░██░░░░░░░░░░░ ##
## ░░░░░██░░░░░██░██░░░░░██░██░░░░░██░░░░ ##
## ░░░░░░░█████░░░░███████░░█████████░░░░ ##
## ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ##
## ++++++++++++++++++++++++++++++++++++++ ##

## ++++++++++++ FOR XPS Data Aquisition ++++++++++++ ##
## ------------------- Binding Energy Auto Calibration.
## ----- Get incident X-ray beam energy from file info.
## -------------- Kinetic to Binding Energy Conversion.

############### Functions ################
def findmax(A):
    floate = float(A[0])
    e = ''
    index = 0
    for i in range(len(A)):
        if float(A[i]) > floate:
            floate = float(A[i])
            index = i
            e = A[i]
    return index, round(floate,2), e

def Excitation(A):
    str1 = A[-2].strip('eV1sf')
    str2 = A[-1].strip('eV1sf')
    if str1 == '':
        return int(str2)
    if str2 == '':
        return int(str1)
    if int(str1) > int(str2):
        return int(str1)
    else:
        return int(str2)

################ Start ################
import os
print("Organic Semiconductor Lab, SAINT, SKKU", "Source code copyright to Taewoong Yoon", "+++++ Email: TWYoon.rs@gmail.com +++++", "░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░", "░░░░░░░█████░░░░███████░░██░░░░░░░░░░░", "░░░░░██░░░░░██░██░░░░░██░██░░░░░░░░░░░", "░░░░░█░░░░░░░█░███░░░░░░░██░░░░░░░░░░░", "░░░░░█░░░░░░░█░░░█████░░░██░░░░░░░░░░░", "░░░░░█░░░░░░░█░░░░░░░███░██░░░░░░░░░░░", "░░░░░██░░░░░██░██░░░░░██░██░░░░░██░░░░", "░░░░░░░█████░░░░███████░░█████████░░░░", "░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░", "++++++++++++++++++++++++++++++++++++++", sep="\n")
print('\n\nNow Running: ', os.path.realpath(__file__), '\n')
fileList = os.listdir()
fileList.remove('XPS.py')

### Common peaks table ###
print('+{0:-^10} Common BE peak {0:-^10}+'.format('-'))
print('{0:<22}{1:>16}'.format('| C1s (C-C) : ', ' 284.8 eV |'))
print('{0:<22}{1:>16}'.format('| N1s (C-NH2) : ', ' ~ 400 eV |'))
print('{0:<22}{1:>16}'.format('| F1s (Organic) : ', ' 688~689 eV |'))
print('+{0:-^36}+\n\n'.format(''))

### Declare variables ###
temp = []
info = []
data = []
KE = []
BE_Err = []
BE = []
intensity = []
start = 0
Err = 0
Ex = 0


for txtname in fileList:
    if '_edited_' in txtname:
        continue
    if '_raw_' in txtname:
        continue
    print("=== Now processing: ", txtname, " ===\n")
    print("~~ If you want to skip this file, enter 0. ~~")
    
    realBE = float(input("BE of target bond or atom [eV]: "))
    if realBE == 0:
        for z in range(len(txtname)+24):
            print('=', end='')
        print('\n')
        continue

    RAW = open(txtname, "r")
    temp = RAW.readlines()
    RAW.close()
    
    for i in temp:
        if "[Data 1]" in i:
            start = temp.index(i) + 1
            break
    
    info = temp[:start-1]
    data = temp[start:len(temp)-1]
    ###
    
    for j in info:
        if "Region Name" in j:
            text = j.split('\x00')[0].split()
            Ex = Excitation(text)
            break
    
    
    for k in data:
        KE.append(round(float(k.split()[0]),2))
        intensity.append(round(float(k.split()[1]),2))
        BE_Err.append(round(Ex - float(k.split()[0]),2))
        BE.append(round(Ex - float(k.split()[0]),2) - Err)
    
    maxInfo = findmax(intensity)
    
    Err = round(BE_Err[maxInfo[0]] - realBE,2)
    print('+{0:-^16} Summary {0:-^15}+'.format('-'))
    print('{0:<22}{1:>15.2f}{2:>5}'.format('| Excitation Energy: ', Ex, ' eV |'))
    print('{0:<22}{1:>15.2f}{2:>5}'.format('| Max intensity: ', maxInfo[1], ' au |'))
    print('{0:<22}{1:>15.2f}{2:>5}'.format('| KE @ Max intensity: ', KE[maxInfo[0]], ' eV |'))
    print('{0:<22}{1:>15.2f}{2:>5}'.format('| BE @ Max intensity: ', BE_Err[maxInfo[0]], ' eV |'))
    print('{0:<22}{1:>15.2f}{2:>5}'.format('| Real BE: ', realBE, ' eV |'))
    print('{0:<22}{1:>13.2f}{2:>5}'.format('| Error (Meas - real) : ', Err, ' eV |'))
    print('+{0:-^40}+'.format(''))
    # print('____DEBUG____ MAX:', maxInfo, '_____ Err:', Err)


    RawName = "_raw_"
    RawName += txtname[:-4]
    RawName += '.txt'
    CalibName = "_edited_"
    CalibName += txtname[:-4]
    CalibName += '.txt'

    RawOut = open(RawName, 'w')
    CalibOut = open(CalibName, 'w')
    for l in range(len(BE)):
        Raw = str(round(BE_Err[l],2)); Raw += '\t'; Raw += str(round(intensity[l],2)); Raw += '\n'
        Calib = str(round(BE[l],2)); Calib += '\t'; Calib += str(round(intensity[l],2)); Calib += '\n'
        RawOut.write(Raw)
        CalibOut.write(Calib)
    RawOut.close()
    CalibOut.close()
    
    temp.clear()
    info.clear()
    data.clear()
    KE.clear()
    BE_Err.clear()
    BE.clear()
    intensity.clear()
    start = 0
    Err = 0
    Ex = 0
    
    for z in range(len(txtname)+26):
        print('=', end='')
    print('\n')

input('Press Enter to exit')
