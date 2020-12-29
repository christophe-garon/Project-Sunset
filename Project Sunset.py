#!/usr/bin/env python
# coding: utf-8

# In[57]:


# Required Imports
import requests
import json
import schedule
import time
import webbrowser
import pandas as pd
from pandas import DataFrame
from datetime import date, datetime, timezone, timedelta
import tzlocal
import arrow
import pgeocode
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.feature_selection import f_regression
import tweepy
import sys
from statistics import mean
import smtplib
from email.message import EmailMessage
import caffeine
caffeine.on(display=True)


# In[58]:


# Country, zip code, and email input functions for first time users
def zipcode():
    while True:
        try:
            zip_code = input('Enter your zip code: ')
            if len(zip_code) != 5:
                raise ValueError # this will send it to the print message and back to the input option
            return zip_code
        except ValueError:
            print("Hmmm... " + zip_code + " is not a valid 5 number zip code. Let's try that again.")

            
def country_code():
    while True:
        try: 
            country = input('Enter 2 letter country code: ').lower()
            if len(country) != 2:
                raise ValueError # this will send it to the print message and back to the input option 
            return country
        except ValueError:
            print("Hmmm... " + country + " is not a valid country code. Let's try that again.")

            
def get_email():  
    while True:
        try: 
            answer = input("Would you like us to email you sunset predictions for your area (Yes/No)? ").lower()
            if answer == 'yes':
                user_email = input('Please enter your email: ').lower()
                return user_email        
            elif answer == 'no':
                user_email = 'None'
                return user_email          
            else:
                raise ValueError # this will send it to the print message and back to the input option 
          
        except ValueError:
            print("Hmmm... " + answer + " is not a valid answer. Let's try that again.")


# In[59]:


def get_twitter_auth(consumer_key, consumer_secret):
    callback_uri = 'oob'
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback_uri)
    redirect_url = auth.get_authorization_url()
    webbrowser.open(redirect_url)
    user_pin = input("Enter user pin: ")
    auth.get_access_token(user_pin)
    access_token = auth.access_token
    access_token_secret = auth.access_token_secret
    return access_token, access_token_secret
    


# In[60]:


# Import existing user data or create new user if no user file exists

try:
    user = pd.read_csv("user.csv", index_col=0)
    country = user['country'][0]
    zip_code = str(user['zip code'][0])
    nomi = pgeocode.Nominatim(country)
    cord = nomi.query_postal_code([zip_code])
    lat = float(cord['latitude'])
    long = float(cord['longitude'])
    owm_key = user['owm api key'][0]
    wb_key = user['wb api key'][0]
    user_email = user['user email'][0]
    consumer_key = user['consumer key'][0]
    consumer_secret = user['consumer secret'][0]
    access_token = user['access token'][0]
    access_token_secret = user['access token secret'][0]
    send_email = user['send email'][0]
    send_password = user['send password'][0]
       
except IOError:
    
    print("Let's get you setup!")
    
    # Get location info
    country = country_code()
    zip_code = zipcode()
    nomi = pgeocode.Nominatim(country)
    cord = nomi.query_postal_code([zip_code])
    lat = float(cord['latitude'])
    long = float(cord['longitude'])
    owm_key = input("Open Weather Map API Key: ")
    wb_key = input("WeatherBit API Key: ")
    
    #See if user wants emails and get email info
    user_email = get_email()
    
    if user_email == "None":
        send_email = "None"
        send_password = "None"
    else:
        send_email = input('Please enter the email you will use to send predictions: ').lower()
        send_password = input('Please enter the email password for the previous email: ')

    #See if user wants to tweet predictions and get twitter info  
    want_tweets = input("Do you want to tweet out predictions and collect ratings via twitter?(Yes/No) ").lower()
    if want_tweets == 'yes':
        consumer_key = input("Twitter Consumer Key: ")
        consumer_secret = input("Twitter Consumer Secret: ")
        access_token, access_token_secret = get_twitter_auth(consumer_key, consumer_secret)
    else:
        consumer_key = "None"
        consumer_secret = "None"
        access_token = "None"
        access_token_secret = "None"
        
    start_date = date.today().strftime('%Y-%m-%d')
    
    # create user dataframe
    col = {
        "country":country, "zip code":zip_code, "user email":user_email, "lat":lat,"long":long, "owm api key":owm_key, "wb api key":wb_key, 
        "consumer key":consumer_key, "consumer secret":consumer_secret, "access token":access_token, "access token secret":access_token_secret,
        "send email":send_email, "send password":send_password}

    user = pd.DataFrame(col, index= [start_date])
    user.to_csv("user.csv", encoding='utf-8', index=True)


# In[61]:


# Create function to call Open Weather Map API later and call now
# Api info: https://openweathermap.org/current

def owm():
    
    r = requests.get('https://api.openweathermap.org/data/2.5/weather', 
                     params={'zip': zip_code + ',' + country, 'APPID': owm_key})
    
    data = json.loads(r.content)
    return data

data = owm()


# In[62]:


# Current Time
def current_time():
    t = datetime.now()
    current_time = t.strftime("%H:%M")
    return current_time


def convert_time(time):
    if time > '12:59':
        converted_time = str(int(time[0:2]) - 12) + time[2:]
    return converted_time

# Sunset Time
unix_timestamp = int(data['sys']['sunset'])
utc_time = datetime.fromtimestamp(unix_timestamp, timezone.utc)
local_time = utc_time.astimezone()
sunset_time = local_time.strftime("%H:%M")
converted_sunset_time = convert_time(sunset_time)


# Determine Run Time (Run Time = Sunset Time - 1 Hour) 
hour = '01:00'
format = '%H:%M'
rt = str(datetime.strptime(sunset_time, format) - datetime.strptime(hour, format))
run_time = rt[:5]

converted_run_time = convert_time(sunset_time)

print("One of our agents will send you a sunset prediction at "+ converted_run_time)


# In[107]:


# Wait until Current Time = Run Time
while current_time() != run_time:
    schedule.run_pending()
    time.sleep(60) # wait one minute 


# In[63]:


# Extract needed metrics from the Open Weather Map API as variables

#Get Updated Metrics
data = owm()

#Convert temp to °F and round
temp_k = data['main']['temp']
temp = round((temp_k - 273.15) * 9/5 + 32, 2)
pressure = data['main']['pressure'] #hPa range(980 to 1030)
humidity = data['main']['humidity']
wind_speed = data['wind']['speed']
clouds = data['clouds']['all']


# In[64]:


#WeatherBit API
r = requests.get('https://api.weatherbit.io/v2.0/current', 
                        params={'postal_code':zip_code, 'units': 'I', 
                        'key':wb_key})

#Get required Metrics from WB API
wb_data = r.json()

for d in wb_data['data']:
    elev_angle=d['elev_angle']
    visibility = d['vis']
    air_qual = d['aqi']
    uv = round(d['uv'], 2)
    dhi = d['dhi']
    ghi = d['ghi']
    dni = d['dni']


# In[65]:


#Create a DataFrame of today's metrics

# Current Date
current_date = date.today().strftime('%Y-%m-%d')

#Creating columns names and adding their data
col = {
    "Sunset Time": sunset_time,
    "Temp (°F)" : temp,
    "Pressure (hPa)" : pressure,
    "Humidity (%)": humidity,
    "Visibility (mi)": visibility,
    "Clouds (%)": clouds,
    "Wind Speed (meter/sec)": wind_speed,
    "Sun Elevation Angle (°)": elev_angle,
    "Air Quality (0-500+)": air_qual,
    "UV index (0-11+)": uv,
    "Diffuse horizontal solar irradiance": dhi,
    "Direct normal solar irradiance": dni,
    "Global horizontal solar irradiance": ghi,
    "Predicted Sunset Rating": 0,
    "Sunset Rating (1-4)": '' 
  
}

# Putting data together in DataFrame called 'update'
update = pd.DataFrame(col, index = [current_date])


# In[66]:


# Open csv file of all past sunset data or create one if first-time user

try:
    legacy = pd.read_csv("senor_sunset.csv", index_col=0)
except IOError:
    update.to_csv("senor_sunset.csv", encoding='utf-8', index=True)
    legacy = pd.read_csv("senor_sunset.csv", index_col=0)
legacy


# In[67]:


# Function that will call the Twitter API
def get_twitter():

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    
    api = tweepy.API(auth)
    return api


# In[68]:


# Function that initiates the rating process

def rating():
    
    legacy = pd.read_csv("senor_sunset.csv", index_col=0)
    
    # Add the latest row of metrics to our legacy table
    for day in [date]:
        if day in legacy['Sunset Time']:
            pass
        else:
            legacy = pd.concat([update,legacy])
            legacy.to_csv('senor_sunset.csv', encoding='utf-8', index=True)
            print('Secret File Updated')
    
    
    # Wait until midnight to collect ratings 
    while current_time() != '00:00':
        schedule.run_pending()
        time.sleep(60) # wait one minute      
      
    
    # Get ratings from twitter users
    api = get_twitter()
    mentions = api.mentions_timeline()
    
    status_id = str(status.id)
    ratings = []

    for m in mentions:
        if status_id in str(m.in_reply_to_status_id):
            try: 
                tweet =  float(m.text[9:])
                if 1 <= tweet <= 4:
                    ratings.append(tweet)
        
            except ValueError:
                pass
         
        
    #Calc the average of the twitter ratings
    try:
        mean_rating = mean(ratings)
        sunset_input = str(round(mean_rating, 1))
        sunset_rating = str(round(mean_rating))
    
    except ValueError:
        sunset_input = ""
        sunset_rating = "....wait no one voted..."

        
    #Tweet out the user ratings
    api = get_twitter()
    api.update_status("Hmmm... according to your votes, yesterday's sunset was actaully a " + sunset_rating + " on a 1 to 4 scale. I'm learning")
    
    #Adding the sunset rating to the table
    legacy.iloc[0,-1] = sunset_input
    legacy.to_csv('senor_sunset.csv', encoding='utf-8', index=True)
    
    print('Thanks for the Data!') 


# In[69]:


# Drop any rows from legacy Dataframe without sunset ratings and count total rows
legacy_cleaned = legacy.dropna(axis=0)
data_count = len(legacy_cleaned.index)

#Check to see if we have at least 8 ratings so we can make a prediction 
if data_count < 8:
    
    print("We need at least 8 entries to start making predictions. We have " + str(data_count) + ", but we're getting there!")
    
    api = get_twitter()
    status = api.update_status("The sun sets at {}. We need at least 8 entries to start making predictions. We have {}, but we're getting there!".format(converted_sunset_time,str(data_count)))
    
    rating()
    
    # Rerun the Program
    filename = sys.argv[0]
    time.sleep(5)
    exec(open(filename).read())


# In[70]:


# Creating ODL Regression model
x = legacy_cleaned[['Temp (°F)', 'Pressure (hPa)', 'Humidity (%)', 'Visibility (mi)', 'Clouds (%)',
         'Wind Speed (meter/sec)', 'Sun Elevation Angle (°)', 'Air Quality (0-500+)', 'UV index (0-11+)',
                    'Diffuse horizontal solar irradiance', 'Direct normal solar irradiance', 'Global horizontal solar irradiance']]

y = legacy_cleaned['Sunset Rating (1-4)']


# In[71]:


# Scaling data for better comparison
# This gives every metric of feature a mean of 0 and a standard deviation of 1 
scaler = StandardScaler()
scaler.fit(x)
x_scaled = scaler.transform(x)

#Fitting the regression model to our past sunset data
reg = LinearRegression()
reg.fit(x_scaled,y)


# In[ ]:


# # Explore the performance of our regression as a whole. Used internally on occasion

# def adj_r2(x,y):
#     r2 = reg.score(x,y)
#     n = x.shape[0]
#     p = x.shape[1]
#     adjusted_r2 = 1-(1-r2)*(n-1)/(n-p-1)
#     return adjusted_r2

# metrics = {
#     'Int':reg.intercept_,
#     'R2':reg.score(x_scaled,y),
#     'Adj R2':adj_r2(x_scaled,y)}

# i = 'Metrics:'

# pd.DataFrame(metrics, index=[i])


# In[ ]:


# # Explore the performance of the individual features and create summary table. Used internally on occasion

# f_regression(x_scaled,y)
# p_values = f_regression(x,y)[1]

# reg_summary = pd.DataFrame(data = x.columns.values, columns=['Features'])
# reg_summary ['Coefficients'] = reg.coef_
# reg_summary ['p-values'] = p_values.round(3)
# reg_summary


# In[ ]:


# Organizing today's metrics from the update DataFrame from earlier

new_x = update[['Temp (°F)', 'Pressure (hPa)', 'Humidity (%)', 'Visibility (mi)', 'Clouds (%)',
         'Wind Speed (meter/sec)', 'Sun Elevation Angle (°)', 'Air Quality (0-500+)', 'UV index (0-11+)',
               'Diffuse horizontal solar irradiance', 'Direct normal solar irradiance', 'Global horizontal solar irradiance']]

new_x_scaled = scaler.transform(new_x)


# In[ ]:


# Run today's metrics through the predictive model
predicted_sunset  = reg.predict(new_x_scaled)
predicted_sunset = str(round(predicted_sunset[0]))

# Add this predicted rating to the DataFrame and printout the rating
update['Predicted Sunset Rating'] = predicted_sunset
print("The sun sets at {}. It's predicted to be rated a {} on the scale (1 to 4)".format(converted_sunset_time, predicted_sunset))


# In[ ]:


#Tweet out the sunset prediction
api = get_twitter()
status = api.update_status("The sun sets at {}. It's predicted to be rated a {} on the scale (1 to 4). Reply to this tweet with your ratings!".format(converted_sunset_time, predicted_sunset))


# In[ ]:


# Initiate the rating function
rating()


# In[ ]:


#Rerun the Program
filename = sys.argv[0]
time.sleep(5)
exec(open(filename).read())


# In[77]:


# Optional: email yourself the prediction

try:
    msg = EmailMessage()
    msg['Subject'] = 'Sunset Prediction'
    msg['From'] = 'Christophe <{}>'.format(send_email)
    msg['To'] = user_email
    msg.set_content("The sun sets in one hour. It's predicted to be rated a "+ predicted_sunset+ " on a (1 to 4) scale.")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:      

        smtp.login(send_email,send_password)

        smtp.send_message(msg)

except IOError:
    pass


# In[ ]:




