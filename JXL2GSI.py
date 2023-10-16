import xml.etree.ElementTree as ET
import pandas as pd
import sys
import math
import os

## Opening JXL/XML file
tree = ET.parse(sys.argv[1])
root = tree.getroot()

data_point = []
data_station = []
data_target = []

##Extracting POINT related data
for point_record in root.findall('.//PointRecord'):
    data_point.append({
        'ID': point_record.get('ID'),
        'TimeStamp': point_record.get('TimeStamp'),
        'PointName': point_record.find('Name').text if point_record.find('Name') is not None else '',
        'HorizontalCircle': point_record.find('Circle/HorizontalCircle').text if point_record.find('Circle/HorizontalCircle') is not None else 0 ,
        'VerticalCircle': point_record.find('Circle/VerticalCircle').text if point_record.find('Circle/VerticalCircle') is not None else 0,
        'EDMDistance': point_record.find('Circle/EDMDistance').text if point_record.find('Circle/EDMDistance') is not None else 0,
        'StationID': point_record.find('StationID').text if point_record.find('StationID') is not None else '',
        'TargetID': point_record.find('TargetID').text if point_record.find('TargetID') is not None else '',
        'Face': point_record.find('Circle/Face').text if point_record.find('Circle/Face') is not None else '',
        'Pressure': point_record.find('Pressure').text if point_record.find('Pressure') is not None else '',
        'Temperature': point_record.find('Temperature').text if point_record.find('Temperature') is not None else '',
        'North': point_record.find('ComputedGrid/North').text if point_record.find('ComputedGrid/North') is not None else '',
        'East': point_record.find('ComputedGrid/East').text if point_record.find('ComputedGrid/East') is not None else '',
        'Elevation': point_record.find('ComputedGrid/Elevation').text if point_record.find('ComputedGrid/Elevation') is not None else '',
    })
df_point = pd.DataFrame(data_point)

##Extracting STATION measurments data
for station_record in root.findall('.//StationRecord'):
    data_station.append({
        'ID': station_record.get('ID'),
        'TimeStamp': station_record.get('TimeStamp'),
        'StationName': station_record.find('StationName').text,
        'InstrumentHeight': station_record.find('RawTheodoliteHeight/MeasuredHeight').text if station_record.find('RawTheodoliteHeight/MeasuredHeight') is not None else '',
    })
df_station = pd.DataFrame(data_station)
df_station=df_station.sort_values(by=['StationName','TimeStamp'],ascending=[False,False])
df_station=df_station.drop_duplicates(subset=['StationName'],ignore_index=True)
df_station['InstrumentHeight'] = pd.to_numeric(df_station['InstrumentHeight']).round(3)

##Extracting TARGET measurments data
for target_record in root.findall('.//TargetRecord'):
    data_target.append({
        'ID': target_record.get('ID'),
        'PrismConstant': target_record.find('PrismConstant').text if target_record.find('PrismConstant') is not None else '',
        'TimeStamp': target_record.get('TimeStamp'),
        'TargetHeight': target_record.find('TargetHeight').text if target_record.find('TargetHeight') is not None else '',
    })
df_target = pd.DataFrame(data_target)
df_target['TargetHeight'] = pd.to_numeric(df_target['TargetHeight']).round(3)

##Joining station and target data
df_merged = df_point.merge(df_station[['ID', 'StationName', 'InstrumentHeight']], how='left', left_on='StationID', right_on='ID')
df_merged = df_merged.merge(df_target[['ID', 'TargetHeight','PrismConstant']], how='left', left_on='TargetID', right_on='ID')

##Filtering the extracted data
df_merged = df_merged.filter(['StationName', 'InstrumentHeight', 'PointName','TargetHeight', 'Face', 'HorizontalCircle','VerticalCircle','EDMDistance','PrismConstant','Pressure', 'Temperature','EDMDistanceCorr','East','North','Elevation'])
df_merged = df_merged.dropna()

#Changing data to the right amount of decimals
df_merged['HorizontalCircle'] = pd.to_numeric(df_merged['HorizontalCircle'])
df_merged['HorizontalCircle'] = df_merged['HorizontalCircle'].round(5)
df_merged['VerticalCircle'] = pd.to_numeric(df_merged['VerticalCircle'])
df_merged['VerticalCircle'] = df_merged['VerticalCircle'].round(5)
df_merged['EDMDistance'] = pd.to_numeric(df_merged['EDMDistance'])
df_merged['EDMDistance'] = df_merged['EDMDistance'].round(3)
df_merged['PrismConstant'] = pd.to_numeric(df_merged['PrismConstant'])
df_merged['Pressure'] = pd.to_numeric(df_merged['Pressure'])
df_merged['Temperature'] = pd.to_numeric(df_merged['Temperature'])
df_merged['North'] = pd.to_numeric(df_merged['North'])
df_merged['North'] = df_merged['North'].round(3)
df_merged['East'] = pd.to_numeric(df_merged['East'])
df_merged['East'] = df_merged['East'].round(3)
df_merged['Elevation'] = pd.to_numeric(df_merged['Elevation'])
df_merged['Elevation'] = df_merged['Elevation'].round(3)

##Applying EDM distance corrections
J=273.64570458809
N=79.170232716506
df_merged['PPM']=(J-((N*df_merged['Pressure'])/(273.16+df_merged['Temperature'])))
df_merged['EDMDistanceCorr']=df_merged['EDMDistance']+(df_merged['EDMDistance']*df_merged['PPM']*0.000001)+df_merged['PrismConstant']

##Converting 2nd face direction measurements to the 1st face
mask1 = ((df_merged['Face'] == 'Face2') & 
        (df_merged['VerticalCircle'] > 180))

mask2 = ((df_merged['Face'] == 'Face2') & 
        (df_merged['HorizontalCircle'] < 180))
        
mask3 = ((df_merged['Face'] == 'Face2') & 
        (df_merged['HorizontalCircle'] > 180))

df_merged.loc[mask2, 'HorizontalCircle'] = df_merged['HorizontalCircle'] + 180
df_merged.loc[mask1, 'VerticalCircle'] = 360 - df_merged['VerticalCircle']
df_merged.loc[mask3, 'HorizontalCircle'] = df_merged['HorizontalCircle'] - 180

df_merged = df_merged[(df_merged['HorizontalCircle'] != 0) | (df_merged['VerticalCircle'] != 0) | (df_merged['EDMDistance'] != 0)]

##Converting DD2DMS
# df_merged['HzDeg'] = abs(df_merged['HorizontalCircle']).astype('int64')
# df_merged['HzMin'] = (df_merged['HorizontalCircle']-df_merged['HzDeg'])*60
# df_merged['HzMin'] = df_merged['HzMin'].astype('int64')
# df_merged['HzSec'] = ((df_merged['HorizontalCircle']-df_merged['HzDeg'])- (df_merged['HzMin']/60))*3600
# df_merged['HzSec'] = df_merged['HzSec'].round()

# df_merged['VDeg'] = abs(df_merged['VerticalCircle']).astype('int64')
# df_merged['VMin'] = (df_merged['VerticalCircle']-df_merged['VDeg'])*60
# df_merged['VMin'] = df_merged['VMin'].astype('int64')
# df_merged['VSec'] = ((df_merged['VerticalCircle']-df_merged['VDeg'])- (df_merged['VMin']/60))*3600
# df_merged['VSec'] = df_merged['VSec'].round()

#df_merged.to_csv('measurements.csv', index=False)

##Creating averaged measurements for every station
keys = ['StationName', 'InstrumentHeight', 'PointName','TargetHeight']
average_meas = df_merged.groupby(keys)[['East', 'North','Elevation','HorizontalCircle', 'VerticalCircle', 'EDMDistanceCorr']].mean()

##Converting DD2DMS
# average_meas['HzDeg'] = abs(average_meas['HorizontalCircle']).astype('int64')
# average_meas['HzMin'] = (average_meas['HorizontalCircle']-average_meas['HzDeg'])*60
# average_meas['HzMin'] = average_meas['HzMin'].astype('int64')
# average_meas['HzSec'] = ((average_meas['HorizontalCircle']-average_meas['HzDeg'])- (average_meas['HzMin']/60))*3600
# average_meas['HzSec'] = average_meas['HzSec'].round()

# average_meas['VDeg'] = abs(average_meas['VerticalCircle']).astype('int64')
# average_meas['VMin'] = (average_meas['VerticalCircle']-average_meas['VDeg'])*60
# average_meas['VMin'] = average_meas['VMin'].astype('int64')
# average_meas['VSec'] = ((average_meas['VerticalCircle']-average_meas['VDeg'])- (average_meas['VMin']/60))*3600
# average_meas['VSec'] = average_meas['VSec'].round()


#print(average_meas)
average_meas.to_csv('measurements_average.csv', index=True)
average_readin = pd.read_csv('measurements_average.csv')
#print(average_readin)

##Converting data type to string and changing the to the right amount of decimals
average_readin['StationName'] = average_readin['StationName'].astype(str)
average_readin['PointName'] = average_readin['PointName'].astype(str)
average_readin['InstrumentHeight'] = average_readin['InstrumentHeight'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['InstrumentHeight'] = average_readin['InstrumentHeight'].str.replace('.','',regex=False)
average_readin['East'] = average_readin['East'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['East'] = average_readin['East'].str.replace('.','',regex=False)
average_readin['North'] = average_readin['North'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['North'] = average_readin['North'].str.replace('.','',regex=False)
average_readin['Elevation'] = average_readin['Elevation'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['Elevation'] = average_readin['Elevation'].str.replace('.','',regex=False)
average_readin['TargetHeight'] = average_readin['TargetHeight'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['TargetHeight'] = average_readin['TargetHeight'].str.replace('.','',regex=False)  
average_readin['HorizontalCircle'] = average_readin['HorizontalCircle'].astype(str).apply(lambda x: '{:.4f}'.format(float(x)))
average_readin['HorizontalCircle'] = average_readin['HorizontalCircle'].str.replace('.','',regex=False)
average_readin['VerticalCircle'] = average_readin['VerticalCircle'].astype(str).apply(lambda x: '{:.4f}'.format(float(x)))
average_readin['VerticalCircle'] = average_readin['VerticalCircle'].str.replace('.','',regex=False)
average_readin['EDMDistanceCorr'] = average_readin['EDMDistanceCorr'].astype(str).apply(lambda x: '{:.3f}'.format(float(x)))
average_readin['EDMDistanceCorr'] = average_readin['EDMDistanceCorr'].str.replace('.','',regex=False)
#print(average_readin)

#Creating a copy of dataset for converting into GSI format
gsi_measurements = average_readin.copy()


##Converting station and target measurements into specific GSI datablock structure
for index, row in gsi_measurements.iterrows():
    gsi_measurements.at[index, 'StationName'] = '*110' + str(index).zfill(3) + '+' + str(row['StationName']).zfill(16)
    gsi_measurements.at[index, 'East'] = '84..00'+ '+' + str(row['East']).zfill(16)
    gsi_measurements.at[index, 'North'] = '85..00'+ '+' + str(row['North']).zfill(16)
    gsi_measurements.at[index, 'Elevation'] = '86..00'+ '+' + str(row['Elevation']).zfill(16)
    gsi_measurements.at[index, 'PointName'] = '*110' + str(index).zfill(3) +'+' + str(row['PointName']).zfill(16)
    gsi_measurements.at[index, 'HorizontalCircle'] = '21.323'+ '+' + str(row['HorizontalCircle']).zfill(16)
    gsi_measurements.at[index, 'VerticalCircle'] = '22.323'+ '+' + str(row['VerticalCircle']).zfill(16)
    gsi_measurements.at[index, 'EDMDistanceCorr'] = '31.310'+ '+' + str(row['EDMDistanceCorr']).zfill(16)
    gsi_measurements.at[index, 'TargetHeight'] = '87..10'+ '+' + str(row['TargetHeight']).zfill(16)
    gsi_measurements.at[index, 'InstrumentHeight'] = '88..10'+ '+' + str(row['InstrumentHeight']).zfill(16)

# Iterate over the related target data
gsi_measurements_row = []
prev_station_name = None
for _, target_row in gsi_measurements.iterrows():
    # Print the target data
    if target_row['StationName'][-15:] != prev_station_name:
        gsi_measurements_row.append(str(target_row['StationName']) + ' ' + str(target_row['InstrumentHeight']) + ' ' + str(target_row['North']) + ' ' + str(target_row['East']) + ' ' + str(target_row['Elevation']) + '\n')
    gsi_measurements_row.append(str(target_row['PointName']) + ' ' + str(target_row['HorizontalCircle']) + ' ' + str(target_row['VerticalCircle']) + ' ' + str(target_row['EDMDistanceCorr']) + ' ' + str(target_row['TargetHeight']) + ' ' + '\n')
    prev_station_name = target_row['StationName'][-15:]

##Write measurements into a new GSI file
file_name = os.path.basename(sys.argv[1])
file_name = os.path.splitext(file_name)[0]
file_name = file_name + ".gsi"

with open(file_name, 'w') as file:
    for item in gsi_measurements_row:
        file.write(str(item))