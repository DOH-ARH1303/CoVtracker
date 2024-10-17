import argparse as ap
import os
import pandas as pd
import re
import openpyxl
import xlrd
import numpy as np
from CoV_master_file import add_to_CoVtracker

# Mounts P: drive if not already mounted
os.system("""
if [ ! -d /mnt/P ]; then
  mkdir /mnt/P
fi
if ! mountpoint -q /mnt/P; then
  sudo mount -t drvfs "P:" /mnt/P
fi
if [ ! -d /mnt/P ] || ! mountpoint -q /mnt/P; then
  echo "The P: drive was not mounted."
  exit 0
fi
""")

# Prompts user to enter the run name
run_name = input('Enter run name: ').strip()

# Variables to construct appropriate file names
# GROUP SO IT CAN BE DIFFERENT IF THE RUN NAME FORMAT IS DIFFERENT
YYMMDD = run_name[-6:]
YY = YYMMDD[:2]
MMDDYY = YYMMDD[2:] + YYMMDD[:2]
run_num = run_name[3:6]

# Absolute path to desired File System Objects (fso)
path = os.path.join('/mnt/P', 'EHSPHL', 'PHL', 'MICRO', 'COVID19', 'Sequencing', 'Bioinformatics - STAY OUT!', f'20{YY} Analysis Files')
csv_path = os.path.join('/mnt/P', 'EHSPHL', 'PHL', 'MICRO', 'COVID19', 'Sequencing', 'Bioinformatics - STAY OUT!')

# I just like this line of code. I refuse to get rid of it entirely :)
  # if any(file.__contains__('dash') for file in os.listdir(run_path)):

# Returns filenames that contain query
def whichfile(pathway, query):
    with os.scandir(pathway) as dirs:
        for entry in dirs:
            if query in entry.name:
                #print(entry.name)
                fso=entry.name
                break
    return fso

parser = ap.ArgumentParser()
# Grabbing run directory
try:
  run_dir = whichfile(path, run_name)
except:
  parser.add_argument('--run', '-r', help = f'Enter pathway for run directory.')
  args = parser.parse_args()
  run_dir = args

run_path = f'{path}/{run_dir}'

# Grabbing Excel/text files
try:
  dash_file = whichfile(run_path,'dash')
  dash_xl = pd.ExcelFile(f'{run_path}/{dash_file}')
except:
  parser.add_argument('--dash', '-d', help = f'Enter pathway for dashboard_{MMDDYY}.xlsx file.')
  args = parser.parse_args()
  dash_xl = pd.ExcelFile(args)
try:
  tr_file = whichfile(run_path,'terra_all')
  tr_xl = pd.ExcelFile(f'{run_path}/{tr_file}')
except:
  parser.add_argument('--tr', '-t', help = 'Enter pathway for terra_all.xlsx file.')
  args = parser.parse_args()
  tr_xl = pd.ExcelFile(args)

  # xl.sheet_names returns a list of all sheets in the excel file
  # parse converts sheet(s) to dataframe(s) (df)
tr_df = tr_xl.parse(sheet_name = 0)
dash_df = dash_xl.parse(sheet_name = 0)

# Changed column names to match final qc file format
tr_df.rename(columns = {f'entity:{run_name}_id': 'SpecimenId'}, inplace=True)

# Function to pull WA#s in tr_df
def convert_to_wa(x):
  if 'WA' in x:
    return x[:9]
  elif 'neg' in x.lower():
    return f'{x}'
  else:
    return 'Unknown: ' + x
wa = tr_df['SpecimenId'].apply(convert_to_wa)
tr_df['SpecimenId'] = wa

# Merge dash_df with tr_df based on SpecimenId -> gets SpecimenId and Seq ID in same df
master_df = dash_df.merge(tr_df, on = 'SpecimenId', how = 'outer')

# Makes dataFrame with only the columns necessary to make the qc file and check the negative control
flag_df = master_df.loc[:, ['SpecimenId', 'Seq ID', 'percent_reference_coverage','sc2_s_gene_percent_coverage', 'vadr_flag']]

# Add Resequencing column to flag_df and add values based on vadr_flag values
conditions = [flag_df['vadr_flag'] == 'FLAGGED', flag_df['vadr_flag'].isnull(), flag_df['vadr_flag'] == 'PASS']
categories = ['Frameshift', 'QC', '']
flag_df.loc[:, 'Resequence'] = np.select(conditions, categories, default='Unknown')

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
    ELB = 'PASS'
elif 5 < float(neg_pct_ref) <= 10:
  if sgene_pct == 'NaN' or float(sgene_pct) <= 0:
    ELB = 'PASS'
  else:
    print('The negative control has a % reference coverage between 5% and 10%. There is also a percent coverage for the S gene. The run has failed and all samples will need to be resequenced.')
    ELB = 'FAIL'
else:
  approval = input(f'The negative control has a reference coverage >10%. Please contact a bioinformatition before continuing.\nDid a bioinformatician approve the run? (yes/no): ').strip().casefold()
  if approval.find('yes') != -1:
    ELB = 'PASS'
  elif approval.find('no') != -1:
    ELB = 'FAIL'
    print('The run has failed. All samples will need to be re-sequenced.')

# A list of columns to append to CoVtracker file
master_columns = ['SpecimenId', 'Seq ID', 'vadr_flag', 'percent_reference_coverage', 'sc2_s_gene_percent_coverage', 'number_N', 'pango_lineage', 'pango_lineage_expanded']

# Function to make a df that contains all the archive info needed for sequencing samples and append the df to a CoVtracker.csv.zip file
add_to_CoVtracker(master_columns, master_df, f'{run_name}', csv_path, f'{ELB}')

# Search for _qc.xlsx file in run_name directory and prompt user to make decisions if the file already exists
if ELB == 'PASS':  
  with os.scandir(f'{run_path}') as dirs:
    for entry in dirs:
      if '_qc.xlsx' in entry.name:
        overwrite = input(f'A file titled CoV{run_num}_qc.xlsx already exists. Would you like to overwrite the existing file? (yes/no): ').strip().casefold()
        if overwrite.find('yes') != -1: 
          reseq_df.to_excel(f'{run_path}/CoV{run_num}_qc.xlsx', index=False)
        elif overwrite.find('no') != -1:
          copy = input(f"This program is only set to make one copy of the file, which is saved as run{run_num}_qc_copy.xlsx. In order to generate the file run{run_num}_qc_copy.xlsx for the first time or overwrite the run{run_num}_qc_copy.xlsx file, type 'copy'. Otherwise, type 'quit'. ").strip().casefold()
          if copy.find('copy') != -1:
            reseq_df.to_excel(f'{run_path}/CoV{run_num}_qc_copy.xlsx', index=False)
          elif copy.find('quit') != -1:
            print("This program is only set to either overwrite the existing file or make a copy of the file. Since you do not want to do either, the program will not be generating anything. Feel free to rerun the program if you decide to overwrite or make a copy of the existing file(s)." )
            exit()
      else:
        reseq_df.to_excel(f'{run_path}/CoV{run_num}_qc.xlsx', index=False)
else: exit()