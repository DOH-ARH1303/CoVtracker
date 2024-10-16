def add_to_CoVtracker(columns, master_df_name, run_name, CoVtracker_path, ELB_stat):
  import os
  import pandas as pd
  import numpy as np

  # Throw out an error if none of the columns are found
  # Makes a list of the columns in the master_df that could be added to CoVtracker and prints them
  CoVtracker_columns = []
  print("COLUMNS UPDATED IN THE CoVtracker")
  for column in columns:
    if column in master_df_name.columns:
      print(column)
      CoVtracker_columns.append(column)
    else:
      pass

  # Makes CoVtracker_df from the columns in master_df that we want in the CoVtracker
  if len(CoVtracker_columns) > 0:
    CoVtracker_df = master_df_name.loc[:, CoVtracker_columns]
    # Adds a run_name column and ELB_status column to CoVtracker_df
    # This function will only be called if the negative control passes, so the ELB status will automatically be 'PASS'
    CoVtracker_df.loc[:, 'run_name'] = run_name
    CoVtracker_df.loc[:, 'ELB_status'] = ELB_stat

    
    # Make condusive with zip
    current = pd.read_csv(f'{CoVtracker_path}/CoVtracker.csv.zip', compression='zip')
    
    # Mak this line check that the WA#s and 
    # if CoVtracker_df['SpecimenId'].isin(current['SpecimenId']).all():
      # merge by SpecimenId and run_name
      # if len of merged == len of CoVtracker_df, overwrite changes
          # esle, make copy
    if len(pd.merge(CoVtracker_df, current, on=['SpecimenId', 'run_name']))==len(CoVtracker_df):
      # Overwrite differences if WA#s and run name is the same in the CoVtracker_df and current
      current.update(CoVtracker_df, overwrite = True)
      updated_df = current
    else:
      updated_df = current.merge(CoVtracker_df, how='outer')
    updated_df.to_csv(f'{CoVtracker_path}/CoVtracker.csv.zip', compression='zip', index=None)
  else:
    # This might only exit the function and not the whole program
    print(f'No columns found. {run_name} not added to CoVtracker.')
    return exit()