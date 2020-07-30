#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 09:38:45 2020

@author: benwilliams
"""

from flask import Flask, request, send_from_directory, jsonify
from flask import render_template
from geopy.geocoders import Nominatim
import pandas as pd
import os
import geopandas as gpd
import geopy
import numpy as np
from shapely.geometry import Polygon, Point, MultiPolygon
import shapefile
from matplotlib import pyplot as plt
from sqlalchemy import create_engine

from tkinter import messagebox
import functools

from bs4 import BeautifulSoup
from urllib.request import urlopen
import requests
import lxml.html as lh

app = Flask(__name__, static_url_path='')
app.static_folder = 'static'


#Route for the Home Page
@app.route('/')
def home_page():
    return render_template('Homepage.html')

#Route for the Meet The Team Page
@app.route('/meet_the_team')
def aboutteam():
    return render_template('about_us.html')

#Route for the Utility Finder input page
@app.route('/utilityfinder')
def utiltyfinder():
    return render_template('utilityfinder.html')

#Route for the result of the Utility Finder input page
@app.route('/search', methods=["GET", "POST"]) #POST requests that a web server accepts the data enclosed in the body of the request message
def search():
    if request.method == "POST":       #GET- retrieves information from the server
        address = request.form["address"]     #gets address from input field
        zipcode = request.form["zipcode"]     #gets zipcode from input field
        state = request.form["state"]         #gets state from input field
        latitude, longitude, granularity = geocode_real(address, zipcode, state)
        if latitude == 0 and longitude ==0:  #case for if the geocode function for address returns nothing
            try:
                latitude, longitude, granularity = geocode_zip(zipcode, state)  #tries the backup geocode function
            except: 
                return render_template("error_page.html", ad=address, zipc=zipcode, st=state)   #errors out if both functions return nothing
        utility = correct_utility_function(latitude, longitude)
        (utility3, pwsidout) = utility
        link2 = "https://www.ncwater.org/WUDC/app/LWSP/report.php?pwsid=" + pwsidout + "&year=2019"  #link format for utility information page
        return render_template("search.html", lat=latitude, lon=longitude, gran= granularity, ad=address, zipc=zipcode, st=state, uname=utility3, linkname=link2)
    elif request.method == "GET":  #routes to interactive map if there's no posted input
        return render_template("interactive_map.html")

#Route for retrieving data from the database for surface water
@app.route('/nwis_surfacewater_avg/<path:site_no>/<path:start_date>/<path:end_date>', methods=['GET'])
def send_surfacewater_avg(site_no, start_date, end_date):
    query = """SELECT a.datenew, b.gage_height_min_avg, b.gage_height_max_avg, b.gage_mean_avg,
        a.gage_height_min, a.gage_height_max, a.gage_mean
        FROM nwis.surfacewater_daily_site_2 a
        RIGHT JOIN (SELECT MIN(gage_height_min) gage_height_min_avg, MAX(gage_height_max) gage_height_max_avg, AVG(gage_mean) gage_mean_avg, day, month
        FROM nwis.surfacewater_daily_site_2
        WHERE site_number = '{site_no}'
        GROUP BY month, day) b
        ON a.month=b.month AND a.day = b.day
        WHERE site_number = '{site_no}' AND a.datenew::TIMESTAMP BETWEEN '{start_date}'::TIMESTAMP AND '{end_date}'::TIMESTAMP
        ORDER BY a.year, a.month, a.day ASC""".format(site_no= site_no, start_date= start_date, end_date= end_date)
    data= pd.read_sql_query(query, cnx)
    df1 = data.where(pd.notnull(data), None) #replaces nulls with Nones for dygraphs to read the data table properly
    return jsonify(**df1.to_dict('split'));


#Route for retrieving data from the database for ground water
@app.route('/nwis_groundwater_avg/<path:site_no>/<path:start_date>/<path:end_date>', methods=['GET'])
def send_groundwater_avg(site_no, start_date, end_date):
    query = """SELECT a.datenew, b.depth_below_land_ft_min_avg, b.depth_below_land_ft_max_avg, b.depth_below_land_ft_mean_avg,
        a.depth_below_land_ft_min, a.depth_below_land_ft_max, a.depth_below_land_ft_mean
        FROM nwis.groundwater_daily_site_2 a
        RIGHT JOIN (SELECT MIN(depth_below_land_ft_min) depth_below_land_ft_min_avg, MAX(depth_below_land_ft_max) depth_below_land_ft_max_avg, AVG(depth_below_land_ft_mean) depth_below_land_ft_mean_avg, day, month
        FROM nwis.groundwater_daily_site_2
        WHERE site_number = '{site_no}'
        GROUP BY month, day) b
        ON a.month=b.month AND a.day = b.day
        WHERE site_number = '{site_no}' AND a.datenew::TIMESTAMP BETWEEN '{start_date}'::TIMESTAMP AND '{end_date}'::TIMESTAMP
        ORDER BY a.year, a.month, a.day ASC""".format(site_no= site_no, start_date= start_date, end_date= end_date)
    data= pd.read_sql_query(query, cnx)
    df1 = data.where(pd.notnull(data), None) #replaces nulls with Nones for dygraphs to read the data table properly
    return jsonify(**df1.to_dict('split'));


#Route for allowing dygraphs to use node modules stored in the node modules folder
@app.route('/node_modules/<path:path>')
def send_js(path):
    return send_from_directory('node_modules', path)

#
## FUNCTIONS FOR FINDING LOCATIONS
#

locator = Nominatim(user_agent="otherGeocoder")   #Our geocoder of choice

def geocode_real (address, zipcode, state):  #geocoder address to coordinates
    lista = []
    lista.append(address)
    lista.append(zipcode)
    lista.append(state)
    addressfull = ' '.join(lista)  #creates string address from three separate inputs
    try: 
        location = locator.geocode(addressfull)
        if address == "":
            return location.latitude, location.longitude, "zipcode_level"
        else:
            return location.latitude, location.longitude, "address_level"
    except:
        return 0, 0, "failure"  #backup case, should push to geocode zip

def geocode_zip (zipcode, state):  #geocoder zip to coordinates as backup
    listb = []
    listb.append(zipcode)
    listb.append(state)
    halfaddress = ' '.join(listb) #creates string address from two separate inputs
    try:
        zip_middle = locator.geocode(halfaddress)
        return zip_middle.latitude, zip_middle.longitude, "zipcode_level"
    except:
        return 0, 0, "failure"


##SECTION FOR ALLOWING DATA TO BE READ/WRITTEN FROM THE DATABASE

hostname = 'rapid-1304.vm.duke.edu'
port = '5432'
username = os.environ['USERNAME']
password = os.environ['PASSWORD']
dbname = 'postgres'


postgres_str = 'postgresql://{username}:{password}@{hostname}:{port}/{dbname}'.format(hostname=hostname,
                                                                                 port=port,
                                                                                 username=username,
                                                                                  password=password,
                                                                                 dbname=dbname)
cnx = create_engine(postgres_str)


##HANDLES GETTING LINKS FROM NCWATER WEBSITE

response = requests.get('https://www.ncwater.org/Drought_Monitoring/statusReport.php/')  #conservation status info webscraping
stored_contents = lh.fromstring(response.content)
table_elements = stored_contents.xpath('//tr')
col=[]
i=0
for t in table_elements[0]:
    i+=1
    name=t.text_content()
    col.append((name,[]))
for j in range(1,len(table_elements)):
    T=table_elements[j]
    if len(T)!=7:
            break
    i=0
    for t in T.iterchildren():
        data=t.text_content() 
        if i>0:
            try:
                data=int(data)
            except:
                pass
        col[i][1].append(data)
        i+=1
Dict ={title:column for (title,column) in col}
Newest_Updates =pd.DataFrame(Dict)
Newest_Updates = Newest_Updates[~Newest_Updates['PWSID'].astype(str).str.startswith('PWSID')]
Bigger_Dataframe = Newest_Updates

filepath = os.path.join('..', 'Boundaries', 'NC_statewide_CWS_areas.gpkg')
StateWide = gpd.read_file(filepath) #make large usable dataframe with both names and links
StateWide.geometry= StateWide.geometry.to_crs(epsg="4326")
Combined_Utility = pd.merge(Bigger_Dataframe, StateWide, 'right', on="PWSID")

polygons = Combined_Utility['geometry'] #return utility name and link
utility1 = Combined_Utility['Water System']
utility2 = Combined_Utility['SystemName']
pwsidnum = Combined_Utility['PWSID']

##BACKUP UTILITY NAME FUNCTION

def missing_utility(i):  
    UtilityCloser = utility2.replace('_', ' ')   #make the utility readable
    UtilityCloser = UtilityCloser.replace('\'', '')
    UtilityCloser = UtilityCloser.replace('\"', '')
    UtilityList = list(UtilityCloser.split(" "))
    for k in range(len(UtilityList)):
        UtilityList[k] = UtilityList[k].replace(' ', '')
        if 'Town' == UtilityList[0] or 'City' == UtilityList[0]:
            return(UtilityCloser, "No link provided by utility company")
        elif 'Town of' in UtilityCloser or 'Town Of' in UtilityCloser or 'City Of' in UtilityCloser or 'City of' in UtilityCloser or 'Village of' in UtilityCloser or 'Village Of' in UtilityCloser:
                if len(UtilityList) == 3:
                    myorder = [1, 2, 0]
                    UtilityTown = [UtilityList[i] for i in myorder]
                    return(' '.join(UtilityTown[0 : 3]), "No link provided by utility company")
                elif len(UtilityList) == 4:
                    myorder = [2, 3, 0, 1]
                    UtilityTown = [UtilityList[i] for i in myorder]
                    return(' '.join(UtilityTown[0 :5]), "No link provided by utility company")
                else:
                    if '' in UtilityList[2]:
                        myorder = [3, 4, 0, 1]
                        UtilityTown = [UtilityList[i] for i in myorder]
                        return(' '.join(UtilityTown[0 :5]), "No link provided by utility company")
                    else:
                        myorder = [1, 2, 0, 3, 4]
                        UtilityTown = [UtilityList[i] for i in myorder]
                        return(' '.join(UtilityTown[0 :6]), "No link provided by utility company")
        else: 
            if ',' in utility.iloc[i]:
                UtilityCloser = utility.iloc[i].replace(',', '')
                UtilityList = list(UtilityCloser.split(" "))
                if len(UtilityList) == 3:
                    myorder = [1, 2, 0]
                    UtilityTown = [UtilityList[i] for i in myorder]
                    return(' '.join(UtilityTown[0 : 3]), "No link provided by utility company")
                elif len(UtilityList) == 4:
                    myorder = [2, 3, 0, 1]
                    UtilityTown = [UtilityList[i] for i in myorder]
                    return(' '.join(UtilityTown[0 :5]), "No link provided by utility company")
                else:
                    myorder = [3, 4, 0, 1, 2]
                    UtilityTown = [UtilityList[i] for i in myorder]
                    return(' '.join(UtilityTown[0 :6]), "No link provided by utility company")
            else:
                return(utility2.iloc[i], "No link provided by utility company")

##PRIMARY UTILITY NAME FUCNTION

def correct_utility_function(latitude, longitude):
    coordinate = Point(longitude, latitude)
    for i in range(len(Combined_Utility)):
        if polygons.iloc[i].contains(coordinate):
            if pd.isnull(utility1.iloc[i]):
                return missing_utility(i)
            else:
                return(utility1.iloc[i], pwsidnum.iloc[i])

    return None, None
