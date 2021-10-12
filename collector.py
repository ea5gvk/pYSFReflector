#!/usr/bin/python3

#    Collector  - this is a Simple Dashboard for pYSFReflector2 by IU5JAE
#
#    Created by David Bencini (IK5XMK) on 01/09/2021.
#    Copyright 2021 David Bencini (IK5XMK). All rights reserved.

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import threading
import queue
import time
import json
import sys
from threading import Lock
import datetime as dt
from datetime import datetime
import re
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import HTMLResponse

# *** CONFIG SECTION ***
# set your Json pYSF2 address and port (see pysfreflector2.ini)
srv_addr_port = ('127.0.0.1', 42396) # 127.0.0.1

# set your dashboard address and port for external
dashb_addr_port = ('PONER VUESTRA WEB O DNS EXTERNA', 12001) # ysf.grupporadiofirenze.net

# set web server listener interface
ws_linterface = "0.0.0.0"

# set main web page refresh time (secs)
r_mpage = 5

# set others web pages refresh time (secs)
r_opages = 60

# show values description in web pages (True/False)
detail = True

# set your url/path logo image
logo = "http://ysf.grupporadiofirenze.net/ysf/img/logo.jpg"

# do you have a BM link ? set the serial
SER_LNK = "E0C4W" # BM_2222

# obscure last IP part number (True/False)
obs_IP = True
# *** END CONFIG SECTION ***

DASH_VER = "B.10.01"
        
conn_msg = "CONNREQ"
bye_msg  = "BYE"
buffer   = 1024
t_out    = 0
t_start  = ""
t_end    = ""
p_title  = "Simple pYSF2 Reflector Dashboard" # it will be overwritten

# reflector infos
refl_info = {"system": "", "ver": "", "REF_ID": "", "REF_NAME": "", "REF_DESC": "", "contact":"", "web":""} 

# callsigns
my_record = {"status":"", "stream_id":"", "call":"", "target":"", "gw":"", "time":"",
             "CS": "1", "CM": "2", "FT": "5", "Dev": "False", "MR": "3", "VoIP": "False", "DT": "0", "SQL": "False", "SQC": "0",
             "latitude":"", "longitude":"", "aprs":"", # aprs key is for internal dashboard use, it is not sent by pYSF2
             "radio_code":"", "station_id":"", "radio_id":"",
             "dst":"", "src":"", "uplink":"", "downlink":"",
             "downlink_id":"", "uplink_id":""}
my_list = [] # main web page records list
my_page = {"status":"Flow",
           "call":"Callsign (sfx)",
           "target":"Target",
           "gw":"Gateway",
           "CM":"Call mode",
           "FT": "Frame",
           "time":"UTC (QSO time)",
           "Dev": "Deviation",
           "DT": "Data type",
           "radio_code":"Radio",
           "radio_id":"Serial",
           "SQC":"GID",
           "latitude":"Latitude",
           "longitude":"Longitude",
           "aprs":"Map"} # see aprs key above 

# linked systems
my_record2 = {"linked":"", "call":"", "IP":"", "port":"", "TC":"", "CF":"", "LO":"", "LK":""}
my_list2 = [] # linked web page
cl_lst = False
my_page2 = {"linked":"#",
            "call":"GW/RPT/HS",
            "IP":"IP address",
            "port":"UDP port",
            "TC":"0/60",
            "CF":"Connected from",
            "LO":"Muted",
            "LK":"Locked"}

# blocked callsigns for defined time (by pYSF2)
my_record3 = {"blk_time":"", "call":"", "BR":"", "TR":""}
my_list3 = [] # blocked web page
cl_lst_blk = False
my_page3 = {"blk_time":"#",
            "call":"Callsign",
            "BR":"Reason",
            "TR":"UTC(will be unlocked)"}

# history calls
my_record4 = {"call":"", "gw":"", "time":"", "gw_IP":""}
my_list4= [] # history web page
my_page4 = {"call":"Callsign",
            "gw":"Gateway",
            "time":"time (UTC)",
            "gw_IP":"GW IP"} # managed in dashboard, not from refl

# web page styles
my_img_hide = "@media (max-width:650px) {img#optionalstuff {display: none;}}"
my_table_style = ".styled-table { \
               border-collapse:collapse; \
               margin:25px 0; \
               font-size:0.9em; \
               font-family:verdana, sans-serif; \
               min-width:400px; \
               box-shadow:0 0 20px rgba(0, 0, 0, 0.15);} \
               .styled-table thead tr {background-color:#009879; color:#ffffff; text-align:left;} \
               .styled-table th, .styled-table td {padding:12px 15px;} \
               .styled-table tbody tr {border-bottom:1px solid #dddddd;} \
               .styled-table tbody tr:nth-of-type(even) {background-color:#f3f3f3;} \
               .styled-table tbody tr:last-of-type {border-bottom:2px solid #009879;} \
               .styled-table tbody tr.active-row {font-weight:bold; color:black; background-color:red;} \
               td, th {white-space:nowrap; vertical-align:middle;} \
               A {text-decoration:none;}" 

my_nav_btns_style = ".btn {width:137px; border:2px solid black; border-radius:5px; background-color:white; color:black; padding:14px 28px; font-size:16px; cursor:pointer;} \
                    .success {border-color:#04AA6D; color:green;} \
                    .success:hover { background-color:#04AA6D; color:white;} \
                    .info {border-color:#2196F3; color:dodgerblue} \
                    .info:hover {background:#2196F3; color:white;} \
                    .warning {border-color:#ff9800; color:orange;} \
                    .warning:hover {background:#ff9800; color:white;} \
                    .danger {border-color:#f44336; color:red} \
                    .danger:hover {background:#f44336; color:white;} \
                    .default {border-color:#e7e7e7; color:black;} \
                    .default:hover {background:#e7e7e7;}"

lock = Lock()

def obscure_IP(IP): # privacy
    global obs_IP
    if ( obs_IP == True):
        tmp = IP.split(".")
        tmp[3] = "***" # hide only last byte
        my_ip = tmp[0] + "." + tmp[1] + "." + tmp[2] + "." + tmp[3]
    else:
        my_ip = IP
    return(my_ip)

def calc_qso_time(t2, t1):
    start_dt = dt.datetime.strptime(t1, '%H:%M:%S')
    end_dt = dt.datetime.strptime(t2, '%H:%M:%S')
    diff = (end_dt - start_dt) 
    diff.seconds/60
    d = str(diff)
    return(d)

def purge_call(call): 
    pattern = r'[/-]' 
    re_call = re.sub(pattern,"+",call) 
    res = re_call.find("+")
    if ( res > 0 ):
        my_call = re_call[:res]
    else:
        my_call = call
    return(my_call)

def add_time():
    return (time.strftime("%Y:%m:%d %H:%M:%S", time.localtime()))

async def homepage(request):
    pg_resp = main_page()
    return HTMLResponse(pg_resp)

async def linked(request):
    pg_resp = linked_page()
    return HTMLResponse(pg_resp)

async def blocked(request):
    pg_resp = blocked_page()
    return HTMLResponse(pg_resp)

async def history(request):
    pg_resp = history_page()
    return HTMLResponse(pg_resp)

def system_info():
    code = "<div style='float:left; display:block; width:550px; padding:5px; background:#FFFFFF; box-shadow:10px 10px 5px #888888; font-family:verdana, arial;'>"
    code = code + "<h3>" + refl_info["system"] + "  #" + refl_info["REF_ID"] + " " + refl_info["REF_NAME"] + "</h3>"
    code = code + "<h4>[ " + refl_info["REF_DESC"] + " ]</h4>"
    code = code + "<span style='font-size:14px; font-family:verdana, arial;'>reflector vers. " + refl_info["ver"] + " dashboard vers. " + DASH_VER + "</span><br>"
    code = code + "<span style='font-size:12px; font-family:verdana, arial;'>Mail: " + refl_info["contact"] + " ___ Web: " + refl_info["web"] + "</span>"
    code = code + "</div><div style='float:right; display:block;'>"
    code = code + "<img id='optionalstuff' src='" + logo + "' width='200px' height='150px'/></div>"
    code = code + "</div><div style='clear:both;'></div><br>"
    return(code)

def nav_bar(): 
    code = system_info()
    code = code + "<div>"
    code = code + "<a href='http://" + dashb_addr_port[0] + ":" + str(dashb_addr_port[1]) + "'><button class='btn success'>Main</button></a>&nbsp;"
    code = code + "<a href='http://" + dashb_addr_port[0] + ":" + str(dashb_addr_port[1]) + "/linked'><button class='btn info'>Linked</button></a>&nbsp;"
    code = code + "<a href='http://" + dashb_addr_port[0] + ":" + str(dashb_addr_port[1]) + "/blocked'><button class='btn warning'>Blocked</button></a>&nbsp;"
    code = code + "<a href='http://" + dashb_addr_port[0] + ":" + str(dashb_addr_port[1]) + "/history'><button class='btn info'>History</button></a>&nbsp;"
    code = code + "</div>"
    return(code)

def main_page():
    global my_page
    global my_list
    global p_title
    temp_list = []
    pg = "<!doctype html>"
    pg = pg + "<head>"
    pg = pg + "<html lang='en'>"
    pg = pg + "<meta charset='utf-8'>"
    pg = pg + "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    pg = pg + "<title>" + p_title + "</title>"
    #pg = pg + "<meta http-equiv='Expires' content='-1'>" # clear browser cache
    pg = pg + "<meta http-equiv='refresh' content='" + str(r_mpage) + "'>"
    pg = pg + "<meta name='description' content='A simple dashboard by ik5xmk for IU5JAE python YSFReflector system'>"
    pg = pg + "<meta name='author' content='ik5xmk'>"
    pg = pg + "<link href='https://fonts.googleapis.com/icon?family=Material+Icons' rel='stylesheet'>" # google fonts
    pg = pg + "<style>"
    pg = pg + my_img_hide
    pg = pg + my_table_style
    pg = pg + my_nav_btns_style
    pg = pg + "</style>"
    pg = pg + "</head>"
    pg = pg + "<body>"
    # nav bar
    pg = pg + nav_bar()
    pg = pg + "<table class='styled-table'>"
    # table head
    pg = pg + "<thead>"
    pg = pg + "<tr>"
    pg = pg + "<th>#</th>"
    for key in my_record:
        if ( key in my_page ):
            pg = pg + "<th>" + my_page[key] + "</th>"
    pg = pg + "</tr>"
    pg = pg + "</thead>"
    pg = pg + "<tbody>"
    # table data
    if ( len(my_list) > 0 ):
        temp_list = my_list.copy()
        temp_list.reverse() # from newest
        nr = 1
        for item in temp_list:    
            if ( item["status"] == "TX" ):
                pg = pg + "<tr class='active-row'>"
            else:
                pg = pg + "<tr>"
            pg = pg + "<td>" + str(nr) + "</td>"
            for key in item:
                if key in my_page:
                    if ( key == "status" ):
                        if ( item["status"] == "TX" ):
                            pg = pg + "<td><center><i class='material-icons' style='font-size:24px;color:black;'>trending_up</i></center></td>"
                        if ( item["status"] == "TC" ):
                            pg = pg + "<td><center><i class='material-icons' style='font-size:24px;color:green;'>check_circle_outline</i></center></td>"
                        if ( item["status"] == "WD" ):
                            pg = pg + "<td><center><i class='material-icons' style='font-size:24px;color:orange;'>pending</i></center></td>"
                        if ( item["status"] == "TO" ):
                            pg = pg + "<td><center><i class='material-icons' style='font-size:24px;color:red;'>record_voice_over</i></center></td>"    
                    elif ( key == "call" ):
                        c = purge_call(item[key])
                        pg = pg + "<td><a href='https://qrz.com/db/" + c + "' target='_blank'>" + c +"</a> (" + re.sub(c,"",item[key]) + ")</td>"
                    elif ( key == "latitude" and item["latitude"] != "" ): # we have the position from the radio
                        pg = pg + "<td><a href='https://www.openstreetmap.org/?mlat=" + item["latitude"] + "&mlon=" + item["longitude"] + "' target='_blank'>" + item[key] + "</a></td>"
                    elif ( key == "aprs" and refl_info["APRS_EN"] == "1" and item["latitude"] != "" ): # the pYSF2 is managing aprs data to aprs server   
                        pg = pg + "<td><center><a href='https://www.aprs.fi/" + purge_call(item["call"]) + refl_info["APRS_SSID"] + "' target='_blank'><i class='material-icons' style='font-size:24px;color:black;'>place</i></a></center></td>"
                    elif ( key =="time" and item["status"] == "TX" ):
                        now = datetime.now()
                        t_now = now.strftime("%H:%M:%S")
                        d = calc_qso_time(t_now, t_start)
                        pg = pg + "<td>" + "talking (" + d[2:] + ")" + "</td>"
                    else:
                        pg = pg + "<td>" + item[key] + "</td>"
            nr = nr + 1
            pg = pg + "</tr>"
    pg = pg + "</tbody>"
    pg = pg + "</table>"
    pg = pg + "</body>"
    pg = pg + "</html>"
    return(pg)

def linked_page():
    global my_page2
    global my_list2
    global p_title
    temp_list2 = []
    pg = "<!doctype html>"
    pg = pg + "<head>"
    pg = pg + "<html lang='en'>"
    pg = pg + "<meta charset='utf-8'>"
    pg = pg + "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    pg = pg + "<title>" + p_title + " linked gws</title>"
    pg = pg + "<meta http-equiv='Expires' content='-1'>"
    pg = pg + "<meta http-equiv='refresh' content='" + str(r_opages) + "'>"
    pg = pg + "<meta name='description' content='A simple dashboard by ik5xmk for IU5JAE python YSFReflector system'>"
    pg = pg + "<meta name='author' content='ik5xmk'>"
    pg = pg + "<style>"
    pg = pg + my_img_hide
    pg = pg + my_table_style
    pg = pg + my_nav_btns_style
    pg = pg + "</style>"
    pg = pg + "</head>"
    pg = pg + "<body>"
    # nav bar
    pg = pg + nav_bar()
    pg = pg + "<table class='styled-table'>"
    # table head
    pg = pg + "<thead>"
    pg = pg + "<tr>"
    for key in my_record2:
        if ( key in my_page2 ):
            pg = pg + "<th>" + my_page2[key] + "</th>"
    pg = pg + "</tr>"
    pg = pg + "</thead>"
    pg = pg + "<tbody>"
    # table data
    if ( len(my_list2) > 0 ):
        temp_list2 = my_list2.copy()
        for item in temp_list2:
            pg = pg + "<tr>"
            for key in item:
                if key in my_page2:
                    pg = pg + "<td>" + item[key] + "</td>"
            pg = pg + "</tr>"
    pg = pg + "</tbody>"
    pg = pg + "</table>"
    pg = pg + "</body>"
    pg = pg + "</html>"
    return(pg)

def blocked_page():
    global my_page3
    global my_list3
    global p_title
    temp_list3 = []
    pg = "<!doctype html>"
    pg = pg + "<head>"
    pg = pg + "<html lang='en'>"
    pg = pg + "<meta charset='utf-8'>"
    pg = pg + "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    pg = pg + "<title>" + p_title + " blocked callsigns</title>"
    pg = pg + "<meta http-equiv='Expires' content='-1'>"
    pg = pg + "<meta http-equiv='refresh' content='" + str(r_opages) + "'>"
    pg = pg + "<meta name='description' content='A simple dashboard by ik5xmk for IU5JAE python YSFReflector system'>"
    pg = pg + "<meta name='author' content='ik5xmk'>"
    pg = pg + "<style>"
    pg = pg + my_img_hide
    pg = pg + my_table_style
    pg = pg + my_nav_btns_style
    pg = pg + "</style>"
    pg = pg + "</head>"
    pg = pg + "<body>"
    # nav bar
    pg = pg + nav_bar()
    pg = pg + "<table class='styled-table'>"
    # table head
    pg = pg + "<thead>"
    pg = pg + "<tr>"
    for key in my_record3:
        if ( key in my_page3 ):
            pg = pg + "<th>" + my_page3[key] + "</th>"
    pg = pg + "</tr>"
    pg = pg + "</thead>"
    pg = pg + "<tbody>"
    # table data
    if ( len(my_list3) > 0 ):
        temp_list3 = my_list3.copy()
        for item in temp_list3:
            pg = pg + "<tr>"
            for key in item:
                if key in my_page3:
                    pg = pg + "<td>" + item[key] + "</td>"
            pg = pg + "</tr>"
    pg = pg + "</tbody>"
    pg = pg + "</table>"
    pg = pg + "</body>"
    pg = pg + "</html>"
    return(pg)

def history_page():
    global my_page4
    global my_list4
    global p_title
    temp_list4 = []
    pg = "<!doctype html>"
    pg = pg + "<head>"
    pg = pg + "<html lang='en'>"
    pg = pg + "<meta charset='utf-8'>"
    pg = pg + "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    pg = pg + "<title>" + p_title + " history page</title>"
    pg = pg + "<meta http-equiv='Expires' content='-1'>"
    pg = pg + "<meta http-equiv='refresh' content='" + str(r_opages) + "'>"
    pg = pg + "<meta name='description' content='A simple dashboard by ik5xmk for IU5JAE python YSFReflector system'>"
    pg = pg + "<meta name='author' content='ik5xmk'>"
    pg = pg + "<style>"
    pg = pg + my_img_hide
    pg = pg + my_table_style
    pg = pg + my_nav_btns_style
    pg = pg + "</style>"
    pg = pg + "</head>"
    pg = pg + "<body>"
    # nav bar
    pg = pg + nav_bar()
    pg = pg + "<table class='styled-table'>"
    # table head
    pg = pg + "<thead>"
    pg = pg + "<tr>"
    for key in my_record4:
        if ( key in my_page4 ):
            pg = pg + "<th>" + my_page4[key] + "</th>"
    pg = pg + "</tr>"
    pg = pg + "</thead>"
    pg = pg + "<tbody>"
    # table data
    if ( len(my_list4) > 0 ):
        temp_list4 = my_list4.copy()
        temp_list4.reverse() # from newest
        for item in temp_list4:
            pg = pg + "<tr>"
            for key in item:
                if key in my_page4:
                    pg = pg + "<td>" + item[key] + "</td>"
            pg = pg + "</tr>"
    pg = pg + "</tbody>"
    pg = pg + "</table>"
    pg = pg + "</body>"
    pg = pg + "</html>"
    return(pg)

def pingpong(s):
    global srv_addr_port
    while True:
        s.sendto(b'PING',  srv_addr_port)
        time.sleep(10)

def timeout(s):
    while True:
        global bye_msg
        global srv_addr_port
        global t_out
        lock.acquire()
        t_out = t_out + 1
        lock.release()
        if ( t_out == 60 ):
            print(add_time() + " timeout, no PONG answer from server")
            s.sendto(str.encode(bye_msg), srv_addr_port)
            time.sleep(1)
            print(add_time() + " sent BYE, and call the server again")
            s.sendto(str.encode(conn_msg), srv_addr_port)
            lock.acquire()
            t_out = 0
            lock.release()
        time.sleep(1)
        
def output():
    global my_list
    global my_record
    print("(" + my_record["status"] + ") " + my_record["call"] + " at: " + my_record["time"])   
    # purge list from last "tx" record
    if ( my_record["status"] == "TC" or my_record["status"] == "WD" or my_record["status"] == "TO" ):
        lock.acquire() 
        my_list.pop()
        lock.release()    
    if ( len(my_list) > 19 ):
        lock.acquire()
        my_list.pop(0)
        lock.release()    
    cp = my_record.copy()
    lock.acquire()
    my_list.append(cp)
    lock.release()

def output2():
    global my_list2
    global my_record2       
    print("==>linked GW:" + my_record2["call"])
    cp = my_record2.copy()
    lock.acquire()
    my_list2.append(cp)
    lock.release()
    print("gw inserted at " + add_time())

def output3():
    global my_list3
    global my_record3       
    print("==>blocked call:" + my_record3["call"])
    cp = my_record3.copy()
    lock.acquire()
    my_list3.append(cp)
    lock.release()
    print("blocked call inserted at " + add_time())

def output4():
    global my_list4
    global my_record4
    print("==>history call:" + my_record4["call"])
    for item in my_list4:
        if ( my_record4["call"] in item.values() ): # call is in history list? remove the old one
            lock.acquire()
            my_list4.remove(item)
            lock.release()
            print(add_time() + " history updated, removed old one")  
    cp = my_record4.copy()
    lock.acquire()
    if ( len(my_list4) > 99 ):
       del my_list4[0] 
    my_list4.append(cp)
    lock.release()
    print("inserted in history at " + add_time())

def rcv(s): 
    while True:
        try:
            msg,adr = s.recvfrom(buffer)
            if ( msg == b"PONG" ):
                global t_out
                lock.acquire()
                t_out = 0
                lock.release()
                continue
            if ( msg[0:6] == b"CONNOK" ):
                answer = msg.decode("utf-8")
                my_par = answer.split(":")
                print("server answered, established with my IP:" + my_par[1] + " PORT:" + my_par[2])
            else: 
                # load the json data to a string
                resp = json.loads(msg)
                global my_record
                global t_start
                global t_end
                global my_record2
                global cl_lst
                global my_record3
                global cl_lst_blk
                global refl_info
                global my_record4
                global p_title
                for item in resp:
                    # reflector info
                    # b'{"system": "pYSFReflector2", "ver": "20210905", "REF_ID": "90123", "REF_NAME": "IT GRF-TEST", "REF_DESC": "TEST PyRefl", "APRS_EN": "1", "APRS_SSID": "", "contact":"", "web":""}'
                    if ( item == "system" ):
                        refl_info["system"] = resp["system"]
                        refl_info["ver"] = resp["ver"]
                        refl_info["REF_ID"] = resp["REF_ID"]
                        refl_info["REF_NAME"] = resp["REF_NAME"]
                        refl_info["REF_DESC"] = resp["REF_DESC"]
                        refl_info["APRS_EN"] = resp["APRS_EN"]
                        refl_info["APRS_SSID"] = resp["APRS_SSID"]
                        refl_info["contact"] = resp["contact"]
                        refl_info["web"] = resp["web"]
                        print("\n" + refl_info["system"] + ":" + refl_info["REF_ID"] + " APRS:" + refl_info["APRS_EN"] + "\n")
                        p_title = "pYSFRelfector2:" + refl_info["REF_ID"] + " " + refl_info["REF_DESC"] + " with APRS:" + refl_info["APRS_EN"] + " SSID:" + refl_info["APRS_SSID"]
                        continue
                    
                    # qso traffic
                    # b'{"stream_start": "2500015", "call": "IW1BR/300D", "target": "*****FAPrb", "gw": "PYBRIDGE", "time": "2021-08-11 15:27:38.089",
                    #    "CS": "1", "CM": "2", "FT": "5", "Dev": "False", "MR": "3", "VoIP": "False", "DT": "0", "SQL": "False", "SQC": "0"}
                    # b'{"stream_id01": "2500015", "Rem1+2": "1773317527"}'
                    # b'{"stream_id02": "2500015", "Rem3+4": "27003FAPrb"}'
                    # b'{"stream_id03": "2500015", "radio_code": "49"}'
                    # b'{"stream_id04": "2500015", "latitude": "45.838166666666666", "longitude": "45.838166666666666"}'
                    # b'{"stream_id05": "2500015", "dst": "", "src": "", "uplink": "", "downlink": ""}'
                    # b'{"stream_end": "2500015", "type": "TC", "time": "2021-08-11 15:27:41.384"}'
                    if ( item == "stream_start" ):
                        lock.acquire()
                        st_id.put( [ resp["stream_start"], resp["call"] ] )
                        lock.release()
                        my_record["status"] = "TX"
                        my_record["stream_id"] = resp["stream_start"]
                        my_record["call"] = resp["call"]
                        my_record["target"] = resp["target"]
                        #if ( detail == True ):
                        #    if ( my_record["target"][:3] == "ALL" ):
                        #        my_record["target"] = "Global/ALL"
                        #    elif ( my_record["target"][:1] == "*" ):
                        #        my_record["target"] = "Global/Me"
                        #    else:
                        #        my_record["target"] = "WiresX/Me"   
                        my_record["gw"] = resp["gw"]
                        # set history
                        my_record4["call"] = resp["call"]
                        my_record4["gw"] = resp["gw"]
                        my_record4["time"] = resp["time"][:19]
                        for r in my_list2:
                            print("check linked:" + r["call"] + "/" + r["IP"])
                            if ( my_record4["gw"] in r.values() ): # gw is already in linked list ?
                                print("found!")
                                my_record4["gw_IP"] = r["IP"] # yes, so we get its IP for history
                                break
                            else:
                                my_record4["gw_IP"] = ""
                        output4()
                        # now normal check
                        temp = str.split(resp["time"])
                        my_record["time"] = temp[1][:8] # begin TX time
                        t_start = my_record["time"]
                        my_record["CS"] = resp["CS"]
                        my_record["CM"] = resp["CM"]
                        if ( detail == True ): 
                            if ( resp["CM"] == "0" ):
                                my_record["CM"] = "Group/CQ"
                            elif ( resp["CM"] == "1" ):
                                my_record["CM"] = "Radio ID"
                            elif ( resp["CM"] == "2" ):
                                my_record["CM"] = "Reserve"
                            else:
                                my_record["CM"] = "Individual"
                        my_record["FT"] = resp["FT"]
                        my_record["Dev"] = resp["Dev"]
                        if ( detail == True ): 
                            if ( resp["Dev"] == "False" ):
                                my_record["Dev"] = "Wide"
                            else:
                                my_record["Dev"] = "Narrow"
                        my_record["MR"] = resp["MR"]
                        my_record["VoIP"] = resp["VoIP"]
                        my_record["DT"] = resp["DT"]
                        if ( detail == True ):
                            if ( resp["DT"] == "0" ):
                                my_record["DT"] = "V/D mode 1"
                            elif ( resp["DT"] == "1" ):
                                my_record["DT"] = "Data FR"
                            elif ( resp["DT"] == "2" ):
                                my_record["DT"] = "V/D mode 2"
                            else:
                                my_record["DT"] = "Voice FR"
                        my_record["SQL"] = resp["SQL"]
                        my_record["SQC"] = resp["SQC"]
                        my_record["latitude"] = ""
                        my_record["longitude"] = ""
                        my_record["radio_code"] = ""
                        my_record["station_id"] = ""
                        my_record["radio_id"] = resp["target"][-5:]
                        my_record["dst"] = ""
                        my_record["src"] = ""
                        my_record["uplink"] = ""
                        my_record["downlink"] = ""
                        my_record["downlink_id"] = ""
                        my_record["uplink_id"] = ""                    
                        output()
                        continue

                    if ( item == "stream_id01" ):
                        if ( resp["stream_id01"] == my_record["stream_id"] ):
                            my_record["downlink_id"] = resp["Rem1+2"][:5]
                            my_record["uplink_id"] = resp["Rem1+2"][5:]
                            continue
                      
                    if ( item == "stream_id02" ):
                        if ( resp["stream_id02"] == my_record["stream_id"] ):
                            my_record["station_id"] = resp["Rem3+4"][:5]
                            my_record["radio_id"] = resp["Rem3+4"][5:]
                            # second check
                            if ( my_record["radio_id"] == "" ):
                                if ( resp["DT"] == "3" ):
                                    my_record["radio_id"] = my_record["target"][5:]
                            continue

                    if ( item == "stream_id03" ):
                        if ( resp["stream_id03"] == my_record["stream_id"] ):
                            if ( my_record["gw"] == "PEANUT" ):
                                radio = "PEANUT"
                            else:
                                radio = "<center><i class='material-icons' style='font-size:24px;color:red;'>search_off</i></center>" # unknown radio type
                            if ( my_record["radio_id"] != "" ):
                                if ( my_record["radio_id"] == SER_LNK ): # "BMLink"
                                    my_record["radio_id"] = "BMLink"
                                    radio = "<center><i class='material-icons' style='font-size:24px;color:green;'>sync_alt</i></center>"
                                elif ( resp["radio_code"] == "43" ):
                                    radio = "FT-70D"
                                elif ( resp["radio_code"] == "48" ):
                                    radio = "FT- 3D"
                                elif ( resp["radio_code"] == "39" ):
                                    radio = "FT-991"
                                elif ( resp["radio_code"] == "37" ):
                                    radio = "FT-400"
                                elif ( resp["radio_code"] == "49" ):
                                    radio = "FT-300"
                                elif ( resp["radio_code"] == "36" ):
                                    radio = "FT-1XD"
                                elif ( resp["radio_code"] == "46" ):
                                    radio = "FT7250"
                                elif ( resp["radio_code"] == "40" ):
                                    radio = "FT- 2D"
                                elif ( resp["radio_code"] == "41" ):
                                    radio = "FT-100"
                                elif ( resp["radio_code"] == "51" ):
                                    radio = "FT- 5D"
                            my_record["radio_code"] = radio
                            continue

                    if ( item == "stream_id04" ):
                        if ( resp["stream_id04"] == my_record["stream_id"] ):
                            my_record["latitude"]  = resp["latitude"][:9].ljust(9, "0") # fixed lenght
                            my_record["longitude"] = resp["longitude"][:9].ljust(9, "0")
                            continue

                    if ( item == "stream_id05" ):
                        if ( resp["stream_id05"] == my_record["stream_id"] ):
                            my_record["dst"] = resp["dst"]
                            my_record["src"] = resp["src"]
                            my_record["uplink"] = resp["uplink"]
                            my_record["downlink"] = resp["downlink"]
                            continue
                      
                    if ( item == "stream_end" ):
                        lock.acquire()
                        temp = st_id.get()
                        lock.release()
                        my_st_id = temp[0]          
                        if ( my_st_id == resp["stream_end"] ):
                            if ( resp["type"] == "TC" ):
                                my_record["status"] = "TC" # call terminated correctly
                            else:
                                my_record["status"] = "WD" # no data anymore, watchdog in 2 secs by pYSF
                            t_end = resp["time"]
                            temp = str.split(resp["time"])
                            my_time = temp[1]
                            my_record["time"] = my_time[:8] # stop TX time
                            t_end = my_record["time"]
                            d = calc_qso_time(t_end, t_start)
                            my_record["time"] = my_record["time"] + "(" + str(d[2:])+ ")"
                            output()
                            continue
                        
                    # b'{"stream_timeout": "4279784", "CS": "IU5JAE", "time": "2021-08-30 22:43:52.322"}'
                    if ( item == "stream_timeout" ): # managed as "stream_end"
                        lock.acquire()
                        temp = st_id.get()
                        lock.release()
                        my_st_id = temp[0]          
                        my_record["status"] = "TO" # timeout
                        t_end = resp["time"]
                        temp = str.split(resp["time"])
                        my_time = temp[1]
                        my_record["time"] = my_time[:8] # stop TX time
                        t_end = my_record["time"]
                        d = calc_qso_time(t_end, t_start)
                        my_record["time"] = my_record["time"] + "(" + str(d[2:])+ ")"
                        output()
                        continue

                    # b'{"blocked": "-1", "CS": "IK5XMK    ", "GW": "BM_2222   ", "BR": "CS", "time": "2021-09-02 08:11:01.032"}'
                    # BR = block reason
                    if ( item == "blocked" ):
                        print(add_time() + " ==> blocked callsign:" + resp["CS"] + " reason: " + resp["BR"])
                        # something to do...
                        continue

                    # linked gateways
                    # b'{"linked": "1", "call": "PYBRIDGE", "IP": "192.168.88.129", "port": "45109", "TC": "4", "CF": "2021-08-29 15:46:54", "LO": "0", "LK": "0"}'
                    # b'{"total_linked": "1"}'
                    if ( item == "linked" ):
                        if ( cl_lst == True ): # we can start with an empty list
                            lock.acquire()
                            my_list2.clear()
                            lock.release()
                            print("gw list erased")
                            cl_lst = False  
                        my_record2["linked"] = resp["linked"]
                        my_record2["call"] = resp["call"]
                        my_record2["IP"] = obscure_IP(resp["IP"]) # privacy
                        my_record2["port"] = resp["port"]
                        my_record2["TC"] = resp["TC"]
                        my_record2["CF"] = resp["CF"]
                        my_record2["LO"] = resp["LO"]
                        if ( detail == True ):
                            if ( resp["LO"] == "0" ):
                                my_record2["LO"] = "No"
                            else:
                                my_record2["LO"] = "Yes"
                        my_record2["LK"] = resp["LK"]
                        if ( detail == True ):
                            if ( resp["LK"] == "0" ):
                                my_record2["LK"] = "No"
                            else:
                                my_record2["LK"] = "Yes"
                        output2()
                        continue

                    if ( item == "total_linked" ):
                        cl_lst = True # linked gw list can be cleared next time
                        # but...
                        if ( resp["total_linked"] == "0" ):
                            # cleal now!
                            lock.acquire()
                            my_list2.clear()
                            lock.release()
                            print("no gws in reflector")

                    # blocked callisgns
                    # {"blk_time": "1", "call": "IU5JAE", "BR": "RCT", "TR": "2021-08-30 22:36:39"}
                    # {"total_blk_time": "1"}
                    if ( item == "blk_time" ):
                        if ( cl_lst_blk == True ): # we can start with an empty list
                            lock.acquire()
                            my_list3.clear()
                            lock.release()
                            print("blocked list erased before new data")
                            cl_lst_blk = False
                            my_record3["blk_time"] = resp["blk_time"]
                            my_record3["call"] = resp["call"]
                            my_record3["BR"] = resp["BR"]
                            if ( detail == True ):
                                if ( resp["BR"] == "RCT" ):
                                    my_record3["BR"] = "TX Timeout"
                                else:
                                    my_record3["BR"] = "Wild PTT"
                            my_record3["TR"] = resp["TR"]
                            output3()
                            continue

                    if ( item == "total_blk_time" ):
                        cl_lst_blk = True # blocked callsigns list can be cleared next time
                        # but...
                        if ( resp["total_blk_time"] == "0" ):
                            # clear now!
                            lock.acquire()
                            my_list3.clear()
                            lock.release()
                            print("no blocked - by time - callsigns in reflector")
                            
        except Exception as e:
            print(str(e))

# init and start socket/conn pYSF server
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.sendto(str.encode(conn_msg), srv_addr_port)

# init queue
st_id = queue.Queue()  # stream_id and call queue

# init threads
threading.Thread(target=pingpong,args=(UDPClientSocket,)).start()      
threading.Thread(target=rcv,args=(UDPClientSocket,)).start()
threading.Thread(target=timeout,args=(UDPClientSocket,)).start()

# init internal webserver
routes = [
    Route('/', homepage),
    Route('/linked', linked),
    Route('/blocked', blocked),
    Route('/history', history)
]
app = Starlette(debug=True, routes=routes)
uvicorn.run(app, host=ws_linterface, port=dashb_addr_port[1], log_level='warning') # set log_level='info' to see http requests

while True:
    time.sleep(2)
