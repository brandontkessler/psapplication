from io import StringIO, BytesIO
import pandas as pd
import numpy as np
import xlsxwriter
from datetime import datetime, timedelta
from flask import send_file


def pre_concert_fun(name, concert_dt, concert_type, tix1, tix2, tix3, tix4,
                    customer, donor):

    concert_dt = pd.to_datetime(concert_dt)

    # Stream ticketing info and concat to df called tix_data
    stream1 = StringIO(tix1.stream.read().decode("UTF8"), newline=None)
    csv_input1 = pd.read_csv(stream1, skiprows=3)

    stream2 = StringIO(tix2.stream.read().decode("UTF8"), newline=None)
    csv_input2 = pd.read_csv(stream2, skiprows=3)

    stream3 =  StringIO(tix3.stream.read().decode("UTF8"), newline=None)
    csv_input3 = pd.read_csv(stream3, skiprows=3)

    stream4 =  StringIO(tix4.stream.read().decode("UTF8"), newline=None)
    csv_input4 = pd.read_csv(stream4, skiprows=3)

    tix_data = pd.concat([csv_input1, csv_input2, csv_input3, csv_input4])

    # Stream customer info
    stream_customer = StringIO(customer.stream.read().decode('ISO-8859-1'), newline=None)
    customer_csv = pd.read_csv(stream_customer, encoding='ISO-8859-1')

    # Stream donor info
    stream_donor = StringIO(donor.stream.read().decode('ISO-8859-1'), newline=None)
    donor_csv = pd.read_csv(stream_donor, encoding='ISO-8859-1')


    # funs
    def date_conv(s):
        dates = {date:pd.to_datetime(date) for date in s.unique()}
        return s.map(dates)


    def prep_data(tix_data=tix_data):
        df = tix_data
        df['perf_dt'] = date_conv(df['perf_dt'])
        df = df.dropna(subset=['summary_cust_id'])
        df['freq'] = df.groupby('summary_cust_id')['summary_cust_id'].transform('count')
        df = df[df['freq'] <= 500]
        df = df[df['paid_amt'] > 5]
        df['seat'] = df['section']+' '+df['row']+'-'+df['seat'].map(str)
        df.loc[df.perf_dt < datetime(2016,7,1), 'fy'] = 16
        df.loc[(df.perf_dt < datetime(2017,7,1)) & (df.perf_dt >= datetime(2016,7,1)), 'fy'] = 17
        df.loc[(df.perf_dt < datetime(2018,7,1)) & (df.perf_dt >= datetime(2017,7,1)), 'fy'] = 18
        df.loc[(df.perf_dt < datetime(2019,7,1)) & (df.perf_dt >= datetime(2018,7,1)), 'fy'] = 19
        df = df[['summary_cust_id',
                 'season_desc',
                 'price_type_group',
                 'paid_amt',
                 'zone_desc',
                 'perf_dt',
                 'summary_cust_name',
                 'seat',
                 'fy']]
        return df


    def load_customer_info(df=customer_csv):
        df = df[['customer_no','combo','esal1_desc','ps_sol']]
        df.columns = ['summary_cust_id','address','salutation','solicitor']
        return df


    def load_donor_data(df=donor_csv):
        # Define donation history
        df1 = pd.DataFrame(df.groupby('summary_cust_id').gift_plus_pledge.sum().reset_index())
        df1.columns = ['summary_cust_id','donor_5yr_hist']

        return df1


    def customer_classification(df, x):
        if x == 'renew':
            df = df[((df['fy'] == df['fy'].max()) & (df['perf_dt'] <= concert_dt)) |
                    (df['fy'] == df['fy'].max() - 1)].summary_cust_id.unique()
        elif x == 'return':
            df = df[(df['fy'] == df['fy'].max() - 2) |
                    (df['fy'] == df['fy'].max() - 3)].summary_cust_id.unique()
        else:
            raise Exception('x must be renew or return only')

        df = pd.DataFrame(df)
        df.columns = ['summary_cust_id']
        df['classifier'] = 1
        return df


    def seat_finder(df):
        df = df[(df['perf_dt'] > concert_dt) &
                (df['perf_dt'] < concert_dt + timedelta(days=1))][['summary_cust_id','summary_cust_name','seat']]

        cust_info = load_customer_info()

        df = df.merge(cust_info,how='left',on='summary_cust_id')

        return df

    def segmentation_df_creation(df):
        df = df[(df['fy'] == df['fy'].max()) |
                (df['fy'] == df['fy'].max() - 1)]

        if concert_type == 'clx':
            df = df[(df['season_desc'] == 'PS 17-18 Classics') |
                    (df['season_desc'] == 'PS 18-19 Classics')]
        elif concert_type == 'pop':
            df = df[(df['season_desc'] == 'PS 17-18 Pops') |
                    (df['season_desc'] == 'PS 18-19 Pops')]
        else:
            df = df

        df = df.groupby(['summary_cust_id','perf_dt'], as_index=False)['paid_amt'].agg(['mean']).reset_index()
        df = df.groupby(['summary_cust_id']).agg(['mean','count','sum']).reset_index()
        df.columns = ['summary_cust_id','mean','count','sum']

        avg_price = df['sum'].sum()/df['count'].sum()
        upper_bound_price = avg_price + df['mean'].std()
        avg_freq = df['count'].mean()
        upper_bound_freq = avg_freq + df['count'].std()

        if avg_freq - df['count'].std() >= 0:
            lower_bound_freq = avg_freq - df['count'].std()
        else:
            lower_bound_freq = 1.1

        df.loc[(df['mean'] > avg_price) & (df['count'] > upper_bound_freq), 'segment'] = 'Aficionado'
        df.loc[(df['mean'] < avg_price) & (df['count'] > avg_freq), 'segment'] = 'Committed low-budget'
        df.loc[(df['mean'] < upper_bound_price) & (df['count'] < avg_freq) & (df['count'] > lower_bound_freq), 'segment'] = 'Evolving concert-goer'
        df.loc[(df['mean'] > avg_price) & (df['count'] < lower_bound_freq), 'segment'] = 'High-value prospect'
        df.loc[(df['mean'] < avg_price) & (df['count'] < lower_bound_freq), 'segment'] = 'One-timer'
        df['segment'] = df['segment'].fillna('High-value regular')

        return df


    def this_concert(df):
        # BUILDING DFS
            # Renew/Return/New
        renew_df = customer_classification(df,'renew')
        return_df = customer_classification(df,'return')

            # Subscribers
        sub_df = pd.DataFrame(df[(df.fy == df.fy.max()) &
                             ((df['price_type_group'] == 'Subscription') |
                                     (df['price_type_group'] == 'Flex'))].summary_cust_id.unique())
        sub_df.columns = ['summary_cust_id']
        sub_df['subscriber'] = 1

            # Segmentation
        segmentation_df = segmentation_df_creation(df)[['summary_cust_id','segment']]

            # Donor DF
        donor_df = load_donor_data()

            # Concert DF
        df = df[(df['perf_dt'] > concert_dt) &
                (df['perf_dt'] < concert_dt + timedelta(days=1))].summary_cust_id.unique()
        df = pd.DataFrame(df)
        df.columns = ['summary_cust_id']

        # SET CUST ID TYPES
        sub_df['summary_cust_id'] = sub_df.summary_cust_id.astype(object)
        donor_df['summary_cust_id'] = donor_df.summary_cust_id.astype(object)
        segmentation_df['summary_cust_id'] = segmentation_df.summary_cust_id.astype(object)

        # MERGING RENEW/RETURN
        df = df.merge(return_df,on='summary_cust_id',how='left')
        df['classification'] = 1
        df.loc[df.classifier == 1, 'classification'] = 'return'
        df = df.drop('classifier',1)

        df = df.merge(renew_df,on='summary_cust_id',how='left')
        df.loc[df.classifier == 1, 'classification'] = 'renew'
        df = df.drop('classifier',1)

        df.loc[df.classification == 1] = 'new'

        # MERGING SUBS
        df = df.merge(sub_df, on='summary_cust_id', how='left')
        df.loc[df.subscriber == 1, 'subscriber'] = 'yes'
        df.subscriber = df.subscriber.fillna('no')

        # MERGING DONOR DATA
        df = df.merge(donor_df,how='left',on='summary_cust_id')
        df.donor_5yr_hist = df.donor_5yr_hist.fillna(0)

        # MERGING SEGMENTS
        df = df.merge(segmentation_df,how='left',on='summary_cust_id')

        return df


    ################# EXECUTABLES #######################
    tix_df = prep_data()
    concert_df = this_concert(tix_df)
    seat_finder_df = seat_finder(tix_df)

    # Create an output stream
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Write the dataframes
    concert_df.to_excel(writer, sheet_name='concert_info', index=False)
    seat_finder_df.to_excel(writer, sheet_name='seat_finder', index = False)

    # Close the writer
    writer.close()

    output.seek(0) # return from the beginning of the stream

    # Create the file name
    file_name = name + '_' +\
                    str(concert_dt.month) + '-' +\
                    str(concert_dt.day) +'-' +\
                    str(concert_dt.year) + '.xlsx'

    return send_file(output,
                 attachment_filename=file_name,
                 as_attachment=True)
