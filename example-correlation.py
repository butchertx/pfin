import pfin
import price_data
import json
import pandas as pd
import seaborn as sn
import matplotlib.pyplot as plt

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

json_file = 'pinwheel_allocation.json'
with open(json_file) as file:
    data = json.load(file)

allo = pfin.AssetAllocation(json_data=data)
print(allo)

allo_df = allo.dataframe()
print(allo_df.head(20))

tickers = ['FSKAX', 'FIENX', 'FXNAX', 'VNQ', 'BTC-USD']
ticker_data = price_data.compile_ticker_data(tickers, already_downloaded=False).dropna()
corrMatrix = ticker_data.corr()
sn.heatmap(corrMatrix, annot=True)

monthly_corr = ticker_data.rolling('300D').corr()[301*len(tickers):]
corr_series = []
for idx, t1 in zip(range(len(tickers)), tickers):
    for t2 in tickers[:idx]:
        corr_series.append(monthly_corr.query('ilevel_1 == @t2').droplevel(1).rename(columns={t1: t1 + '-' + t2})[t1 + '-' + t2])

corr_full = pd.concat(corr_series, axis=1)
corr_full.plot()
plt.show()


