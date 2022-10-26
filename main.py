import streamlit as st
import requests
import numpy as np
import pandas as pd
from numerize import numerize
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
import time
import threading

st.set_page_config(
    page_title="Live NSE Option Chain", layout="wide"
)

st.subheader("Live NSE Option Chain")

# # update every 1 mins
# st_autorefresh(interval=1 * 60 * 1000, key="graphdatarefresh")


def convert_to_thousand(arr):
    data = []
    for i in arr:
        data.append(numerize.numerize(int(i)))
    return data


def get_nifty_current_strike(price):
    res = price % 50
    if res < 25:
        return int(price - res)
    elif res >= 25:
        return int(price-res+50)


def get_bank_nifty_current_strike(price):
    res = price % 100
    if res < 50:
        return int(price - res)
    elif res >= 50:
        return int(price-res+100)


def get_nse_live_option_chain():
    # BANKNIFTY , NIFTY
    url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8'
    }

    session = requests.Session()
    request = session.get(url, headers=headers)

    cookies = dict(request.cookies)

    response = session.get(url, headers=headers, cookies=cookies).json()
    row_data = pd.DataFrame(response)

    raw_option_chain_data = pd.DataFrame(
        row_data['filtered']['data']).fillna(0)

    underlying_value = row_data['records']['underlyingValue']
    current_time = row_data['records']['timestamp']

    res = {
        'raw_option_chain_data': raw_option_chain_data,
        'current_value': int(underlying_value),
        'current_time': current_time
    }
    threading.Timer(60, get_nse_live_option_chain).start()
    return res


def build_option_chain_dataframe(raw_option_chain):
    data = []
    for i in range(0, len(raw_option_chain)):
        call_oi = call_change_oi = call_ltp = put_oi = put_change_oi = put_ltp = 0
        strike_price = raw_option_chain['strikePrice'][i]

        if(raw_option_chain['CE'][i] == 0):
            call_oi = call_change_oi = 0
        else:
            call_oi = raw_option_chain['CE'][i]['openInterest']
            call_change_oi = raw_option_chain['CE'][i]['changeinOpenInterest']
            call_ltp = raw_option_chain['CE'][i]['lastPrice']

        if(raw_option_chain['PE'][i] == 0):
            put_oi = put_change_oi = 0
        else:
            put_oi = raw_option_chain['PE'][i]['openInterest']
            put_change_oi = raw_option_chain['PE'][i]['changeinOpenInterest']
            put_ltp = raw_option_chain['PE'][i]['lastPrice']

        option_data = {
            'CALL OI': call_oi,
            'CALL CHANGE OI': call_change_oi,
            'CALL LTP': call_ltp,
            'STRIKE PRICE': strike_price,
            'PUT OI': put_oi,
            'PUT CHANGE OI': put_change_oi,
            'PUT LTP': put_ltp
        }

        data.append(option_data)

    option_chain_data = pd.DataFrame(data)
    return option_chain_data


def build_option_chain_graph_data(current_strike, option_chain):

    for_ward_data = option_chain.loc[option_chain['STRIKE PRICE']
                                     >= current_strike]
    back_ward_data = option_chain.loc[option_chain['STRIKE PRICE']
                                      < current_strike]

    for_ward_filter_data = for_ward_data[:11]
    back_ward_filter_data = back_ward_data[-10:]

    concat_for_ward_back_ward_data = pd.concat(
        [back_ward_filter_data, for_ward_filter_data])

    res = {
        'strike_price': concat_for_ward_back_ward_data['STRIKE PRICE'].values,
        'call_oi': concat_for_ward_back_ward_data['CALL OI'].values,
        'put_oi': concat_for_ward_back_ward_data['PUT OI'].values,
        'call_change_oi': concat_for_ward_back_ward_data['CALL CHANGE OI'].values,
        'put_change_oi': concat_for_ward_back_ward_data['PUT CHANGE OI'].values,
        'trim_oi_data': concat_for_ward_back_ward_data
    }

    return res


def plot_option_chain_graph(call_oi, put_oi, strike_price, current_price, current_time):
    barWidth = 0.25
    fig = plt.figure(figsize=(16, 7))

    current_strike_and_time = "Current Price: {}  Time: {}".format(
        current_price, current_time)

    plt.title(current_strike_and_time)

    # Set position of bar on X axis
    br1 = np.arange(len(call_oi))
    br2 = [x + barWidth for x in br1]

    # Make the plot
    plt.bar(br1, call_oi, color='r', width=barWidth,
            edgecolor='grey', label='Call OI')
    plt.bar(br2, put_oi,  color='g', width=barWidth,
            edgecolor='grey', label='Put OI')

    # Adding Xticks
    plt.xlabel('Strike',  fontweight='bold', fontsize=15)
    plt.ylabel('Call/Put PI', fontweight='bold', fontsize=15)
    plt.xticks([r + barWidth for r in range(len(call_oi))], strike_price)

    plt.legend()
    st.pyplot(fig)


@st.cache(suppress_st_warning=True)
def update():
    live_data = get_nse_live_option_chain()
    current_strike = get_nifty_current_strike(live_data['current_value'])
    option_chain = build_option_chain_dataframe(
        live_data['raw_option_chain_data'])

    graph_data = build_option_chain_graph_data(
        current_strike, option_chain)

    plot_option_chain_graph(graph_data['call_change_oi'], graph_data['put_change_oi'],
                            graph_data['strike_price'], live_data['current_value'], live_data['current_time'])

    plot_option_chain_graph(graph_data['call_oi'], graph_data['put_oi'],
                            graph_data['strike_price'], live_data['current_value'], live_data['current_time'])

    df = graph_data['trim_oi_data']
    st.table(df)


try:
    update()
except:
    st.write('No Record Found')
