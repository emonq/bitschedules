import datetime
import re
import requests
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from pytz import timezone

TZ = timezone("Asia/Shanghai")


def getRandomString(length):
    return ''.join(random.choices("ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678", k=length))


def encryptPassword(password, key):
    password = password.strip()
    aes = AES.new(bytes(key, encoding='utf-8'), mode=AES.MODE_CBC,
                  iv=bytes(getRandomString(16), encoding='utf-8'))
    pad_pkcs7 = pad(bytes(getRandomString(64) + password,
                          encoding='utf-8'), AES.block_size, style='pkcs7')
    return base64.b64encode(aes.encrypt(pad_pkcs7)).decode('utf-8')


def getDatetime(date: datetime.datetime, time: datetime.datetime):
    return (date + datetime.timedelta(hours=time.hour, minutes=time.minute)).replace(tzinfo=TZ)


class bit:
    session = requests.Session()
    username = ''
    password = ''
    schoolTerm = ''
    schoolYear = ''
    startDate = ''
    schedule = {}  # { '第i节': {'begin': datetime,'end': datetime} }

    def login(self):
        result = self.session.get(
            'http://jxzxehall.bit.edu.cn/amp-auth-adapter/login?service=http%3A%2F%2Fjxzxehall.bit.edu.cn%2Flogin%3Fservice%3Dhttp%3A%2F%2Fjxzxehall.bit.edu.cn%2Fnew%2Findex.html')
        execution = re.findall(
            r'name=\"execution\" value=\"(.*?)\"', result.text)[0]
        pwdEncryptSalt = re.findall(
            r'input type=\"hidden\" id=\"pwdEncryptSalt\" value=\"(.*?)\"', result.text)[0]
        loginurl = re.sub('cas', 'authserver', result.history[0].headers['Location'])
        data = {'username': self.username, 'password': encryptPassword(
            self.password, pwdEncryptSalt), 'captcha': '', 'rememberMe': 'true', '_eventId': 'submit',
                'cllt': 'userNameLogin',
                'dllt': 'generalLogin', 'lt': '',
                'execution': execution}
        result = self.session.post(loginurl, data=data)
        if result.status_code == 401:
            raise Exception('密码错误！')
        elif result.status_code != 200:
            raise Exception('其他错误%d' % result.status_code)
        result = self.session.get(
            'http://jxzxehall.bit.edu.cn/appShow?appId=5959167891382285')
        self.session.get(re.sub(';.*\?', '?', result.history[0].headers['Location']))

    def post(self, url, data={}):
        return self.session.post(url, data)

    def get(self, url):
        return self.session.get(url)

    def getWeekClasses(self, week) -> list:
        """
        获取第week周课表\n
        :param week: 周次
        :return: [{ 'name': 课程名, 'location': 上课地点, 'begin': 开始时间, 'end': 结束时间 }]
        """
        res = self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/wdkbByController/cxzkbrq.do',
                        {'requestParamStr': '{"XNXQDM": %s-%s, "ZC": %s}' % (
                            self.schoolYear, self.schoolTerm, week)}).json()['data']
        date = {}
        for i in res:
            date[i['XQ']] = datetime.datetime.strptime(i['RQ'], '%Y-%m-%d')
        res = self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/modules/xskcb/cxxszhxqkb.do',
                        {'XNXQDM': '%s-%s' % (self.schoolYear, self.schoolTerm), 'SKZC': week}).json()['datas'][
            'cxxszhxqkb']['rows']
        classes = []
        for i in res:
            classes.append({'name': '%s-%s' % (i['KCM'], i['SKJS']), 'location': '%s%s' % (i['XXXQMC'], i['JASMC']),
                            'begin': getDatetime(date[i['SKXQ']], self.schedule[i['KSJC_DISPLAY']]['begin']),
                            'end': getDatetime(date[i['SKXQ']], self.schedule[i['JSJC_DISPLAY']]['end'])})
        return classes

    def getAllClasses(self):
        classes = []
        i = 1
        while i:
            res = self.getWeekClasses(i)
            if len(res) > 0:
                classes += res
                i += 1
            else:
                print('本学期共 %d 周' % (i - 1))
                i = 0
        return classes

    def getExams(self):
        """
        获取本学期考试安排
        \
        :return: [{ 'name': 课程名, 'location': 考试地点, 'begin': 开始时间, 'end': 结束时间 , 'description': 备注}]
        """
        res = \
            self.session.post("http://jxzxehallapp.bit.edu.cn/jwapp/sys/studentWdksapApp/WdksapController/cxxsksap.do",
                              {
                                  'requestParamStr': '{"XNXQDM":"%s-%s","*order":"-KSRQ,-KSSJMS"}' % (
                                      self.schoolYear, self.schoolTerm)}).json()['datas']['cxxsksap']['rows']
        exams = []
        for i in res:
            date = re.findall(r"\d+-\d+-\d+", i['KSSJMS'])[0]
            exams.append({'name': "%s-%s-%s" % (i['KCM'], i['ZJJSXM'], i['KCH']), 'location': i['JASMC'],
                          'begin': datetime.datetime.strptime(
                              date + ' ' + re.findall(r"\d+-\d+-\d+ (\d+:\d+)", i['KSSJMS'])[0],
                              "%Y-%m-%d %H:%M").replace(tzinfo=TZ),
                          'end': datetime.datetime.strptime(
                              date + ' ' + re.findall(r"\d+-\d+-\d+ \d+:\d+-(\d+:\d+)", i['KSSJMS'])[0],
                              "%Y-%m-%d %H:%M").replace(tzinfo=TZ), 'description': '座位号：%s' % i['ZWH']}

                         )
        return exams

    def getMe(self):
        """
        获取个人信息
        \
        :return: { 'name': , 'department': , 'id': }
        """
        result = self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/modules/xskcb/cxxsjbxx.do',
                           {'XH': self.username}).json()['datas']['cxxsjbxx']['rows'][0]
        return {'name': result['XM'], 'department': result['YXMC'], 'id': result['XH']}

    def __init__(self, username, password):
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.74'}
        self.username = username
        self.password = password
        try:
            self.login()
        except Exception as e:
            print("登录失败\n" + str(e))
            return
        print('欢迎 %s'%self.getMe()['name'])
        res = \
            self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/modules/jshkcb/dqxnxq.do').json()['datas'][
                'dqxnxq'][
                'rows'][0]
        self.schoolYear = res['XNDM']
        self.schoolTerm = res['XQDM']
        print('当前 %s' % res['MC'])
        res = \
            self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/modules/xskcb/cxxljc.do').json()['datas'][
                'cxxljc'][
                'rows']
        for i in res:
            if i['XN'] == self.schoolYear and i['XQ'] == self.schoolTerm:
                startDate = re.findall(r'\d+-\d+-\d+', i['XQKSRQ'])[0]
                self.startDate = datetime.datetime.strptime(startDate, '%Y-%m-%d')
                break
        print('学期开始于', self.startDate.strftime('%Y-%m-%d'))
        res = self.post('http://jxzxehallapp.bit.edu.cn/jwapp/sys/wdkbby/modules/jshkcb/jc.do').json()['datas']['jc'][
            'rows']
        for i in res:
            self.schedule[i['MC']] = {'begin': datetime.datetime.strptime(i['KSSJ'], '%H:%M'),
                                      'end': datetime.datetime.strptime(i['JSSJ'], '%H:%M')}
