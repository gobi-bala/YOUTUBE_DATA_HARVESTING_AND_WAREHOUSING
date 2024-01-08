from googleapiclient.discovery import build
import pymongo
import pandas as pd
import psycopg2
import streamlit as st

#api key connection

def Api_connect():
    Api_id='AIzaSyA_JdxZ80vqUKPtTMPhPynvkf9aiSt5Ttw'
    
    api_service_name="youtube"
    api_version="v3"
    
    youtube = build(api_service_name,api_version,developerKey=Api_id)

    return youtube

youtube=Api_connect()

# FUNCTION TO GET CHANNEL DETAILS
def get_channel_info(channel_id):
    request = youtube.channels().list(part = 'snippet,contentDetails,statistics',
                                      id=channel_id)
    response=request.execute()

    for i in response['items']:
        data=dict(channel_name = i['snippet']['title'],
               channel_Id=i['id'],
               subscribers = i['statistics']['subscriberCount'],
               views= i['statistics']['viewCount'],
               Total_videos= i['statistics']['videoCount'],
               channel_Description=i['snippet']['description'],
               playlist_id = i['contentDetails']['relatedPlaylists']['uploads'])
    return data

#get video ids
def get_videos_ids(channel_id):
    video_ids=[]
    response = youtube.channels().list(id=channel_id,
                                        part='contentDetails').execute()
    playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids

#get video information
def get_video_info(video_Ids):
    video_data=[]
    for video_id in video_Ids:
        request=youtube.videos().list(part='snippet,ContentDetails,statistics',
                                     id=video_id
                                     )
        response=request.execute()

        for item in response['items']:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    Published_Date=item['snippet']['publishedAt'],
                    Duration=item['contentDetails']['duration'],
                    views=item['statistics'].get('viewCount'),
                    likes=item['statistics'].get('likeCount'),
                    comments=item['statistics'].get('commentCount'),
                    Favorite=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_status=item['contentDetails']['caption']
                    )
            video_data.append(data)
    return video_data

#get comment information
def get_comment_info(video_ids):
    comment_data=[]
    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(comment_Id=item['snippet']['topLevelComment']['id'],
                        video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                comment_data.append(data)
    except:
        pass
    return comment_data

#get playlist details
def get_playlist_details(Channel_id):
    next_page_token=None
    All_data=[]
    while True:
        request=youtube.playlists().list(
            part='snippet,contentDetails',
            channelId=Channel_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response=request.execute()

        for item in response['items']:
            data=dict(playlist_Id=item['id'],
                    Title=item['snippet']['title'],
                    Channel_Id=item['snippet']['channelId'],
                    Channel_Name=item['snippet']['channelTitle'],
                    Published=item['snippet']['publishedAt'],
                    video_count=item['contentDetails']['itemCount'])
            All_data.append(data)
        next_page_token=response.get('nextPageToken')
        if next_page_token is None:
            break
    return All_data

#upload to mongodb

client=pymongo.MongoClient("mongodb+srv://Gobi:gobi@cluster0.qm3sozy.mongodb.net/?retryWrites=true&w=majority")
db=client["Youtube_data"]

def channel_details(channel_id):
    ch_details=get_channel_info(channel_id)
    pl_details=get_playlist_details(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)
    cm_details=get_comment_info(vi_ids)

    coll1=db["channel_details"]
    coll1.insert_one({"channel_information": ch_details,"playlist_information":pl_details,
                      "video_information":vi_details,"comment_information":cm_details})
    
    return "upload completed sucessfully"

#table creation for channels,playlists,videos,comments
def channels_table():
    mydb = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="gobi",
    database="youtube_data",
    port="5432"
    )

    cursor = mydb.cursor()

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query='''create table if not exists channels(channel_name varchar(100),
                                                            channel_Id varchar(80) primary key,
                                                            subscribers bigint,
                                                            views bigint,
                                                            Total_videos int,
                                                            channel_Description text,
                                                            playlist_Id varchar(80))'''
        cursor.execute(create_query)
        mydb.commit()

    except:
        st.write("channel table already created")


    ch_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data['channel_information'])
    df=pd.DataFrame(ch_list)


    for index,row in df.iterrows():
        insert_query='''insert into channels(channel_name,
                                            channel_Id,
                                            subscribers,
                                            views,
                                            Total_videos,
                                            channel_Description,
                                            playlist_Id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row["channel_name"],
                row["channel_Id"],
                row["subscribers"],
                row["views"],
                row["Total_videos"],
                row["channel_Description"],
                row["playlist_Id"])
        try:
            cursor.execute(insert_query,values)
            mydb.commit()

        except:
            st.write("channels values are already inserted")

#table creation for playlists
def playlist_table():
    mydb = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="gobi",
        database="youtube_data",
        port="5432"
        )

    cursor = mydb.cursor()

    drop_query='''drop table if exists playlists'''
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query='''create table if not exists playlists(playlist_Id varchar(100) primary key,
                                                            Title varchar(100) ,
                                                            Channel_Id varchar(100),
                                                            Channel_Name varchar(100),
                                                            Published timestamp,
                                                            video_count int
                                                            )'''
    
        cursor.execute(create_query)
        mydb.commit()
    except:
        st.write("Playlists Table alredy created")
    
    pl_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=pd.DataFrame(pl_list)
    
    

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()


    for index,row in df1.iterrows():
        insert_query='''insert into playlists(playlist_Id,
                                            Title,
                                            Channel_Id,
                                            Channel_Name,
                                            Published,
                                            video_count
                                            )
                                            
                                            values(%s,%s,%s,%s,%s,%s)'''
        
        values=(row["playlist_Id"],
                row["Title"],
                row["Channel_Id"],
                row["Channel_Name"],
                row["Published"],
                row["video_count"]
                )
        try:
            cursor.execute(insert_query,values)
            mydb.commit()
        except:
            st.write("Playlists values are already inserted")

#table creation for videos
def videos_table():
    mydb = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="gobi",
        database="youtube_data",
        port="5432"
        )

    cursor = mydb.cursor()

    drop_query='''drop table if exists videos'''
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                        Channel_Id varchar(100),
                                                        video_Id varchar(30) primary key,
                                                        Title varchar(150),
                                                        Tags text,
                                                        Thumbnail varchar (200),
                                                        Description text,
                                                        Published_Date timestamp,
                                                        Duration interval,
                                                        views bigint,
                                                        likes bigint,
                                                        comments int,
                                                        Favorite int,
                                                        Definition varchar(10),
                                                        Caption_status varchar(50))'''

        cursor.execute(create_query)
        mydb.commit()
    except:
        st.write("Videos Table alrady created")


    vi_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=pd.DataFrame(vi_list)



    for index,row in df2.iterrows():
            insert_query='''insert into videos(Channel_Name,
                                                    Channel_Id,
                                                    video_Id,
                                                    Title,                                               
                                                    Tags,
                                                    Thumbnail,
                                                    Description,
                                                    Published_Date,
                                                    Duration,
                                                    views,
                                                    likes,
                                                    comments,
                                                    Favorite,
                                                    Definition,
                                                    Caption_status
                                            )
                                                    
                                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''


            values=(row['Channel_Name'],
                    row['Channel_Id'],
                    row['video_Id'],
                    row['Title'],
                    row['Tags'],
                    row['Thumbnail'],
                    row['Description'],
                    row['Published_Date'],
                    row['Duration'],
                    row['views'],
                    row['likes'],
                    row['comments'],
                    row['Favorite'],
                    row['Definition'],
                    row['Caption_status']
                    )

            try:
                cursor.execute(insert_query,values)
                mydb.commit()
            except:
                st.write("videos values already inserted in the table")

#table creation for comments
def comments_table():
    mydb = psycopg2.connect(host="localhost",
                            user="postgres",
                            password="gobi",
                            database="youtube_data",
                            port="5432"
                            )
    cursor = mydb.cursor()

    drop_query='''drop table if exists comments'''
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query='''create table if not exists comments(comment_Id varchar(100) primary key,
                                                            video_Id varchar(50),
                                                            comment_Text text,
                                                            comment_Author varchar(150),
                                                            comment_Published timestamp
                                                            )'''

        cursor.execute(create_query)
        mydb.commit()
    except:
        st.write("Commentsp Table already created")
    
    com_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=pd.DataFrame(com_list)

    for index,row in df3.iterrows():
        insert_query='''insert into comments(comment_Id ,
                                            video_Id,
                                            comment_Text,
                                            comment_Author,
                                            comment_Published
                                            )
                                            
                                            values(%s,%s,%s,%s,%s)'''
        
        values=(row['comment_Id'],
                row['video_Id'],
                row['comment_Text'],
                row['comment_Author'],
                row['comment_Published']
                )
        try:
            cursor.execute(insert_query,values)
            mydb.commit()
        except:
               st.write("This comments are already exist in comments table")

def tables():
    channels_table()
    playlist_table()
    videos_table()
    comments_table()

    return "Tables created sucessfully"

def show_channels_table():
    ch_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data['channel_information'])
    df=st.dataframe(ch_list)

    return df

def show_playlist_table():
    pl_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=st.dataframe(pl_list)

    return df1

def show_video_table():
    vi_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=st.dataframe(vi_list)
    
    return df2

def show_comment_table():
    com_list=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=st.dataframe(com_list)
    
    return df3

#streamlit part

with st.sidebar:
    st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.header("Skill Take Away")
    st.caption("Python Scripting")
    st.caption("Data Collection")
    st.caption("MongoDB")
    st.caption("API Integration")
    st.caption("Data Management using MongoDB and SQL")

channel_id=st.text_input("Enter the channel ID")

if st.button("collect and store data"):
    ch_ids=[]
    db=client["Youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data['channel_information']['channel_Id'])

    if channel_id in ch_ids:
        st.sucess("channel details of the given channel id already exists")
    
    else:
        insert=channel_details(channel_id)
        st.sucess(insert)

if st.button("Migrate to Sql"):
    Table=tables()
    st.sucess(Table)

show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","PLAYLISTS","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()

elif show_table=="PLAYLISTS":
    show_playlist_table()

elif show_table=="VIDEOS":
    show_video_table()

elif show_table=="COMMENTS":
    show_comment_table()        

#sql connection
mydb = psycopg2.connect(host="localhost",
                        user="postgres",
                        password="gobi",
                        database="youtube_data",
                        port="5432"
                        )
cursor = mydb.cursor()

question=st.selectbox("select your question",("1. All the videos and the channel name",
                                              "2. channels with most number of videos",
                                              "3. 10 most viewed videos",
                                              "4. comments in each video",
                                              "5. videos with highest likes",
                                              "6. likes for each videos",
                                              "7. views for each channel",
                                              "8. videos published  in the year 2022",
                                              "9. average duration of all videos in each channel",
                                              "10. videos have the highest number of comments"))

if question=="1. All the videos and the channel name":
    query1='''select title as videos,channel_name as channelname from videos'''
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    df=pd.DataFrame(t1,columns=["videos title","channel name"])
    st.write(df)

elif question=="2. channels with most number of videos":
    query2='''select channel_name as channelname,total_videos as no_videos from channels
                order by total_videos desc'''
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    df2=pd.DataFrame(t2,columns=["channel name","No of videos"])
    st.write(df2)

elif question=="3. 10 most viewed videos":
    query3='''select views as views,channel_name as channelname,title as videotitle from videos
                where views is not null order by views desc limit 10'''
    cursor.execute(query3)
    mydb.commit()
    t3=cursor.fetchall()
    df3=pd.DataFrame(t3,columns=["views","channel name","videotitle"])
    st.write(df3)

elif question=="4. comments in each video":
    query4='''select comments as no_comments,title as videotitle from videos where comments is not null'''
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    df4=pd.DataFrame(t4,columns=["no of comments","videotitle"])
    st.write(df4)

elif question=="5. videos with highest likes":
    query5='''select title as videotitle,channel_name as channelname,likes as likecount
                from videos where likes is not null order by likes desc'''
    cursor.execute(query5)
    mydb.commit()
    t5=cursor.fetchall()
    df5=pd.DataFrame(t5,columns=["videotitle","channelname","likecount"])
    st.write(df5)

elif question=="6. likes for each videos":
    query6='''select likes as likecount,title as videotitle from videos'''
    cursor.execute(query6)
    mydb.commit()
    t6=cursor.fetchall()
    df6=pd.DataFrame(t6,columns=["likecount","videotitle"])
    st.write(df6)

elif question=="7. views for each channel":
    query7='''select channel_name as channelname,views as totalviews from channels'''
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    df7=pd.DataFrame(t7,columns=["channel name","totalviews"])
    st.write(df7)

if question=="8. videos published  in the year 2022":
    query8='''select title as video_title,published_date as videorelease,channel_name as channelname from videos
                where extract(year from published_date)=2022'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    df8=pd.DataFrame(t8,columns=["videotitle","published_date","channel name"])
    st.write(df8)

elif question=="9. average duration of all videos in each channel":
    query9='''select channel_name as channelname,AVG(duration) as averageduration from videos group by channel_name'''
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    df9=pd.DataFrame(t9,columns=["channelname","averageduration"])
    df9

    T9=[]
    for index,row in df9.iterrows(): 
        channel_title=row["channelname"]
        average_duration=row["averageduration"]
        average_duration_str=str(average_duration)
        T9.append(dict(channeltitle=channel_title,avgduration=average_duration_str))
    df1=pd.DataFrame(T9)
    st.write(df1)

elif question=="10. videos have the highest number of comments":
    query10='''select title as videotitle, channel_name as channelname,comments as comments from videos where comments is
                not null order by comments desc'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    df10=pd.DataFrame(t10,columns=["videotitle","channelname","comments"])
    st.write(df10)
