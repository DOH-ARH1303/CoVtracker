# Change terra_final back to terra_reseq when done
import argparse as ap
import os
import pandas as pd
import re
import openpyxl
import xlrd
import numpy as np

run_name = input('Enter run name: ').strip()

# Returns None if run_name is not correct format
# Change to make instrument name more variable
nextseq = re.search(r'CoV\d{3}[-_]VH00(442|453)[-_]\d{6}', run_name)
miniseq = re.search(r'CoV\d{3}[-_]2068[-_]\d{6}', run_name)

# Gives user 5 chances to enter run_name in correct format
x = 1
while x <= 4:
  if nextseq is None and miniseq is None and x <= 3:
    run_name = input('The run name was not in the correct format. Please enter the run name (CoVXXX-VH00XXX-YYMMDD or CoVXXX-2068-YYMMDD): ').strip()
    x += 1
    nextseq = re.search(r'CoV\d{3}[-_]VH00(442|453)[-_]\d{6}', run_name)
    miniseq = re.search(r'CoV\d{3}[-_]2068[-_]\d{6}', run_name)
  elif nextseq is None and miniseq is None and x > 3:
    print('Run name is not in the correct format. Please check the run name before re-running the program.')
    exit()
  else:
    break

if run_name.find('_') != -1:
  run_name.replace('_', '-')
else:
  pass

# Variables to construct appropriate file names
YYMMDD = run_name[-6:]
YY = YYMMDD[:2]
MMDDYY = YYMMDD[2:] + YYMMDD[:2]
run_num = run_name[3:6]

# Path to desired files
path = '../../mnt/P/EHSPHL/PHL/MICRO/COVID19/Sequencing/'Bioinformatics - STAY out!'/20{YY} Analysis Files/{run_name}'

# Grabbing Excel/text files
parser = ap.ArgumentParser()
try:
  dash_xl = pd.ExcelFile(f'{path}/dashboard_{MMDDYY}.xlsx')
except:
  parser.add_argument('dash', help = f'Enter pathway for dashboard_{MMDDYY}.xlsx file')
  args = parser.parse_args()
  dash_xl = pd.ExcelFile(args)
try:
  tr_xl = pd.ExcelFile(f'{path}/{run_name}_terra_final.xlsx')
except:
  parser.add_argument('tr', help = 'Enter pathway for terra_reseq.xlsx file')
  args = parser.parse_args()
  tr_xl = pd.ExcelFile(args)

  # xl.sheet_names returns a list of all sheets in the excel file
  # parse converts sheet(s) to dataframe(s) (df)
tr_df = tr_xl.parse(sheet_name = 0)
dash_df = dash_xl.parse(sheet_name = 0)

# Changed column names to match final qc file format
tr_df.rename(columns = {f'entity:{run_name}_id': 'SpecimenId'}, inplace=True)

# Change to search for regex for 'WA' and 'neg'
# Function to pull WA#s in tr_df
def convert_to_wa(x):
  if x.find('WA') != -1:
    return x[:9]
  elif x.casefold().find(r'(?i)neg\w+') != -1:
    return 'Negative'
  else:
    return 'Unknown: ' + x
wa = tr_df['SpecimenId'].apply(convert_to_wa)
tr_df['SpecimenId'] = wa

# Merge dash_df with tr_df based on SpecimenId -> gets SpecimenId and Seq ID in same df
master_df = dash_df.merge(tr_df, on = 'SpecimenId', how = 'outer')
print(master_df)
# Add run name column to master df - put in make_master function
# master_df['Run_name'] = f'{run_name}'

# Makes dataFrame with only the columns necessary to make the qc file and check the negative control
flag_df = master_df[['SpecimenId', 'Seq ID', 'percent_reference_coverage','sc2_s_gene_percent_coverage', 'vadr_flag']]

# Add Resequencing column to flag_df and add values based on vadr_flag values
conditions = [flag_df['vadr_flag'] == 'FLAGGED', flag_df['vadr_flag'].isnull(), flag_df['vadr_flag'] == 'PASS']
categories = ['Frameshift', 'QC', '']
flag_df['Resequence'] = np.select(conditions, categories, default='Unknown')
print(flag_df)

# Makes df 3 columns in order specified
flag_df = flag_df[['SpecimenId', 'Seq ID', 'Resequence']]

# Makes dataFrame with only rows containing 'Frameshift' or 'QC' in the 'Resequencing' column
reseq_df = flag_df.loc[(flag_df['Resequence'] == 'Frameshift') | (flag_df['Resequence'] == 'QC')]
# Keeps all the rows not conatining (~) 'neg' in the SpecimenId column
reseq_df = reseq_df[~reseq_df.SpecimenId.str.contains(r'(?i)neg\w+')]

# Checks negative control
neg_df = tr_df[tr_df.SpecimenId.str.contains(r'(?i)neg\w+')]

neg_pct_ref = neg_df['percent_reference_coverage'].to_string(index=False)
sgene_pct = neg_df['sc2_s_gene_percent_coverage'].to_string(index=False)

if neg_pct_ref == 'NaN' or float(neg_pct_ref) <= 5:
  if sgene_pct == 'NaN' or float(sgene_pct) <= 1:
    pass
elif 5 < float(neg_pct_ref) <= 10:
  if sgene_pct == 'NaN' or float(sgene_pct) <= 0:
    pass
  else:
    print('The negative control has a % reference coverage between 5% and 10%. There is also a percent coverage for the S gene. The run has failed and all samples will need to be resequenced.')
    exit()
else:
  approval = input(f'The negative control has a reference coverage >10%. Please contact a bioinformatition before continuing.\nDid a bioinformatician approve the run? (yes/no): ').strip().casefold()
  if approval.find('yes') != -1:
    pass
  elif approval.find('no') != -1:
    print('The run has failed. All samples will need to be re-sequenced.')
    exit()

# Search for _qc.xlsx file in run_name directory and prompt user to make decisions if the file already exists
with os.scandir(f'{path}') as dirs:
  for entry in dirs:
    if '_qc.xlsx' in entry.name:
      overwrite = input(f'A file titled CoV{run_num}_qc.xlsx already exists. Would you like to overwrite the existing file? (yes/no): ').strip().casefold()
      if overwrite.find('yes') != -1: 
        reseq_df.to_excel(f'{path}/CoV{run_num}_qc.xlsx', index=False)
      elif overwrite.find('no') != -1:
        copy = input(f"This program is only set to make one copy of the file, which is saved as run{run_num}_qc_copy.xlsx. In order to generate the file run{run_num}_qc_copy.xlsx for the first time or overwrite the run{run_num}_qc_copy.xlsx file, type 'copy'. Otherwise, type 'quit'. ").strip().casefold()
        if copy.find('copy') != -1:
          reseq_df.to_excel(f'{path}/CoV{run_num}_qc_copy.xlsx', index=False)
        elif copy.find('quit') != -1:
          print("This program is only set to either overwrite the existing file or make a copy of the file. Since you do not want to do either, the program will not be generating anything. Feel free to rerun the program if you decide to overwrite or make a copy of the existing file(s)." )
          exit()
    else:
      reseq_df.to_excel(f'{path}/CoV{run_num}_qc.xlsx', index=False)

# A list of columns to append to CoVtracker file
master_columns = ['SpecimenId', 'Seq ID', 'vadr_flag', 'percent_reference_coverage', 'sc2_s_gene_percent_coverage', 'number_N', 'pango_lineage', 'pango_lineage_expanded']
