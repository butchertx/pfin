'''
Scrape data for tickers to look at correlations and test allocation strategies
'''

from selenium import webdriver
import os
import shutil
import time
from dotenv import load_dotenv
import pandas as pd


def retrieve_yahoo_data(url, data_path, filename):
    load_dotenv()
    chromedriver = os.environ['CHROMEDRIVER']
    chrome_options = webdriver.ChromeOptions()
    prefs = {'download.default_directory': data_path}
    # chrome_options.add_argument("--headless")
    chrome_options.add_experimental_option('prefs', prefs)
    driver = webdriver.Chrome(chromedriver, chrome_options=chrome_options)
    driver.get(url)

    filepath = os.path.join(data_path, filename)
    if os.path.isfile(filepath):
        os.remove(filepath)

    time.sleep(2)
    driver.find_element_by_xpath('//*[@id="Col1-1-HistoricalDataTable-Proxy"]/section/div[1]/div[1]/div[1]/div/div/div/span').click()
    driver.find_element_by_xpath('//*[@id="dropdown-menu"]/div/ul[2]/li[4]/button').click()
    time.sleep(2)
    driver.find_element_by_xpath('//*[@id="Col1-1-HistoricalDataTable-Proxy"]/section/div[1]/div[2]/span[2]/a/span').click()
    time.sleep(2)
    driver.quit()

    if not os.path.isfile(filepath):
        # check and see if the file accidentally went to the global default download directory
        default_dl_file = os.path.join(os.environ['DEFAULT_DOWNLOAD_PATH'], filename)
        if os.path.isfile(default_dl_file):
            shutil.copyfile(default_dl_file, filepath)
        else:
            raise FileNotFoundError('Error finding ticker data file. Set the DEFAULT_DOWNLOAD_PATH in your .env file to Chrome\'s default download directory')

    return pd.read_csv(filepath)


def retrieve_ticker_data(ticker, source='Yahoo Finance'):
    data_path = './ticker_data/'
    try:
        os.mkdir(data_path)
    except OSError:
        print('Ticker data directory already exists.')

    if source == 'Yahoo Finance':
        url = 'https://finance.yahoo.com/quote/' + ticker + '/history?p=' + ticker
        ticker_data = retrieve_yahoo_data(url, data_path, ticker + '.csv')

    else:
        raise NotImplementedError('Only source available is Yahoo Finance')

    return ticker_data


def compile_ticker_data(tickers, already_downloaded=True, translate=False):
    if not already_downloaded:
        for t in tickers:
            retrieve_ticker_data(t)

    series_list = []
    for t in tickers:
        filename = os.path.join('./ticker_data/', t + '.csv')
        t_data = pd.read_csv(filename)
        t_data['Date'] = pd.to_datetime(t_data['Date'], infer_datetime_format=True)
        series_list.append(t_data[['Date', 'Adj Close']].set_index('Date').rename(columns={'Adj Close': t}))

    return pd.concat(series_list, axis=1)
