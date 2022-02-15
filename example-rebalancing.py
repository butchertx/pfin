import pfin
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


NET_WORTH_GOAL = 25000
NUM_MONTHS_TO_GOAL = 12
MY_NAME = 'Name'
json_file = 'pinwheel_allocation.json'
bal_file = 'balance.csv'

port = pfin.Portfolio(MY_NAME, NET_WORTH_GOAL, NUM_MONTHS_TO_GOAL, 'My Portfolio', allocation_file=json_file, balance_file=bal_file)
goals_df = port.rebalance_monthly('goals.csv')
port.sunburst(['Asset Class', 'Asset Style', 'Ticker'], 'Initial Balance')
port.sunburst(['Asset Class', 'Asset Style'], 'Total Allocation %', balance=False)