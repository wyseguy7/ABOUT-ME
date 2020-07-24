#GROUNDWATER!!!!!!!
dfg = pd.read_table('groundwaterdata', sep='\t', lineterminator='\r')
df2g = dfg[["site_no", "station_nm", "site_tp_cd"]]
siteNumbersg = df2g["site_no"]

#create empty dataframes
newDFg = pd.DataFrame()
finalDFg = pd.DataFrame()

#assign start and end dates
days = datetime.timedelta(1)
new_date = date.today() - days
newest_date = (str(new_date))

for i in range(siteNumbersg.size):
    if i==0:
        continue
    query = """SELECT datenew, year, month, day, site_number FROM nwis.groundwater_daily_site_2
    WHERE site_number = '{}' ORDER BY year DESC, month DESC, day DESC LIMIT 1""".format(siteNumbersg[i])
    data= pd.read_sql_query(query, cnx)
    if (data.empty):
        continue
    lastdate = data.iloc[0][0]
    lastdateobj = datetime.datetime.strptime(lastdate, '%m/%d/%Y') + datetime.timedelta(days=1)
    lastdatefinal = lastdateobj.strftime('%m/%d/%Y')
    lastdatelist = lastdatefinal.split("/")
    lastdatelist = [lastdatelist[2], lastdatelist[0], lastdatelist[1]]
    lastdatestr = "-".join(lastdatelist)
    dfg = nwis.get_record(sites=siteNumbersg[i], service='dv', start=lastdatestr, end=date.today())
    if (dfg.empty):
        continue
    a_list = dfg.index.tolist()
    if(len(a_list) > 0):
        for i in range(len(a_list)):
            a_list[i] = str(a_list[i]).replace(" 00:00:00+00:00", "")
            dfg.index = a_list
    newDFg = newDFg.append(dfg, ignore_index = False)
    newDFg["date"] = newDFg.index
    newDFg[['year','month', 'day']] = newDFg.date.str.split("-",expand=True)
    newDFg["datecloser"] = newDFg['month'].str.cat(newDFg['day'], sep= "/")
    newDFg["datenew"] = newDFg['datecloser'].str.cat(newDFg['year'], sep= "/")
finalDFg = newDFg[["site_no", "72019_Mean", "72019_Mean_cd", "72019_Maximum", "72019_Maximum_cd", "72019_Minimum", "72019_Minimum_cd", 'year','month', 'day', "datenew"]]
finalDFg = finalDFg.reset_index(drop=True)
finalDFg = finalDFg.rename(columns={"site_no":"site_number", "72019_Mean":"depth_below_land_ft_mean", "72019_Mean_cd":"mean_cd", "72019_Maximum":"depth_below_land_ft_max", "72019_Maximum_cd":"max_cd", "72019_Minimum":"depth_below_land_ft_min", "72019_Minimum_cd":"min_cd"})

finalDFg.to_sql(name='groundwater_daily_site_2', schema='nwis', con=cnx, if_exists='append', index=False)

