from aip import AipFace
from picamera import PiCamera
import urllib.request
import RPi.GPIO as GPIO
import base64
import time
import smbus
import sys
from time import sleep
import vlc

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
TouchPin = 17
tilt = 27
TRIG = 19
ECHO = 20
BtnPin = 6
Buzzer = 13 #蜂鸣器接在第13管脚上
tmp = 0
GPIO.setup(tilt, GPIO.OUT) # white => TILT
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

BUS = smbus.SMBus(1)
LCD_ADDR = 0x27
BLEN = 1 #turn on/off background light

 #定义低中高频率
CL = [0, 131, 147, 165, 175, 196, 211, 248]     # Frequency of Low C notes
 
CM = [0, 262, 294, 330, 350, 393, 441, 495]     # Frequency of Middle C notes
 
CH = [0, 525, 589, 661, 700, 786, 882, 990]     # Frequency of High C notes
 
# 第一首歌谱子频率
song_1 = [  CM[3], CM[5], CM[6], CM[3], CM[2], CM[3], CM[5], CM[6], # Notes of song1
            CH[1], CM[6], CM[5], CM[1], CM[3], CM[2], CM[2], CM[3], 
            CM[5], CM[2], CM[3], CM[3], CL[6], CL[6], CL[6], CM[1],
            CM[2], CM[3], CM[2], CL[7], CL[6], CM[1], CL[5] ]
# 节奏
beat_1 = [1, 1, 3, 1, 1, 3, 1, 1,           # Beats of song 1, 1 means 1/8 beats
          1, 1, 1, 1, 1, 1, 3, 1, 
          1, 3, 1, 1, 1, 1, 1, 1, 
          1, 2, 1, 1, 1, 1, 1, 1, 
          1, 1, 3 ]
 
song_2 = [  CM[1], CM[1], CM[1], CL[5], CM[3], CM[3], CM[3], CM[1], # Notes of song2
            CM[1], CM[3], CM[5], CM[5], CM[4], CM[3], CM[2], CM[2], 
            CM[3], CM[4], CM[4], CM[3], CM[2], CM[3], CM[1], CM[1], 
            CM[3], CM[2], CL[5], CL[7], CM[2], CM[1]   ]
 
beat_2 = [  1, 1, 2, 2, 1, 1, 2, 2,        # Beats of song 2, 1 means 1/8 beats
            1, 1, 2, 2, 1, 1, 3, 1, 
            1, 2, 2, 1, 1, 2, 2, 1, 
            1, 2, 2, 1, 1, 3 ]
        
def turn_light(key):
    global BLEN
    BLEN = key
    if key ==1 :
        BUS.write_byte(LCD_ADDR ,0x08)
    else:
        BUS.write_byte(LCD_ADDR ,0x00)
 
def write_word(addr, data):
    global BLEN
    temp = data
    if BLEN == 1:
        temp |= 0x08
    else:
        temp &= 0xF7
    BUS.write_byte(addr ,temp)
 
def send_command(comm):
    # Send bit7-4 firstly
    buf = comm & 0xF0
    buf |= 0x04               # RS = 0, RW = 0, EN = 1
    write_word(LCD_ADDR ,buf)
    time.sleep(0.002)
    buf &= 0xFB               # Make EN = 0
    write_word(LCD_ADDR ,buf)
     
    # Send bit3-0 secondly
    buf = (comm & 0x0F) << 4
    buf |= 0x04               # RS = 0, RW = 0, EN = 1
    write_word(LCD_ADDR ,buf)
    time.sleep(0.002)
    buf &= 0xFB               # Make EN = 0
    write_word(LCD_ADDR ,buf)
 
def send_data(data):
    # Send bit7-4 firstly
    buf = data & 0xF0
    buf |= 0x05               # RS = 1, RW = 0, EN = 1
    write_word(LCD_ADDR ,buf)
    time.sleep(0.002)
    buf &= 0xFB               # Make EN = 0
    write_word(LCD_ADDR ,buf)
     
    # Send bit3-0 secondly
    buf = (data & 0x0F) << 4
    buf |= 0x05               # RS = 1, RW = 0, EN = 1
    write_word(LCD_ADDR ,buf)
    time.sleep(0.002)
    buf &= 0xFB               # Make EN = 0
    write_word(LCD_ADDR ,buf)
 
def init_lcd():
    try:
        send_command(0x33) # Must initialize to 8-line mode at first
        time.sleep(0.005)
        send_command(0x32) # Then initialize to 4-line mode
        time.sleep(0.005)
        send_command(0x28) # 2 Lines & 5*7 dots
        time.sleep(0.005)
        send_command(0x0C) # Enable display without cursor
        time.sleep(0.005)
        send_command(0x01) # Clear Screen
        BUS.write_byte(LCD_ADDR ,0x08)
    except:
        return False
    else:
        return True
 
def clear_lcd():
    send_command(0x01) # Clear Screen
 
def print_lcd(x, y, str):
    if x < 0:
        x = 0
    if x > 15:
        x = 15
    if y <0:
        y = 0
    if y > 1:
        y = 1
    # Move cursor
    addr = 0x80 + 0x40 * y + x
    send_command(addr)
     
    for chr in str:
        send_data(ord(chr))
        
#servo angle
def setServoAngle(servo, angle):
    assert angle >=0 and angle <= 180
    pwm = GPIO.PWM(servo, 50)
    pwm.start(8)
    dutyCycle = angle / 18. + 3.
    pwm.ChangeDutyCycle(dutyCycle)
    sleep(0.3)
    pwm.stop()

def distance():
    GPIO.output(TRIG, 0)
    time.sleep(0.000002)

    GPIO.output(TRIG, 1)
    time.sleep(0.00001)
    GPIO.output(TRIG, 0)


    while GPIO.input(ECHO) == 0:
        a = 0
    time1 = time.time()
    while GPIO.input(ECHO) == 1:
        a = 1
    time2 = time.time()

    during = time2 - time1
    return during * 340 / 2 * 100
   
def Servo(x):
    if x == 0:
        setServoAngle(tilt, 0)
        time.sleep(3)
    if x == 1:
        setServoAngle(tilt, 90)
        playvoice('voice4.mp3')
        time.sleep(3)
        curren_time = time.asctime(time.localtime(time.time()))#获取当前时间
        f = open('Log2.txt','a')
        f.write("Person: " + "Time:" + str(curren_time)+'   '+'OUT'+'\n')
        f.close()
        
def Print(x):
    global tmp
    if x != tmp:
        if x == 0:
            clear_lcd()
            print ('CLOSE')
            print_lcd(5, 1, 'CLOSE')
        if x == 1:
            clear_lcd()
            print ('OPEN')
            print_lcd(5, 1, 'OPEN')
        tmp = x

def playvoice(name):
    p = vlc.MediaPlayer(name)
    p.play()
    
#百度人脸识别API账号信息
APP_ID = '23646920'
API_KEY = 'FqwYhlRGxePAv4pmFiAcTIKV'
SECRET_KEY ='usLU9wgmk9UzL7Ki6cp6va3k7pC2RWhl'
client = AipFace(APP_ID, API_KEY, SECRET_KEY)#创建一个客户端用以访问百度云

#图像编码方式
IMAGE_TYPE='BASE64'
camera = PiCamera()#定义一个摄像头对象

#用户组
GROUP = '01'
 
#照相函数
def getimage():
        camera.resolution = (1024,768)#摄像界面为1024*768
        camera.start_preview()#开始摄像
        time.sleep(5)
        camera.capture('faceimage.jpg')#拍照并保存
        time.sleep(2)
def getvideo():
    camera.start_recording('video.h264')
    
#对图片的格式进行转换
def transimage():
    f = open('faceimage.jpg','rb')
    img = base64.b64encode(f.read())
    return img

#上传到百度api进行人脸检测
def go_api(image):
    result = client.search(str(image, 'utf-8'), IMAGE_TYPE, GROUP);#在百度云人脸库中寻找有没有匹配的人脸
    if result['error_msg'] == 'SUCCESS':#如果成功了
        name = result['result']['user_list'][0]['user_id']#获取名字
        score = result['result']['user_list'][0]['score']#获取相似度
        if score > 80:#如果相似度大于80
            if name == 'LiuYibing':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LiuYibing')
                time.sleep(5)
            if name == 'LiuFei':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LiuFei')
                time.sleep(5)
                print_lcd(2, 1, '')
            if name == 'HeFurong':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME HeFurong')
                time.sleep(5)
            if name == 'XuZhirui':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME XuZhirui')
                time.sleep(5)
            if name == 'XiaoZhan':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME XiaoZhan')
                time.sleep(5)
            if name == 'YangMi':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME YangMi')
                time.sleep(5)
            if name == 'RenHao':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME RenHao')
                time.sleep(5)
            if name == 'KunKun':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME KunKun')
                time.sleep(5)
            if name == 'LuoLuo':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LuoLuo')
                time.sleep(5)
            if name == 'ChunChun':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME ChunChun')
                time.sleep(5)
            if name == 'Rain':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME Rain')
                time.sleep(5)
            if name == 'WangKai':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME WangKai')
                time.sleep(5)
            if name == 'YangZi':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME YangZi')
                time.sleep(5)
            if name == 'LiuYifei':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LiuYifei')
                time.sleep(5)
            if name == 'XuanBin':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME XuanBin')
                time.sleep(5)
            if name == 'WangYuan':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME WangYuan')
                time.sleep(5)
            if name == 'QianXi':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME QianXi')
                time.sleep(5)
            if name == 'LiYifeng':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LiYifeng')
                time.sleep(5)
            if name == 'LiXian':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME LiXian')
                time.sleep(5)
            if name == 'ChaoYue':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME ChaoYue')
                time.sleep(5)
            if name == 'KaiKai':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME KaiKai')
                time.sleep(5)
            if name == 'QianQian':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME QianQian')
                time.sleep(5)
            if name == 'XiaoJu':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME XiaoJu')
                time.sleep(5)
            if name == 'TianTian':
                print("欢迎%s !" % name)
                print_lcd(0, 1, 'WELCOME TianTian')
                time.sleep(5)
        else:
            print("对不起，我不认识你！")
            name = 'Unknow'
            print_lcd(2, 1, 'UNKNOW')
            time.sleep(5)
            return 0
        curren_time = time.asctime(time.localtime(time.time()))#获取当前时间
 
        #将人员出入的记录保存到Log.txt中
        f = open('Log1.txt','a')
        f.write("Person" + name + "     " + "Time:" + str(curren_time)+'   '+'IN'+'\n')
        f.close()
        return 1
    if result['error_msg'] == 'pic not has face':
        print('检测不到人脸')
        time.sleep(3)
        return -1
    else:
        print(result['error_code']+' ' + result['error_code'])
        return 0

def detect(chn):
    Key(GPIO.input(BtnPin))

def Key(x):
    if x == 0:
        print ('    ***********************')
        print ('    *   Button Pressed!   *')
        print ('    ***********************')
        print ('\n    Playing song 1...')
        global Buzz 
        Buzz = GPIO.PWM(Buzzer, 440)    # 440 is initial frequency.440HZ初试频率
        Buzz.start(50)
        for i in range(1, len(song_1)):     # Play song 1
            Buzz.ChangeFrequency(song_1[i]) # Change the frequency along the song note
            time.sleep(beat_1[i] * 0.5)     # delay a note for beat * 0.5s 
        time.sleep(1)                       # Wait a second for next song.
 
        print ('\n\n    Playing song 2...')
        for i in range(1, len(song_2)):     # Play song 1
            Buzz.ChangeFrequency(song_2[i]) # Change the frequency along the song note
            time.sleep(beat_2[i] * 0.5)     # delay a note for beat * 0.5s
        Buzz = GPIO.PWM(Buzzer, 0)
 
def setup():
    GPIO.setup(TouchPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Set BtnPin's mode is input, and pull up to high level(3.3V)
    GPIO.setup(BtnPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Set BtnPin's mode is input, and pull up to high level(3.3V)
    GPIO.setwarnings(False)         # 先关掉警告，因为操作io口会有警告
    GPIO.setup(Buzzer, GPIO.OUT)    # Set pins' mode is output Buzzer = 11 #蜂鸣器接在第33管脚上
    GPIO.add_event_detect(BtnPin, GPIO.BOTH, callback=detect, bouncetime=200)
    
def destroy():
    GPIO.cleanup()                     # Release resource
    camera.stop_preview()
    Buzz = GPIO.PWM(Buzzer, 0)
    
def touch():
    Print (GPIO.input(TouchPin))
    Servo(GPIO.input(TouchPin))
    time.sleep(5)
    Servo(GPIO.input(TouchPin))
    Print (GPIO.input(TouchPin))
    time.sleep(5)
    
#主函数
if __name__ == '__main__':
    init_lcd()
    setup()
    touch()
try:
    while True:
        dis = int(distance())
        print(dis,'cm')
        if dis < 20:
           print('准备开始，请面向摄像头 ^_^')
           playvoice('voice5.mp3')        
           if True:
                getimage()#拍照
                getvideo()
                img = transimage()  #转换照片格式
                res = go_api(img)   #将转换了格式的图片上传到百度云
                if(res == 1):#是人脸库中的人
                    print_lcd(2, 0, 'DOOR OPEN')
                    setServoAngle(tilt, 90)
                    print("欢迎回家，门已打开")
                    clear_lcd()
                    playvoice('voice1.mp3')
                    time.sleep(5)
                    print_lcd(2, 0, 'DOOR CLOSE')
                    setServoAngle(tilt, 0)
                    time.sleep(3)
                    playvoice('voice3.mp3')
                elif(res == -1):
                    print("我没有看见你,我要关门了")
                    clear_lcd()
                    playvoice('voice2.mp3')
                    print_lcd(2, 1, 'UNSIGHTED')
                    time.sleep(5)
                    print_lcd(2, 0, 'DOOR CLOSE')
                    playvoice('voice3.mp3')
                    time.sleep(3)
                else:
                    print("关门")
                    clear_lcd()
                    playvoice('voice2.mp3')
                    time.sleep(5)
                    print_lcd(2, 0, 'DOOR CLOSE')
                    playvoice('voice3.mp3')
                    time.sleep(3)
                time.sleep(3)
                print('好了')
                clear_lcd()
                print_lcd(2, 0, 'OVER')
                time.sleep(2)
                camera.stop_recording()
                clear_lcd()
                camera.stop_preview()
                touch()
                time.sleep(3)
        if dis >20:
            camera.stop_preview()
            touch()
            clear_lcd()
except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
        destroy()