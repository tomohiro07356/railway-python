import os
import io
import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import boto3
import numpy as np
import urllib.request, urllib.error
from pathlib import Path
import json
import pandas as pd

#ベーシック認証
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
security = HTTPBasic()

app = FastAPI(
    title='ニレコ車両管理サイト',
    description='ニレコ八王子本社の駐車場入庫管理システムです。',
    version='1.0'
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

#環境変数取得(DynamoDB用)
AWS_ACCESS_KEY = os.environ["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = os.environ["AWS_SECRET_KEY"]
AWS_DEFAULT_REGION = os.environ["AWS_DEFAULT_REGION"]

#JSTとUTCの差分は+9時間
DIFF_JST_FROM_UTC = 9


#https://nireco-vehicle-manage.herokuapp.com/
def index(request: Request):
    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    day = dt_now.strftime('%Y%m%d')

    Items = DynamoDB()
    cnt = 0
    lis_ID = []
    for item in Items:
        cnt += 1
        if item['Date']==day[2:]: #先頭2文字除きYYmmdd
            lis_ID.append(item['ID'])
    ManagedNum = len(lis_ID) #台数
    message = NextUpdate()
    status = OAT()
    #status = str(cnt)

    return templates.TemplateResponse('index.html',
                                    {'request': request,
                                    'ManagedNum': ManagedNum,
                                    'message': message,
                                    'status': status})


#https://nireco-vehicle-manage.herokuapp.com/admin
#本日のデータ
def admin(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    # Basic認証で受け取った情報
    correct_username = secrets.compare_digest(credentials.username, "nireco")
    correct_password = secrets.compare_digest(credentials.password, "205")

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    day = dt_now.strftime('%Y%m%d')

    Items = DynamoDB()
    lis_ID, lis_Date, lis_Time, lis_Image, lis_estiID, lis_Person, lis_ImgPath, lis_Ori = [],[],[],[],[],[],[],[]

    for item in Items:
        lis_ID.append(item['ID'])
        lis_Date.append(item['Date'])
        lis_Time.append(item['Time'])
        lis_Image.append(item['Image'])
        lis_estiID.append(item['estiID'])
        lis_Person.append(item['estiPerson'])
        lis_ImgPath.append("https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/" + item['Image'])

        if('orientation' in item.keys()):
            if(item['orientation'] == '45' or item['orientation'] == '0'):
                lis_Ori.append("入庫")
            elif(item['orientation'] == '225' or item['orientation'] == '180'):
                lis_Ori.append("出庫")
            else:
                lis_Ori.append(item['orientation'])
        else:
            lis_Ori.append("-")


    #日付・時間順にsortした時のindexを取得
    ind_lex = np.lexsort((lis_Time,lis_Date))

    #sortしたlistを作成
    a, b, c, d, e, f, g, h = [],[],[],[],[],[],[],[]
    for i in ind_lex:
        if lis_Date[i]==day[2:]: #先頭2文字除きYYmmdd
            a.append(lis_ID[i])
            b.append(lis_Date[i])
            c.append(lis_Time[i])
            d.append(lis_Image[i])
            e.append(lis_estiID[i])
            f.append(lis_Person[i])
            g.append(lis_ImgPath[i])
            h.append(lis_Ori[i])
    
    ManagedNum = len(a) #台数
    if ManagedNum == 0:
        lis_ImgPath[0] = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/no_image.png"
        g.append(lis_ImgPath)

    lis_DB = [a,b,c,d,e,f,g,h]
    message = NextUpdate()

    #最新のログファイル
    hour = dt_now.strftime('%H')
    if int(hour) < 9:
        day = (dt_now + datetime.timedelta(days = -1)).strftime('%Y%m%d')
    log_file = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/log_" + day + ".log"

    #認証された場合のみadmin画面へ推移
    return templates.TemplateResponse('admin.html',
                                    {'request': request,
                                    'listDB': lis_DB,
                                    'ManagedNum': ManagedNum,
                                    'message': message,
                                    'dt_now': dt_now,
                                    'log_file': log_file})


#https://nireco-vehicle-manage.herokuapp.com/dateinfo
#日付毎のデータ
async def get_dateinfo(request: Request):
    data = await request.form()
    data_date = data.getlist('id_date') 
    id_date = data_date[0] #2020-12-01
    id_date_ = id_date[2:4] + id_date[5:7] + id_date[8:] #201201

    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC) 

    Items = DynamoDB()
    lis_ID, lis_Date, lis_Time, lis_Image, lis_estiID, lis_Person, lis_ImgPath, lis_Ori = [],[],[],[],[],[],[],[]

    for item in Items:
        lis_ID.append(item['ID'])
        lis_Date.append(item['Date'])
        lis_Time.append(item['Time'])
        lis_Image.append(item['Image'])
        lis_estiID.append(item['estiID'])
        lis_Person.append(item['estiPerson'])
        lis_ImgPath.append("https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/" + item['Image'])
        
        if('orientation' in item.keys()):
            if(item['orientation'] == '45' or item['orientation'] == '0'):
                lis_Ori.append("入庫")
            elif(item['orientation'] == '225' or item['orientation'] == '180'):
                lis_Ori.append("出庫")
            else:
                lis_Ori.append(item['orientation'])
        else:
            lis_Ori.append("-")

    #日付・時間順にsortした時のindexを取得
    ind_lex = np.lexsort((lis_Time,lis_Date))

    #sortしたlistを作成
    a, b, c, d, e, f, g, h = [],[],[],[],[],[],[],[]
    for i in ind_lex:
        if lis_Date[i]==id_date_:
            a.append(lis_ID[i])
            b.append(lis_Date[i])
            c.append(lis_Time[i])
            d.append(lis_Image[i])
            e.append(lis_estiID[i])
            f.append(lis_Person[i])
            g.append(lis_ImgPath[i])
            h.append(lis_Ori[i])

    ManagedNum = len(a) #台数
    if ManagedNum == 0:
        lis_Time[0] = ""
        lis_Person[0] = ""
        lis_ImgPath[0] = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/no_image.png"
        c.append(lis_ImgPath)
        f.append(lis_Person)
        g.append(lis_ImgPath)

    lis_DB = [a,b,c,d,e,f,g,h]
    message = NextUpdate()

    return templates.TemplateResponse('dateinfo.html',
                                    {'request': request,
                                    'listDB': lis_DB,
                                    'ManagedNum': ManagedNum,
                                    'message': message,
                                    'display_date': id_date,
                                    'dt_now': dt_now})


#https://nireco-vehicle-manage.herokuapp.com/dateinfo_error
#日付毎のエラーデータ
async def get_dateinfo_error(request: Request):
    data = await request.form()
    data_date = data.getlist('id_date') 
    id_date = data_date[0] #2020-12-01
    id_date_ = id_date[2:4] + id_date[5:7] + id_date[8:] #201201

    data_changeID = data.getlist('change_id')
    data_changePerson = data.getlist('change_person')
    data_changeImg = data.getlist('change_img')
    data_changeFlg = data.getlist('change_flg')
    data_inout = data.getlist('in_out')

    cngID = ""
    cngPerson = ""
    cngImgIndex = -1
    cngFlg = -1
    cngInOut = ""
    if len(data_changeID) != 0:
        cngID = data_changeID[0]
    if len(data_changePerson) != 0:
        cngPerson = data_changePerson[0]
    if len(data_changeImg) != 0:
        if data_changeImg[0].isdecimal():
            cngImgIndex = int(data_changeImg[0])
    if len(data_inout) != 0:
        if(data_inout[0] == "in"):
            cngInOut = "45"
        if(data_inout[0] == "out"):
            cngInOut = "225"
    if len(data_changeFlg) != 0:
        cngFlg = int(data_changeFlg[0]) #0:削除、1:編集

    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)

    Items = DynamoDB_ER()
    lis_Date, lis_Time, lis_ImgPath, lis_ImgName = [],[],[],[]

    for item in Items:
        if item['Date']==id_date_:
            lis_Date.append(item['Date'])
            lis_Time.append(item['Time'])
            lis_ImgPath.append("https://nireco-vehicle-manage-error.s3-ap-northeast-1.amazonaws.com/" + item['Image'])
            lis_ImgName.append(item['Image'])

    #日付・時間順にsortした時のindexを取得
    ind_lex = np.lexsort((lis_Time,lis_Date))

    #sortしたlistを作成
    a, b, c = [],[],[]
    cnt = 0
    for i in ind_lex:
        #DBから削除
        if cngFlg == 0 and cnt == cngImgIndex:
            DeleteDynamo(lis_ImgName[i])
        #DB編集
        elif cngFlg == 1 and cnt == cngImgIndex and cngID != "NDB_9999":
            ChangeDynamo(lis_ImgName[i], lis_Date[i], lis_Time[i], cngID, cngPerson, cngInOut)
            DeleteDynamo(lis_ImgName[i])
        else:
            a.append(lis_Date[i])
            b.append(lis_Time[i])
            c.append(lis_ImgPath[i])
        cnt+=1
    
    ManagedNum = len(a) #台数
    if ManagedNum == 0:
        lis_Date.append(id_date_)
        lis_Time.append("")
        lis_ImgPath.append("https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/no_image.png")
        a.append(lis_Date[0])
        b.append(lis_Time[0])
        c.append(lis_ImgPath[0])

    lis_DB = [a,b,c]

    #ニレコ利用者リスト
    Items_nireco = DynamoDB_nireco()
    lis_nID, lis_nName, lis_nPlateA, lis_nPlateB, lis_nPlateC, lis_nPlateD, lis_Monthly, lis_nImg, lis_maker_temp,lis_model_temp = [],[],[],[],[],[],[],[],[],[]
    for item in Items_nireco:
        lis_nID.append(item['ID'])
        lis_nName.append(item['Name'])
        lis_nPlateA.append(item['PlateA'])
        lis_nPlateB.append(item['PlateB'])
        lis_nPlateC.append(item['PlateC'])
        lis_nPlateD.append(item['PlateD'])
        lis_maker_temp.append(item['Maker'])
        lis_model_temp.append(item['Model'])

        if item['Monthly'] == "0":
            lis_Monthly.append("×")
        else:
            lis_Monthly.append("〇")
        url = "https://nirecodb.s3-ap-northeast-1.amazonaws.com/" + item['ID'] + ".jpg"
        lis_nImg.append(url)

    ind_nlex = np.argsort(lis_nID)
    na, nb, nc, nd, ne, nf, ng, nh, ni, nj= [],[],[],[],[],[],[],[],[],[]
    for i in ind_nlex:
        na.append(lis_nID[i])
        nb.append(lis_nName[i])
        nc.append(lis_nPlateA[i])
        nd.append(lis_nPlateB[i])
        ne.append(lis_nPlateC[i])
        nf.append(lis_nPlateD[i])
        ng.append(lis_Monthly[i])
        nh.append(lis_nImg[i])
        ni.append(lis_maker_temp[i])
        nj.append(lis_model_temp[i])
    lis_NDB = [na, nb, nc, nd, ne, nf, ng, nh, ni, nj]

    initial_slide = 0
    if cngImgIndex != -1:
        initial_slide = cngImgIndex

    return templates.TemplateResponse('dateinfo_error.html',
                                    {'request': request,
                                    'listDB': lis_DB,
                                    'listNDB': lis_NDB,
                                    'ManagedNum': ManagedNum,
                                    'display_date': id_date,
                                    'dt_now': dt_now,
                                    'initial_slide': initial_slide})


def get_monthly_record(request: Request):

    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    day = dt_now.strftime('%Y%m%d')
    year_now = day[0:4]
    month_now = day[4:6]
    message = NextUpdate()

    #登録している元データベースから全利用者の情報を取得→ドロップダウンリストに使用
    Items_nireco = DynamoDB_nireco()
    lis_nID_temp, lis_nName_temp, lis_nPlateA_temp, lis_nPlateB_temp, lis_nPlateC_temp, lis_nPlateD_temp,lis_nImage_temp, lis_Monthly_temp,lis_maker_temp,lis_model_temp = [],[],[],[],[],[],[],[],[],[]
    for item in Items_nireco:
        lis_nID_temp.append(item['ID'])
        lis_nName_temp.append(item['Name'])
        lis_nPlateA_temp.append(item['PlateA'])
        lis_nPlateB_temp.append(item['PlateB'])
        lis_nPlateC_temp.append(item['PlateC'])
        lis_nPlateD_temp.append(item['PlateD'])

        if item['Monthly'] == "0":
            lis_Monthly_temp.append("×")
        else:
            lis_Monthly_temp.append("〇")

        lis_nImage_temp.append("https://nirecodb.s3-ap-northeast-1.amazonaws.com/"+item['ID']+".jpg")

        lis_maker_temp.append(item['Maker'])
        lis_model_temp.append(item['Model'])

    ind_nlex = np.argsort(lis_nID_temp)

    List_N_ID, List_N_Name, List_N_PlateA, List_N_PlateB, List_N_PlateC, List_N_PlateD, List_N_Monthly, List_N_Image, List_N_Maker, List_N_Model = [],[],[],[],[],[],[],[],[],[]
    selected_ID_info = []
    for i in ind_nlex:
        List_N_ID.append(lis_nID_temp[i])
        List_N_Name.append(lis_nName_temp[i])
        List_N_PlateA.append(lis_nPlateA_temp[i])
        List_N_PlateB.append(lis_nPlateB_temp[i])
        List_N_PlateC.append(lis_nPlateC_temp[i])
        List_N_PlateD.append(lis_nPlateD_temp[i])
        List_N_Monthly.append(lis_Monthly_temp[i])
        List_N_Image.append(lis_nImage_temp[i])
        List_N_Maker.append(lis_maker_temp[i])
        List_N_Model.append(lis_model_temp[i])


    #入庫履歴データベースから写真の取得
    Items = DynamoDB()
    lis_ID_temp, lis_Date_temp, lis_Time_temp, lis_Image_temp, lis_estiID_temp, lis_estiPerson_temp, lis_ImagePath_temp = [],[],[],[],[],[],[]

    for item in Items:
        #lis_ID_temp.append(item['ID'])
        lis_Date_temp.append(item['Date'])
        lis_Time_temp.append(item['Time'])
        #lis_Image_temp.append(item['Image'])
        #lis_estiID_temp.append(item['estiID'])
        lis_estiPerson_temp.append(item['estiPerson'])
        lis_ImagePath_temp.append("https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/" + item['Image'])

    #日付・時間順にsortした時のindexを取得
    ind_lex = np.lexsort((lis_Time_temp,lis_Date_temp))
    #sortしたlistを作成
    List_ID, List_Date, List_Time, List_Image, List_estiID, List_estiPerson, List_ImagePath = [],[],[],[],[],[],[]

    for i in ind_lex:
        #List_ID.append(lis_ID_temp[i])
        List_Date.append(lis_Date_temp[i])
        #List_Time.append(lis_Time_temp[i])
        #List_Image.append(lis_Image_temp[i])
        #List_estiID.append(lis_estiID_temp[i])
        List_estiPerson.append(lis_estiPerson_temp[i])
        List_ImagePath.append(lis_ImagePath_temp[i])

    history_data_num = len(List_ID)


    return templates.TemplateResponse('monthly_record.html',
                                {'request': request,
                                'List_Date': List_Date,
                                'List_estiPerson': List_estiPerson,
                                'List_ImagePath': List_ImagePath,
                                'List_N_ID': List_N_ID,
                                'List_N_Name': List_N_Name,
                                'List_N_PlateA': List_N_PlateA,
                                'List_N_PlateB': List_N_PlateB,
                                'List_N_PlateC': List_N_PlateC,
                                'List_N_PlateD': List_N_PlateD,
                                'List_N_Monthly': List_N_Monthly,
                                'List_N_Image': List_N_Image,
                                'List_N_Maker': List_N_Maker,
                                'List_N_Model': List_N_Model,
                                'message': message,
                                'dt_now': dt_now,
                                'year_now': year_now,
                                'month_now': month_now,
                                'history_data_num': history_data_num})


def history_download_employee(request: Request):
    
    #土日以外の全休日リストの作成
    # lis_holiday = []

    #nireco休日情報取得
    # url_nireco_holiday = 'https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/NirecoHoliday.json'
    # req_nireco_holiday = urllib.request.Request(url_nireco_holiday)
    # with urllib.request.urlopen(req_nireco_holiday) as res_nireco:
    #     body_nireco = res_nireco.read().decode()
    #     body_nireco_json = json.loads(body_nireco)
    
    # for key,value in body_nireco_json.items():
    #     date_dt = datetime.datetime.strptime(key,'%Y-%m-%d')
    #     date_date = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    #     lis_holiday.append(date_date)

    #国民の祝日の情報取得
    # url_national_holiday = 'https://holidays-jp.github.io/api/v1/date.json'
    # req_national_holiday = urllib.request.Request(url_national_holiday)
    # with urllib.request.urlopen(req_national_holiday) as res_national:
    #     body_national = res_national.read().decode()
    #     body_national_json = json.loads(body_national)

    # for key,value in body_national_json.items():
    #     date_dt = datetime.datetime.strptime(key,'%Y-%m-%d')
    #     date_date = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    #     lis_holiday.append(date_date)

    # print(lis_holiday)

    #登録者情報のロード
    Items_nireco = DynamoDB_nireco()
    lis_nID, lis_nName, lis_nPlateA, lis_nPlateB, lis_nPlateC, lis_nPlateD,lis_salary_code,lis_employee_code= [],[],[],[],[],[],[],[]
    for item in Items_nireco:
        if item['Name'] not in lis_nName:
            if item['SalaryCode'] != "0":
                lis_nID.append(item['ID'])
                lis_nName.append(item['Name'])
                lis_nPlateA.append(item['PlateA'])
                lis_nPlateB.append(item['PlateB'])
                lis_nPlateC.append(item['PlateC'])
                lis_nPlateD.append(item['PlateD'])
                lis_salary_code.append(item['SalaryCode'])
                lis_employee_code.append(item['EmployeeCode'])

    #登録者情報をID順にソート
    ind_nlex = np.argsort(lis_nID)
    nID, nName, nPlateA, nPlateB, nPlateC, nPlateD, n_number,n_salary_code,n_employee_code= [],[],[],[],[],[],[],[],[]
    for i in ind_nlex:
        nID.append(lis_nID[i])
        nName.append(lis_nName[i])
        nPlateA.append(lis_nPlateA[i])
        nPlateB.append(lis_nPlateB[i])
        nPlateC.append(lis_nPlateC[i])
        nPlateD.append(lis_nPlateD[i])
        n_number.append('{0}{1}{2}{3}'.format(lis_nPlateA[i],lis_nPlateB[i],lis_nPlateC[i],lis_nPlateD[i]))
        n_salary_code.append(lis_salary_code[i])
        n_employee_code.append(lis_employee_code[i])
    lis_NDB = [nID, nName, nPlateA, nPlateB, nPlateC, nPlateD,n_number,n_salary_code,n_employee_code]

    #入庫履歴情報のロード　直近3ヶ月分を抽出
    date_now_date = datetime.date.today()
    print(date_now_date.month)
    if(date_now_date.month > 2):
        twomonthago_date = datetime.date(date_now_date.year, date_now_date.month-2, 1) #2ヶ月前の月初の日付
    else:
        twomonthago_date = datetime.date(date_now_date.year-1, date_now_date.month - 2 + 12, 1) #2ヶ月前の月初の日付

    

    Items = DynamoDB()
    lis_ID,lis_Date, lis_estiID, lis_estiPerson=[],[],[],[]
    lis_year_month = []
    for item in Items:
        date_his_int = item['Date']
        date_his_date = datetime.date(int("20"+date_his_int[0:2]),int(date_his_int[2:4]),int(date_his_int[4:6]))
        
        if date_his_date >= twomonthago_date:
            lis_ID.append(item['ID'])
            lis_Date.append(item['Date'])
            lis_estiID.append(item['estiID'])
            lis_estiPerson.append(item['estiPerson'])
            year_month = item['Date'][0:4]
            #利用履歴のある年・月を抽出
            if year_month not in lis_year_month:
                lis_year_month.append(year_month)
        

    lis_year_month.sort()

    #月別利用回数を記録するためのリストを作成。
    lis_of_lis_monthly_count = []
    for i in range(len(lis_year_month)):
        lis_monthly_count = [0] * len(nName)
        lis_of_lis_monthly_count.append(lis_monthly_count)
        #lis_of_lis_monthly_count[k][j] → kは年月のindex, jは登録者DBのindex. j番目の人がk番目の年月に入庫した回数.


    #同一日付に複数回入庫した場合に重複登録しないように、各人の入庫日リストを作成、照会する
    lis_of_lis_histdate = []
    for i in range(len(nName)):
        lis_histdate = [0]
        lis_of_lis_histdate.append(lis_histdate)

    #利用履歴の一つ一つについて、登録者DBから合致するIDを検索。合致したら利用回数を加算する。
    for i in range(len(lis_estiPerson)):
        for j in range(len(nName)):
            if lis_estiPerson[i] == nName[j]:
                if lis_Date[i] not in lis_of_lis_histdate[j]:
                    #土日と祝日はカウントしない
                    # detected_date_dt = datetime.datetime.strptime('20'+str(lis_Date[i]),'%Y%m%d')
                    # detected_date_date = datetime.date(detected_date_dt.year, detected_date_dt.month, detected_date_dt.day)
                    # if detected_date_date not in lis_holiday and detected_date_date.weekday()<5:
                        lis_of_lis_histdate[j].append(lis_Date[i])
                        #利用年・月に対応するリストにだけ加算
                        for k in range(len(lis_year_month)):
                            if lis_Date[i][0:4] == lis_year_month[k]:
                                lis_of_lis_monthly_count[k][j] += 1

    dic_contents = {'ID':nID,'社員番号':n_employee_code, '利用者':nName,'給与コード':n_salary_code, 'ナンバー情報':n_number}

    for i in range(len(lis_year_month)):
        # 新しい履歴が左側、古い履歴が右側に来るようにデータを追加する
        year = lis_year_month[len(lis_year_month) - i - 1][0:2]
        month = lis_year_month[len(lis_year_month) - i - 1][2:4]
        dictionary_key = '{0}年{1}月分'.format(year,month)
        dic_contents[dictionary_key]=lis_of_lis_monthly_count[len(lis_year_month) - i - 1]

    df = pd.DataFrame(dic_contents)

    session = Session()
    s3 = session.resource('s3')
    bucket = s3.Bucket('nireco-vehicle-manage')
    df_csv = df.to_csv(index=None)
    objkey = "VehiclePassageRecord.csv"
    putobj = bucket.Object(objkey)
    putobj.put(Body=df_csv.encode('shift_jis'), ContentEncoding='shift_jis')

    csv_file_path = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/VehiclePassageRecord.csv"
    return RedirectResponse(csv_file_path)


def history_download_nonemployee(request: Request):
    
    #土日以外の全休日リストの作成
    # lis_holiday = []

    #nireco休日情報取得
    # url_nireco_holiday = 'https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/NirecoHoliday.json'
    # req_nireco_holiday = urllib.request.Request(url_nireco_holiday)
    # with urllib.request.urlopen(req_nireco_holiday) as res_nireco:
    #     body_nireco = res_nireco.read().decode()
    #     body_nireco_json = json.loads(body_nireco)
    
    # for key,value in body_nireco_json.items():
    #     date_dt = datetime.datetime.strptime(key,'%Y-%m-%d')
    #     date_date = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    #     lis_holiday.append(date_date)

    #国民の祝日の情報取得
    # url_national_holiday = 'https://holidays-jp.github.io/api/v1/date.json'
    # req_national_holiday = urllib.request.Request(url_national_holiday)
    # with urllib.request.urlopen(req_national_holiday) as res_national:
    #     body_national = res_national.read().decode()
    #     body_national_json = json.loads(body_national)

    # for key,value in body_national_json.items():
    #     date_dt = datetime.datetime.strptime(key,'%Y-%m-%d')
    #     date_date = datetime.date(date_dt.year, date_dt.month, date_dt.day)
    #     lis_holiday.append(date_date)

    #登録者情報のロード
    Items_nireco = DynamoDB_nireco()
    lis_nID, lis_nName, lis_nPlateA, lis_nPlateB, lis_nPlateC, lis_nPlateD,lis_salary_code,lis_employee_code= [],[],[],[],[],[],[],[]
    for item in Items_nireco:
        if item['Name'] not in lis_nName:
            if item['SalaryCode'] == "0":
                lis_nID.append(item['ID'])
                lis_nName.append(item['Name'])
                lis_nPlateA.append(item['PlateA'])
                lis_nPlateB.append(item['PlateB'])
                lis_nPlateC.append(item['PlateC'])
                lis_nPlateD.append(item['PlateD'])
                lis_salary_code.append(item['SalaryCode'])
                lis_employee_code.append(item['EmployeeCode'])

    #登録者情報をID順にソート
    ind_nlex = np.argsort(lis_nID)
    nID, nName, nPlateA, nPlateB, nPlateC, nPlateD, n_number,n_salary_code,n_employee_code= [],[],[],[],[],[],[],[],[]
    for i in ind_nlex:
        nID.append(lis_nID[i])
        nName.append(lis_nName[i])
        nPlateA.append(lis_nPlateA[i])
        nPlateB.append(lis_nPlateB[i])
        nPlateC.append(lis_nPlateC[i])
        nPlateD.append(lis_nPlateD[i])
        n_number.append('{0}{1}{2}{3}'.format(lis_nPlateA[i],lis_nPlateB[i],lis_nPlateC[i],lis_nPlateD[i]))
        n_salary_code.append(lis_salary_code[i])
        n_employee_code.append(lis_employee_code[i])
    lis_NDB = [nID, nName, nPlateA, nPlateB, nPlateC, nPlateD,n_number,n_salary_code,n_employee_code]

    #入庫履歴情報のロード　直近3ヶ月分を抽出
    date_now_date = datetime.date.today()
    if(date_now_date.month > 2):
        twomonthago_date = datetime.date(date_now_date.year, date_now_date.month-2, 1) #2ヶ月前の月初の日付
    else:
        twomonthago_date = datetime.date(date_now_date.year-1, date_now_date.month - 2 + 12, 1) #2ヶ月前の月初の日付

    Items = DynamoDB()
    lis_ID,lis_Date, lis_estiID, lis_estiPerson=[],[],[],[]
    lis_year_month = []
    for item in Items:
        date_his_int = item['Date']
        date_his_date = datetime.date(int("20"+date_his_int[0:2]),int(date_his_int[2:4]),int(date_his_int[4:6]))

        if date_his_date >= twomonthago_date:
            lis_ID.append(item['ID'])
            lis_Date.append(item['Date'])
            lis_estiID.append(item['estiID'])
            lis_estiPerson.append(item['estiPerson'])
            year_month = item['Date'][0:4]
            #利用履歴のある年・月を抽出
            if year_month not in lis_year_month:
                lis_year_month.append(year_month)

    lis_year_month.sort()

    #月別利用回数を記録するためのリストを作成。値は0、長さは登録者数
    lis_of_lis_monthly_count = []
    for i in range(len(lis_year_month)):
        lis_monthly_count = [0] * len(nName)
        lis_of_lis_monthly_count.append(lis_monthly_count)

    #同一日付に複数回入庫した場合に重複登録しないように、各人の入庫日リストを作成、照会する
    lis_of_lis_histdate = []
    for i in range(len(nName)):
        lis_histdate = [0]
        lis_of_lis_histdate.append(lis_histdate)

    #利用履歴の一つ一つについて、登録者DBから合致するIDを検索。合致したら利用回数を加算する。
    for i in range(len(lis_estiPerson)):
        for j in range(len(nName)):
            if lis_estiPerson[i] == nName[j]:
                if lis_Date[i] not in lis_of_lis_histdate[j]:
                    #土日と祝日はカウントしない
                    # detected_date_dt = datetime.datetime.strptime('20'+str(lis_Date[i]),'%Y%m%d')
                    # detected_date_date = datetime.date(detected_date_dt.year, detected_date_dt.month, detected_date_dt.day)
                    # if detected_date_date not in lis_holiday and detected_date_date.weekday()<5:
                        lis_of_lis_histdate[j].append(lis_Date[i])
                        #利用年・月に対応するリストにだけ加算
                        for k in range(len(lis_year_month)):
                            if lis_Date[i][0:4] == lis_year_month[k]:
                                lis_of_lis_monthly_count[k][j] += 1


    dic_contents = {'ID':nID,'社員番号':n_employee_code, '利用者':nName,'給与コード':n_salary_code, 'ナンバー情報':n_number}

    for i in range(len(lis_year_month)):
        # 新しい履歴が左側、古い履歴が右側に来るようにデータを追加する
        year = lis_year_month[len(lis_year_month) - i - 1][0:2]
        month = lis_year_month[len(lis_year_month) - i - 1][2:4]
        dictionary_key = '{0}年{1}月分'.format(year,month)
        dic_contents[dictionary_key]=lis_of_lis_monthly_count[len(lis_year_month) - i - 1]

    df = pd.DataFrame(dic_contents)

    session = Session()
    s3 = session.resource('s3')
    bucket = s3.Bucket('nireco-vehicle-manage')
    df_csv = df.to_csv(index=None) # dfはデータフレーム型のデータ
    objkey = "VehiclePassageRecord_nonemployee.csv"
    putobj = bucket.Object(objkey)
    putobj.put(Body=df_csv.encode('shift_jis'), ContentEncoding='shift_jis')

    csv_file_path = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/VehiclePassageRecord_nonemployee.csv"
    return RedirectResponse(csv_file_path)


async def add_holiday(request: Request):
    data = await request.form()
    data_date = data.getlist('add_date') 
    cng_date_tmp = data_date[0] #2021/03/01
    cng_date = cng_date_tmp.replace('/', '-') #2021-03-01
    
    #新規に書き込むデータ
    data_dict = dict()
    data_dict[cng_date] = 'nireco' #"2021-03-01": "nireco"
    
    #s3からデータを取得
    json_path = "https://nireco-vehicle-manage.s3-ap-northeast-1.amazonaws.com/NirecoHoliday.json"
    session = Session()
    S3 = session.resource('s3')
    s3obj = S3.Object("nireco-vehicle-manage", "NirecoHoliday.json")
    file_content = s3obj.get()['Body'].read().decode('utf-8')
    json_content = json.loads(file_content)

    #辞書をマージ
    data_dict.update(json_content)
    #JSON形式に変換
    Json = json.dumps(data_dict, indent=4, sort_keys=True)
    #結果の格納
    s3obj.put(Body = Json)
    return data_dict

    
#DynamoDBからデータ取得
def DynamoDB():
    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('NirecoVehicleManage')
    response = table.scan()
    Items = response['Items']

    # レスポンスに LastEvaluatedKey が含まれなくなるまでループ処理を実行する
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        Items.extend(response['Items'])
    return Items

def DynamoDB_ER():
    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('NirecoVehicleManageError')
    response = table.scan()
    Items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        Items.extend(response['Items'])
    return Items

def DynamoDB_nireco():
    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('nirecoDB')
    response = table.scan()
    Items = response['Items']
    return Items

def DeleteDynamo(ImgName):
    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('NirecoVehicleManageError')
    table.delete_item(Key={'Image': ImgName})


def ChangeDynamo(ImgName, Date, Time, nID, nPerson, InOut):
    #IDには日時を使用する
    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    day = dt_now.strftime('%y%m%d%H%M%S')

    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('NirecoVehicleManage')
    item = {
    "ID": day,
    "Date": Date,
    "Image": ImgName,
    "Time": Time,
    "estiID": nID,
    "estiPerson": nPerson,
    "orientation": InOut
    }
    table.put_item(Item=item)

    #画像をS3にコピー
    S3 = session.resource('s3')
    copy_source = {
        'Bucket': 'nireco-vehicle-manage-error',
        'Key': ImgName
        }
    bucket = S3.Bucket('nireco-vehicle-manage')
    bucket.copy(copy_source, ImgName)

def Session():
    session = boto3.session.Session(
        aws_access_key_id = AWS_ACCESS_KEY,
        aws_secret_access_key = AWS_SECRET_KEY,
        region_name = AWS_DEFAULT_REGION
    )
    return session


#次回更新時間
def NextUpdate():
    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    hour = dt_now.strftime('%H')
    today = dt_now.strftime('%m/%d')
    tomorrow = (dt_now + datetime.timedelta(days = 1)).strftime('%m/%d')
    message = ""
    if int(hour) < 9:
        message = today + " 9:00"
    elif int(hour) < 13:
        message = today + " 13:00"
    elif int(hour) < 16:
        message = today + " 16:00"
    elif int(hour) < 24:
        message = today + " 24:00"
    else:
        message = tomorrow + " 9:00"
    return message


#稼働状況
def OAT():
    session = Session()
    DynamoDB = session.resource('dynamodb')
    table = DynamoDB.Table('NVM_OAT')
    response = table.scan()
    Items = response['Items']
    
    message = ""

    dt_now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
    for item in Items:
        if str(item['id']) == "0": 
            month_ = str(item['date'])[:2] #04/19 → 04
            day_ = str(item['date'])[-2:] #04/19 → 19
            hour_ =  str(item['time'])[:2] #11:04 → 11
            minute_ =  str(item['time'])[:2] #11:04 → 04
            month = int(month_)
            day = int(day_)
            hour = int(hour_)
            minute = int(minute_)
            dt_update = datetime.datetime(dt_now.year, month, day, hour, minute)

            # ”アップデート時刻＋1時間　＞　現在時刻”なら正常
            dt_up_1 = dt_update + datetime.timedelta(hours=1)
            if dt_up_1 > dt_now:
                message = "{0} ({1} {2})".format(item['status'], item['date'], item['time'])
            else:
                message = "動作確認時刻から１時間以上が経過しています。ネットワークを確認してください。"
        else:
            message = "DynamoDBとの連携ができませんでした"
    return message