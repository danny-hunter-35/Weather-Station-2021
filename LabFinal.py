#################################################
# File: LabFinal.py
# Version 1.0.0
# Author: Danny Hunter
# Description:  
#   This program reads in raw station data; adds wind chill values to the data;
#   performs quality assurance tests on the data;
#   and creates formatted daily files, a summary report, and a png image containing
#   a graph of the wind speed and gusts along with a histogram of the wind gusts.
# Inputs: 
#  * CSV formatted raw data file from CR300 series datalogger.
#  * settings.yaml file  
# 
# Outputs: 
#  * CSV formatted daily files (quality assured)
#  * Summary report file
#  * PNG image containing a wind speed/gust graph and a wind gusts histogram
#
#################################################  

# import the needed pandas package
import pandas as pd
import numpy as np
import matplotlib as mpl 
import matplotlib.pyplot as plt
import yaml
from datetime import date, datetime, timedelta 

# Constants
settings_file = ".\settings.yaml"

# Wind chill function
def wind_chill(temperature, wind_speed):
     """ Calculate paycheck     
     :temperature: Air temperature (in °C)    
     :wind_speed: (m/s) 
     :return: Wind chill ("real feel")    
     """    
     w_chill = np.real(13.12 + (0.6215*temperature) - 11.37*(pow((wind_speed*3.6),0.16))
     + 0.3965*temperature*(pow((wind_speed*3.6),0.16)))
     return w_chill

#### Main Program ####     
if __name__ == "__main__": 
    print("** Begin Program **")
    with open(settings_file, 'r') as reader:
        settings = yaml.safe_load(reader)
    settings['start_datetime'] = datetime.strptime(settings['start_datetime'], '%Y-%m-%d %H:%M')
    settings['end_datetime'] = datetime.strptime(settings['end_datetime'], '%Y-%m-%d %H:%M')
    
    # read in the csv data file (automatically formatted to a pandas data frame)
    print("Read in raw data file...") 
    stationData = pd.read_csv(settings['data_file'], skiprows=(0, 2, 3)).set_index("TIMESTAMP")
    
    # construct an empty data frame 
    print("Set up blank dataframe...")
    emptyDF = pd.DataFrame(index = pd.date_range(start=(settings['start_datetime']), end=(settings['end_datetime']), 
    freq='5min'), 
    columns=['RECORD','TAIR','RELH','SRAD','WSPD','WMAX','WDIR','RAIN','BATV']).rename_axis('TIMESTAMP')
    
    # merge the two data frames
    print("Merge raw data into blank dataframe...") 
    rawMergedData = stationData.combine_first(emptyDF)
    rawMergedData.reset_index(inplace = True)
    rawMergedData['TIMESTAMP'] = pd.to_datetime(rawMergedData['TIMESTAMP'])
    
    #Add the wind chill column (empty for now)
    rawMergedData['CHIL'] = wind_chill(rawMergedData['TAIR'], rawMergedData['WSPD'])
    
    # create a copy of the merged data frame to modify
    qaData = rawMergedData.copy()
    
    # #quality assurance tests (replaces bad data with -998)
    qaData['TAIR'] = qaData.apply(lambda row: -998 
                                if (((row['TAIR']) > settings['variable']['tair']['qa']['high_limit']) or
                                    (row['TAIR']) < settings['variable']['tair']['qa']['low_limit'])
                                else row['TAIR'], axis = 1)
    qaData['RELH'] = qaData.apply(lambda row: -998 
                                if (((row['RELH']) > settings['variable']['relh']['qa']['high_limit']) or
                                    (row['RELH']) < settings['variable']['relh']['qa']['low_limit'])
                                else row['RELH'], axis = 1)
    qaData['SRAD'] = qaData.apply(lambda row: -998 
                                if (((row['SRAD']) > settings['variable']['srad']['qa']['high_limit']) or
                                    (row['SRAD']) < settings['variable']['srad']['qa']['low_limit'])
                                else row['SRAD'], axis = 1)
    qaData['WSPD'] = qaData.apply(lambda row: -998 
                                if (((row['WSPD']) > settings['variable']['wspd']['qa']['high_limit']) or
                                    (row['WSPD']) < settings['variable']['wspd']['qa']['low_limit'])
                                else row['WSPD'], axis = 1)
    qaData['WMAX'] = qaData.apply(lambda row: -998 
                                if (((row['WMAX']) > settings['variable']['wmax']['qa']['high_limit']) or
                                    (row['WMAX']) < settings['variable']['wmax']['qa']['low_limit'])
                                else row['WMAX'], axis = 1)
    qaData['CHIL'] = qaData.apply(lambda row: -998 
                                if ((row['CHIL']) > settings['variable']['chil']['qa']['high_limit'] or
                                    (row['CHIL']) < settings['variable']['chil']['qa']['low_limit'] or
                                    row['TAIR'] == -998 or
                                    row['WSPD'] == -998)
                                else row['CHIL'], axis = 1)
    
    # replace any empty "NaN" values with -999
    qaData.fillna(-999, inplace = True)
    
    # Output data files    
    print("Output data files...") 
    curr_date = settings['start_datetime']    
    while curr_date <= settings['end_datetime']:       
        print(curr_date) 
        
        # Set filename
        filename="{}NWC0_{:04d}{:02d}{:02d}.dat".format(settings['output_file_path'],curr_date.year, curr_date.month, curr_date.day)        
        
        # Determine start and end of the current day         
        start_period = datetime(curr_date.year,curr_date.month,curr_date.day,0,0)         
        end_period = datetime(curr_date.year,curr_date.month,curr_date.day,23,55)  
        
        # Write out dataframe subset        
        qaData[(qaData['TIMESTAMP']>=start_period) & (qaData['TIMESTAMP']<=end_period)].to_csv(filename, index=False)        
       
        # Increment date         
        curr_date += timedelta(days=1)
    
    # Make a copy of the qaData to use for the purpose of statistical calculations
    statData = qaData.copy()
    
    # Change the -999's and -998's to nan's for statistical calculations
    statData.replace([-999, -998], np.nan, inplace = True)
    
    ## Write the statistics report
    print("Output report files...")
    
    # Create the file name and file itself
    filename="{}NWC0_REPORT_{:04d}{:02d}{:02d}_{:04d}{:02d}{:02d}.txt".format(settings['output_file_path'], 
      settings['start_datetime'].year, settings['start_datetime'].month, settings['start_datetime'].day, 
      settings['end_datetime'].year, settings['end_datetime'].month, settings['end_datetime'].day)
    file = open(filename, 'w')
    # Header info
    file.write("Statistics Report\nInput file: " + settings['data_file'] + "\nOutput Data:\n")
    # Air temp and wind speed formatted to be over their respective max min and mean columns
    file.write("{:>81}{:5}{}\n".format("Air Temperature (C)", "", "Wind Speed (m/s)"))
    # Setting up the columns
    file.write("{:^19}{:<22}{:<21}{:7}{:7}{:10}{:7}{:7}{:7}\n".format
                ("File/day", "Missing Observations", "Precipitation (mm)", 
                "Max", "Min", "Mean", "Max", "Min", "Mean"))
    
    curr_date = settings['start_datetime']     
    while curr_date <= settings['end_datetime']:        
        print(curr_date) 
        
        # Determine start and end of the current day       
        start_period = datetime(curr_date.year,curr_date.month,curr_date.day,0,0)     
        end_period = datetime(curr_date.year,curr_date.month,curr_date.day,23,55) 
        
        # Make a subset of the dataframe      
        daily_df = statData[(statData['TIMESTAMP']>=start_period) & (statData['TIMESTAMP']<=end_period)]   
        
        # Write out the statistics for the given day
        entry_name = "NWC0_{:04d}{:02d}{:02d}.dat".format(curr_date.year, curr_date.month, curr_date.day)      
        file.write("{:^19}{:^22n}{:^21.2f}{:<7.2f}{:<7.2f}{:<10.2f}{:<7.2f}{:<7.2f}{:<7.2f}\n".format
                (entry_name, daily_df['RECORD'].isna().sum(), daily_df['RAIN'].sum(), daily_df['TAIR'].max(), 
                  daily_df['TAIR'].min(), daily_df['TAIR'].mean(), daily_df['WSPD'].max(), daily_df['WSPD'].min(),
                  daily_df['WSPD'].mean()))
                
        # Increment date         
        curr_date += timedelta(days=1)
    
    file.close()
    
    ## Graphing wind speed
    fig, (ax1, ax2) = plt.subplots(2,1,figsize=(10,12))
    
    # Plot for wind speed and gusts as a function of time
    print("Make wind speed and gust graph...") 
    ax1.plot(statData['TIMESTAMP'], statData['WSPD'], color = "green", linestyle = "--", label = "Wind Speed", zorder = 2)
    ax1.plot(statData['TIMESTAMP'], statData['WMAX'], color = "#000099", linestyle = "-", label = "Wind Gust", zorder = 2)
    ax1.grid(color='black', axis='y', linestyle=':', zorder = 1)
    ax1.set_ylim(0,3)
    ax1.set_xlabel("Time (Date and UTC hour)")
    ax1.set_ylabel("Wind Speed (m/s)")
    ax1.set_xlim([settings['start_datetime'],settings['end_datetime']+timedelta(minutes=5)])     
    ax1.xaxis.set_major_formatter(mpl.dates.DateFormatter('%m-%d-%Y \n %H:%M Z'))
    ax1.set_title("NWC0 Wind Speed and Gust")
    ax1.legend(loc = "upper left")
    
    # Histogram of the wind gusts
    print("Make wind gust histogram...")
    ax2.hist(statData['WMAX'], bins = settings['wind_histogram_bins'], edgecolor = 'black', zorder = 2) 
    ax2.grid(color='black', axis='y', linestyle=':', zorder = 1) 
    ax2.set_xlim(0,3) 
    ax2.set_ylim(0,200)
    ax2.set_xlabel("Wind Gust (m/s)")
    ax2.set_ylabel("Observations")
    ax2.set_title("Wind Gust Histogram")
    
    plt.show()
    fig.savefig(settings['output_file_path'] + settings['wind_graph_name']) 
    
    print("** End Program **") 
    # =============================================================================
    # End program
    # =============================================================================