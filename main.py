from bit import bit
from buildics import *
import getpass

username = ''  # 学号
userpassword = ''  # 密码

if __name__ == '__main__':
    if username == '' or userpassword == '':
        username = input('输入学号：')
        userpassword = getpass.getpass('输入密码（密码不会显示）：')
    bs = bit(username, userpassword)
    res = bs.getExams()
    ics = buildIcs(res)
    icstofile(ics, '%s-考试' % bs.username)
    res = bs.getAllClasses()
    ics = buildIcs(res)
    icstofile(ics, '%s-课程' % bs.username)
