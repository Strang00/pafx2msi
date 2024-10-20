VERSION   = 'PAFX2MSI Strang\'s convertor v1.1'
COMMENT   = 'Converts antenna patterns from PAFX format to MSI format'
USAGE     = 'Usage: pafx2msi.py [-h|--help] [data/*.pafx]'
COPYRIGHT = '(c) 2024 Sergey Arkhipov'

import os
import sys
import glob
import datetime
import zipfile
import xml.etree.ElementTree as ET 


class PatternDescriptor:
    def __init__(self, options=None):
        self.name = ''
        self.file = ''
        self.polarization = ''
        self.front_to_back = ''
        self.beam_width = 0
        self.beam_height = 0
        self.tilt = 0
        self.frequency = 0
        self.max_gain_db = 0
        self.max_gain_unit = 'dBi'
        self.comment = ''
        self.rho_v = [0.0]*360
        self.rho_h = [0.0]*360

    def __repr__(self) -> str:
        return (f"--- Pattern {self.file}\n" + self.header())

    def header(self) -> str:
        return (f"NAME {self.name}\n"
                f"FREQUENCY {self.frequency}\n"
                f"H_WIDTH {self.beam_width}\n"
                f"V_WIDTH {self.beam_height}\n"
                f"FRONT_TO_BACK {self.front_to_back}\n"
                f"GAIN {self.max_gain_db} {self.max_gain_unit}\n"
                f"ELECTRICAL_TILT {self.tilt}\n"
                f"POLARIZATION {self.polarization}\n"
                f"COMMENT {self.comment}")

    def msi(self) -> str:
        hor = "HORIZONTAL 360\n"
        for i in range(360):
            hor += '{i} {v:.2f}\n'.format(i=i, v=self.rho_h[i])

        ver = "VERTICAL 360\n"
        for i in range(360):
            ver += '{i} {v:.2f}\n'.format(i=i, v=self.rho_v[i])

        return self.header() + '\n' + hor + ver

def parse_pap(filexml, descr): 
    tree = ET.parse(filexml) 
    root = tree.getroot()
    
    hor = root.find('.//HorizontalPattern')
    h_gains = hor.find('Gains').text.split(';')
    h_start = int(hor.find('StartAngle').text)
    h_end = int(hor.find('EndAngle').text)
    h_step = int(hor.find('Step').text)
    counter = 0
    for i in range(h_start, h_end + h_step, h_step):
        descr.rho_h[(i+360)%360] = abs(float(h_gains[counter]))
        counter += 1

    ver = root.find('.//VerticalPattern')
    v_gains = ver.find('Gains').text.split(';')
    v_start = int(ver.find('StartAngle').text)
    v_end = int(ver.find('EndAngle').text)
    v_step = int(ver.find('Step').text)
    counter = 0
    for i in range(v_start, v_end + v_step, v_step):
        descr.rho_v[(i+360)%360] = abs(float(v_gains[counter]))
        counter += 1

    #print(f'Pattern {descr.name} have {len(h_gains)} HGains and {len(v_gains)} VGains')
    

def parse_paf(filexml): 
    tree = ET.parse(filexml) 
    root = tree.getroot()
    
    result = {}
    name = root.find('Name').text
    manufacturer = (root.find('Manufacturer').text or 'NONAME') if not root.find('Manufacturer') is None else 'NONAME'
    version = (root.find('Version').text or '0.0') if not root.find('Version') is None else '0.0'
    print('PAF have antenna', manufacturer, name)
    
    for p in root.iter('Pattern'):
        descr = PatternDescriptor()
        descr.name = manufacturer + ' ' + p.find('Name').text.replace(name + '\\', '')
        descr.frequency = int(float(p.find('MeasurementFrequencyMHz').text))
        descr.max_gain_db = round(float(p.find('BoresightGain').text),3)
        descr.max_gain_unit = p.find('BoresightGainUnit').text
        descr.tilt = int(p.find('ElectricalTiltDegrees').text)
        descr.beam_width = round(float(p.find('HorizontalBeamwidthDegrees').text),2)
        descr.beam_height = round(float(p.find('VerticalBeamwidthDegrees').text),2)
        descr.polarization = p.find('Polarization').text.replace('Plus','+').replace('Minus','-')
        descr.front_to_back = p.find('FrontToBackRatioDB').text
        if not p.find('Comment') is None and p.find('Comment').text:
            descr.comment = p.find('Comment').text + '; '
        descr.comment += f'V{version} Generated by {VERSION}'
        descr.file = p.find('AntennaPatternsEntryName').text
        result[descr.file] = descr
        #print(descr)
        
    return name, result


def read_pafx(filepath, save_msi=True):
    #print(zipfile.ZipFile(filepath).namelist())
    with zipfile.ZipFile(filepath) as zip:
        with zip.open('antenna.paf') as file_paf:
            antenna, dict_pap = parse_paf(file_paf)
        if not antenna:
            antenna = os.path.basename(filepath).replace('.pafx','')
        for file, descr in dict_pap.items():
            with zip.open(file) as file_pap:
                parse_pap(file_pap, descr)
    print(f'Loaded {len(dict_pap)} patterns for {antenna}')
    if (save_msi):
        dirname = os.path.dirname(filepath) or '.'
        write_msi(dirname + '/' + antenna, dict_pap)
    return antenna, dict_pap


def write_msi(folder, dict_pap): 
    if not os.path.exists(folder):
        os.makedirs(folder)
    antenna = os.path.basename(folder)
    for file,descr in dict_pap.items():
        freq_suffix = '_{:04d}'.format(descr.frequency)
        tilt_suffix = '_{:02d}'.format(descr.tilt)
        filename = folder + '/' + file.replace('.pap', '').replace(antenna + '%092','')
        if (filename.find(tilt_suffix + 'T') == -1):
            if filename.endswith(tilt_suffix):
                filename += 'T'
            else:
                filename += tilt_suffix + 'T'
        if (filename.find(freq_suffix) == -1):
            filename += freq_suffix
        filename += '.msi'
        print('Writing MSI ' + filename)
        with open(filename, 'w') as f:
            f.write(descr.msi())
            f.close()


print(VERSION)
print(COPYRIGHT)

if len(sys.argv) <= 1 or '-h' in sys.argv or '--help' in sys.argv:
    print(COMMENT)
    print(USAGE)
    exit(0)

path = sys.argv[1]
print('Searching', path)
for f in glob.glob(path):
    print('Reading PAFX', f)
    read_pafx(f, save_msi = True)
