#-*-coding:utf-8-*-
import RPi.GPIO as GPIO
import sys
import time
import datetime
import Adafruit_DHT
import pymysql
import threading
import spidev
import board
import busio
import adafruit_veml7700
from twython import Twython
from urllib.request import urlopen

from auth import(consumer_key,consumer_secret,access_token,access_token_secret)
twitter = Twython(consumer_key,consumer_secret,access_token,access_token_secret)


sensor=Adafruit_DHT.DHT22
conn=pymysql.connect(host="localhost",user="raspi_use",passwd="1234",db="raspi")

A1A = 6
A1B = 12
A2A = 13
A2B = 16

now=datetime.datetime.now()
moring = now.replace(hour=7, minute=0, second=0, microsecond=0)
night = now.replace(hour=22, minute=0, second=0, microsecond=0)

N_TEMP_THRESHOLD = 17
M_TEMP_THRESHOLD = 27
HUM_THRESHOLD = 20
COUNT = 0


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(A1A, GPIO.OUT)
GPIO.output(A1A, GPIO.LOW)
GPIO.setup(A1B, GPIO.OUT)
GPIO.output(A1B, GPIO.LOW)

GPIO.setup(A2A, GPIO.OUT)
GPIO.setup(A2B, GPIO.OUT)
GPIO.output(A2A, GPIO.LOW)
GPIO.output(A2B, GPIO.LOW)

spi=spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=500000

pin=27

i2c = busio.I2C(board.SCL, board.SDA)
veml7700 = adafruit_veml7700.VEML7700(i2c)


key='91K1QI6DO0RRDCVH'
tsURL=('https://api.thingspeak.com/update?api_key=%s' %(key))


def read_spi_adc(adcChannel) :
 adcValue=0
 buff=spi.xfer2([1,(8+adcChannel)<<4,0])
 adcValue=((buff[1]&3)<<8)+buff[2]
 return adcValue

def map(x, input_min,input_max,output_min,output_max):
 return (x-input_min)*(output_max-output_min)/(input_max-input_min)+output_min

try:
 with conn.cursor() as cur :
  sql="insert into collect_data values(%s, %s, %s, %s, %s)"
  while True :
   adcValue=read_spi_adc(0)
   soil=map(adcValue,0,1023,0,100)
   light=map(veml7700.light,0,42560,0,100)
   humidity, temp = Adafruit_DHT.read_retry(sensor, pin)
   humidity = round(humidity,2)
   temp = round(temp,2)

   if now >= moring and now < night and int(temp) > M_TEMP_THRESHOLD :
    GPIO.output(A2A, GPIO.HIGH)
    GPIO.output(A2B, GPIO.LOW)
   elif now >= night and int(temp) > N_TEMP_THRESHOLD :
    GPIO.output(A2A, GPIO.HIGH)
    GPIO.output(A2B, GPIO.LOW)
   elif now < moring and int(temp) > N_TEMP_THRESHOLD :
    GPIO.output(A2A, GPIO.HIGH)
    GPIO.output(A2B, GPIO.LOW)
   else :
    GPIO.output(A2A, GPIO.LOW)
    GPIO.output(A2B, GPIO.LOW)

   if int(soil) < HUM_THRESHOLD : # 임계치보다 수분값이 작으면
    GPIO.output(A1A,GPIO.HIGH)  #워터펌프 가동
    GPIO.output(A1B,GPIO.LOW)
    time.sleep(1)
    GPIO.output(A1A,GPIO.LOW)
    GPIO.output(A1B,GPIO.LOW)
   else :
    GPIO.output(A1A,GPIO.LOW)
    GPIO.output(A1B,GPIO.LOW)

   message=('%s 온도=%0.1f*C // 습도=%0.1f%% // 토양수분= %d%% // 빛 = %d%% ' %(time.strftime("%Y-%m-%d  %H:%M:%S",time.localtime()), temp, humidity, soil, light))
   print(message) #메시지 출력

   if COUNT%15==0 :
    twitter.update_status(status=message)
    html=urlopen(tsURL+'&field1=%0.1f&field2=%0.1f&field3=%d&field4=%d'%(temp, humidity, soil, light))

   if humidity is not None and temp is not None and COUNT==150 :
    cur.execute(sql,("1120호",time.strftime("%Y-%m-%d  %H:%M:%S",time.localtime()),humidity,temp,soil)) #읽은센서 값  DB에 저장
    conn.commit()
    print('ok')
    COUNT=0
   else:
    print(COUNT)
   COUNT += 1
   time.sleep(1)
except KeyboardInterrupt :
 exit()
finally :
 conn.close()
 spi.close()
 GPIO.output(A2A, GPIO.LOW)
 GPIO.output(A2B, GPIO.LOW)
 GPIO.output(A1A,GPIO.LOW)
 GPIO.output(A1B,GPIO.LOW)
 



