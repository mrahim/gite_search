# TODO read csvs and filter according to distance and number of beds
import pandas as pd
import numpy as np
import sys

# set region
regions = ['bourgogne', 'champagne-ardenne', 'pays-de-loire', 'centre',
           'picardie', 'haute-normandie', 'basse-normandie']
region = 'bourgogne' if sys.argv[-1] not in regions else sys.argv[-1]
print('-> %s' % region)

fname = 'results/gites_%s.csv' % region
df = pd.read_csv(fname)

max_duration = 9000.
min_beds = 20
max_beds = 30

short_list = df[(df.n_beds >= min_beds) & (df.duration_value <= max_duration)]
short_list = short_list[short_list.n_beds <= max_beds]


short_list.to_csv('results/short_list_%s.csv' % region, index=False)
