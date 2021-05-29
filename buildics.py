import datetime
import ics


def buildEvent(name, location, begin_t: datetime.datetime, end_t: datetime.datetime, description=None):
    return ics.Event(name=name, location=location, begin=begin_t, end=end_t, description=description)


def buildIcs(data: list):
    cal = ics.Calendar()
    for i in data:
        cal.events.add(buildEvent(i['name'], i['location'], i['begin'], i['end'],
                                  i['description'] if 'description' in i.keys() else None))
    return cal


def icstofile(cal, filename):
    with open(filename + '.ics', 'w', encoding='UTF-8') as file:
        file.writelines(cal)
    print('已生成文件 %s.ics' % filename)
