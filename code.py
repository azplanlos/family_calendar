import os
import gc
import ssl
import time
import sys
sys.path.append('/lib/circuitpython_cest_adjuster')


import adafruit_ntp
import adafruit_requests
import alarm
import analogio
import board
import re
import displayio
from dithered_rectangle import dithered_rectangle
import neopixel
import socketpool
import terminalio
import wifi
import adafruit_datetime
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_datetime import datetime, date, timedelta
import cedargrove_dst_adjuster

import ws7in5b

class Frequency:
    (DAILY, WEEKLY, MONTHLY, YEARLY) = range(4)

    @staticmethod
    def of(val: str) -> int:
        if val == 'DAILY':
            return Frequency.DAILY
        elif val == 'WEEKLY':
            return Frequency.WEEKLY
        elif val == 'MONTHLY':
            return Frequency.MONTHLY
        else:
            return Frequency.YEARLY

class Weekday:
    (MO, TU, WE, TH, FR, SA, SU) = range(7)

    @staticmethod
    def of(val: str) -> int:
        if val == 'MO':
            return Weekday.MO
        elif val == 'TU':
            return Weekday.TU
        elif val == 'WE':
            return Weekday.WE
        elif val == 'TH':
            return Weekday.TH
        elif val == 'FR':
            return Weekday.FR
        elif val == 'SA':
            return Weekday.SA
        else:
            return Weekday.SU

class Event:
    title: str
    start_time: datetime
    end_time: datetime
    attendent: list[str]
    frequency: int
    exclude: list[datetime]
    until: datetime
    byday: int
    count: int
    interval: int
    is_important: bool = False

    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return self.title + ' (' + (str(self.start_time) if self.start_time else "-") + ' - ' + (str(self.end_time) if self.end_time else "-") + ', repeat ' + (str(self.frequency) if hasattr(self, 'frequency') and self.frequency else "-") + ')'

def show_header(ntp, header_y):
    header_group = displayio.Group()

    # print header
    headertext = prefix_date(ntp.datetime.tm_mday) + '.' + prefix_date(ntp.datetime.tm_mon) + '.' + str(ntp.datetime.tm_year)
    headerfont = bitmap_font.load_font("/TitilliumWeb-Bold-26.bdf")
    #headerfont = terminalio.FONT
    headercolor = 0x000000

    # Create the tet label
    text_area_header = label.Label(headerfont, text=headertext, color=headercolor)
    text_area_header.anchor_point = (1.0, 0.0)
    text_area_header.anchored_position = (780, header_y)
    header_group.append(text_area_header)
    print(text_area_header.bounding_box)

    line = Rect(0, header_y + text_area_header.height + 10, 800, 3, fill=0x000000)
    header_group.append(line)
    return header_group

def zeige_tag(date: date, lbl: str):
    tag_group = displayio.Group()
    tag = ""
    if date.weekday() == 0:
        tag = "Montag"
    elif date.weekday() == 1:
        tag = "Dienstag"
    elif date.weekday() == 2:
        tag = "Mittwoch"
    elif date.weekday() == 3:
        tag = "Donnerstag"
    elif date.weekday() == 4:
        tag = "Freitag"
    elif date.weekday() == 5:
        tag = "Samstag"
    elif date.weekday() == 6:
        tag = "Sonntag"
    print('weekday: ' + str(date.weekday()))
    tag_header_label = label.Label(day_header_font, text=lbl + ' (' + tag + ')', color=0x000000)
    tag_header_label.anchor_point = (1.0, 0.0)
    tag_header_label.anchored_position = (218, 0)
    tag_group.append(tag_header_label)
    return tag_group

def zeige_person_label(att: str):
    p_group = displayio.Group()
    circ = Circle(18, 18, 18, fill=0x000000)
    p_group.append(circ)
    person_label = label.Label(label_person_font, text=att, color=0xFFFFFF)
    person_label.anchor_point = (0.5, 0.5)
    person_label.anchored_position = (18, 18)
    p_group.append(person_label)
    return p_group

def zeige_stunde(titel: str, is_important: bool) -> displayio.Group:
    s_group = displayio.Group()
    fill_color = 0x000000
    text_color = 0x000000
    bar = Rect(14, 0, 8, 44, fill=0x000000)
    s_group.append(bar)
    rect = Rect(45, 0, 218 - 45, 36, outline=0x000000)
    if is_important:
        fill_color = 0xFF0000
        text_color = 0xFFFFFF
        rect = Rect(45, 0, 218 - 45, 36, outline=0x000000, fill=fill_color)
    s_group.append(rect)
    title_label = label_with_max_width(titel, 80, 218 - 45 - 10, text_color)
    s_group.append(title_label)
    return s_group

def zeige_termin(startzeit: adafruit_datetime.time | None, person: list[str], titel: str, is_important: bool):
    print("showing '" + titel + "': " + str(startzeit) + ' max width ' + str(218 - len(person) * 36 - 10) + " attendees: " + str(person))
    gc.collect()
    termin_group = displayio.Group()
    px = 18
    label_color = 0xFFFFFF
    rect = Rect(max(px + (len(person) - 1) * 36, 0), 0, max(200 - max((len(person) - 1) * 36, -18), 10), 36, fill=0xFF0000, outline=0x000000)
    if startzeit is not None and (startzeit.hour > 0 or startzeit.minute > 0):
        px = 64
        time_color = 0x000000
        if not is_important:
            label_color = 0x000000
            rect = Rect(px, 0, 218 - px, 36, outline=0x000000)
        else:
            time_color = 0xFF0000
            rect = Rect(px, 0, 218 - px, 36, fill=0xFF0000, outline=0x000000)
        timestr = prefix_date(startzeit.hour) + ":" + prefix_date(startzeit.minute)
        time_label = label.Label(default_font, text=timestr, color=time_color)
        time_label.anchor_point = (0.0, 0.5)
        time_label.anchored_position = (0, 18)
        termin_group.append(time_label)
    termin_group.append(rect)
    if "AS" in person and "AN" in person and "LU" in person:
        person = ["A"]
    for att in person:
        pg = zeige_person_label(att)
        pg.x = px - 18
        termin_group.append(pg)
        px += 36
    title_label = label_with_max_width(titel, px, 218 - len(person) * 36 - 10, label_color)
    termin_group.append(title_label)
    return termin_group

def label_with_max_width(titel: str, px: int, max_width: int, label_color: int):
    while True:
        title_label = label.Label(default_font, text=titel, color=label_color)
        if title_label.width <= max(max_width, 20):
            break
        else:
            pos = titel.rfind(" ")
            if pos is None:
                pos = len(titel) - 5
            titel = titel[:pos] + "..."
    title_label.anchor_point = (0.5, 0.5)
    title_label.anchored_position = (px + 9 + int((max_width - px)/2), 18)
    return title_label

def zeige_kalender(mon: int, year: int, current_day: int, persons: list[str], termine: list[Event], ferien: list[Event]):
    width = 40
    height = 40
    calendar_group = displayio.Group()
    dt = datetime(year, mon, 1)
    start_weekday = dt.weekday()
    first_monday = dt + timedelta(days=6-start_weekday)
    monstr = ""
    if mon == 1:
        monstr = "Januar"
    elif mon == 2:
        monstr = "Februar"
    elif mon == 3:
        monstr = "März"
    elif mon == 4:
        monstr = "April"
    elif mon == 5:
        monstr = "Mai"
    elif mon == 6:
        monstr = "Juni"
    elif mon == 7:
        monstr = "Juli"
    elif mon == 8:
        monstr = "August"
    elif mon == 9:
        monstr = "September"
    elif mon == 10:
        monstr = "Oktober"
    elif mon == 11:
        monstr = "November"
    else:
        monstr = "Dezember"
    mon_label = label.Label(day_header_font, text=monstr + " " + str(year), color=0x000000)
    mon_label.anchor_point = (1.0, 0.0)
    mon_label.anchored_position = (int(width*7), 0)
    calendar_group.append(mon_label)
    y_offest = mon_label.height + 5
    for i in range(0, start_weekday):
        rect = dithered_rectangle(i * width, y_offest, width, height, fill=0x000000, opacity=0.75)
        calendar_group.append(rect)
    last_day = 1
    for d in range(0, 31):
        cdt = dt + timedelta(days=d)
        if cdt.month == mon:
            row = int((d - first_monday.day) / 7 + 1)
            col = (d - first_monday.day) % 7
            outline_color = 0x000000
            stroke = 1
            fill_color = None
            if col >= 5:
                fill_color = 0x000000
            if d == current_day - 1:
                outline_color = 0xFF0000
                stroke = 2
                fill_color= 0xFF0000
            rect = dithered_rectangle(col * width, y_offest + row * height, width, height, outline=outline_color, stroke=stroke, fill=fill_color, opacity=0.25)
            day_label = label.Label(day_header_font, text=str(cdt.day), color=outline_color)
            day_label.anchor_point = (0.5, 0.5)
            day_label.anchored_position = (int(col * width + width / 2), int(y_offest + row * height + height / 2))
            calendar_group.append(rect)
            calendar_group.append(day_label)
            for i in range(0, len(persons)):
                p = persons[i]
                found = False
                for t in termine:
                    if t.start_time.date() == cdt.date():
                        for a in t.attendent:
                            if a == p:
                                found = True
                                break
                    if found == True:
                        break
                if found:
                    colors = [0x000000, 0xFF0000, 0x0000]
                    block = Rect(col * width + 1, y_offest + row * height + i * 3 + 3, width - 2, 3, fill=colors[i % 3])
                    calendar_group.append(block)
            for f in ferien:
                if f.start_time.date() == cdt.date():
                    block = Rect(col * width + 1, y_offest + row * height + height - 9, width - 2, 6, fill=0xFF0000)
                    calendar_group.append(block)
            last_day = d
    for i in range(1, 6 - (last_day + first_monday.day) % 7, 1):
        d = last_day + i 
        row = int((d - first_monday.day) / 7 + 1)
        col = (d - first_monday.day) % 7
        rect = dithered_rectangle(col * width, y_offest + row * height, width, height, fill=0x000000, opacity=0.75)
        calendar_group.append(rect)
    return calendar_group

def prefix_date(num: int):
    if num < 10:
        return "0" + str(num)
    else:
        return str(num)

event_start = re.compile("BEGIN:VEVENT")
event_end = re.compile("END:VEVENT")
event_attendee = re.compile("ATTENDEE;ROLE=REQ-PARTICIPANT;CN=(.+):")
event_start_time = re.compile("DTSTART(;TZID=.+?)*(;VALUE=DATE)*:([0-9]+)T*([0-9]+)*")
event_end_time = re.compile("DTEND(;TZID=.+?)*(;VALUE=DATE)*:([0-9]+)T*([0-9]+)*")
event_summary = re.compile("SUMMARY:(.+)")
event_frequency = re.compile("RRULE:FREQ=(WEEKLY|DAILY|MONTHLY|YEARLY);(UNTIL=([0-9]+)T*([0-9]+)*Z*;)*(COUNT=([0-9]+);*)*(INTERVAL=([0-9]+);*)*(BYDAY=(.+))*")
event_exdate = re.compile("EXDATE:(([0-9]+T[0-9]+,*)+)")
event_color = re.compile("COLOR:#([A-F0-9]+)")
event_date = re.compile("([0-9]+)T*([0-9]+)*Z*")

def start_time(event: Event):
    return event.start_time

def append_event(events: list[Event], event: Event, current_day: datetime):
    if (event.start_time.year == current_day.year and event.start_time.month == current_day.month) \
        or (event.start_time > current_day and event.start_time < current_day + timedelta(days=2)):
            print("saving event " + str(event))
            events.append(event)

def parse_ical(text: str, current_day: datetime) -> list[Event]:
    lines = text.splitlines()
    event = None
    events = []
    for line in lines:
        if event_start.match(line):
            print("----EVENT----")
            event = Event()
        if event_end.match(line) and event is not None and hasattr(event, "start_time") and event.start_time is not None:
            if not hasattr(event, "attendent"):
                event.attendent = ["AS", "AN", "LU"]
            append_event(events, event, current_day)
            if hasattr(event, "frequency") and event.frequency is not None:
                print("repeat event " + event.title)
                count = 1
                dt = event.start_time
                while True:
                    print(".")
                    if (hasattr(event, 'count') and event.count is not None and event.count < count) or (hasattr(event, 'until') and event.until is not None and event.until < dt) or (dt > datetime(year=current_day.year, month=current_day.month, day=1, tzinfo=timezone) + timedelta(days=31)):
                        break
                    interval = 1
                    if hasattr(event, 'interval') and event.interval is not None:
                        interval = event.interval
                    if event.frequency == Frequency.DAILY:
                        dt = event.start_time + adafruit_datetime.timedelta(days=count*interval)
                    elif event.frequency == Frequency.WEEKLY:
                        dt = event.start_time + timedelta(weeks=count*interval)
                    elif event.frequency == Frequency.MONTHLY and (event.start_time.month != current_date.month or event.start_time.year != current_date.year):
                        dt = adafruit_datetime.datetime(current_day.year, current_date.month, event.start_time.day, event.start_time.hour, event.start_time.minute, tzinfo=timezone)
                    elif event.frequency == Frequency.YEARLY and event.start_time.year != current_date.year:
                        dt = adafruit_datetime.datetime(event.start_time.year + count - 1, event.start_time.month, event.start_time.day, event.start_time.hour, event.start_time.minute, tzinfo=timezone)
                    else:
                        break
                    duplicate = Event()
                    duplicate.title = event.title
                    duplicate.start_time = dt
                    duplicate.end_time = dt + timedelta(seconds=int(event.end_time.timestamp() - event.start_time.timestamp()))
                    duplicate.attendent = event.attendent
                    duplicate.is_important = event.is_important
                    excl = False
                    if hasattr(event, 'exclude'):
                        for ex_date in event.exclude:
                            if ex_date.date() == duplicate.start_time.date():
                                excl = True
                                print("exclude " + str(ex_date))
                    if not excl:
                        append_event(events, duplicate, current_day)
                    count += 1
                pass
            if event.end_time is not None and event.end_time.date != event.start_time.date:
                #duplicate event for every active day
                add_days = 1
                print("duplicate event for duration " + event.title)
                while True:
                    day = event.start_time + timedelta(days=add_days)
                    day = datetime.combine(day.date(), time=adafruit_datetime.time(tzinfo=timezone))
                    if day >= event.end_time:
                        break
                    else:
                        duplicate = Event()
                        duplicate.title = event.title
                        duplicate.start_time = day
                        duplicate.end_time = event.end_time
                        duplicate.attendent = event.attendent
                        duplicate.is_important = event.is_important
                        append_event(events, duplicate, current_day)
                    add_days += 1
        m = event_frequency.match(line)
        if m is not None and event is not None:
            event.frequency = Frequency.of(m.group(1))
            if m.group(2) is not None:
                event.until = parse_date(m, 3, 4)
            if m.group(5) is not None:
                event.count = int(m.group(6))
            if m.group(7) is not None:
                event.interval = int(m.group(8))
            if m.group(9) is not None:
                event.byday = Weekday.of(m.group(10))
        m = event_start_time.match(line)
        if m is not None and event is not None:
            event.start_time = parse_date(m)
        m = event_end_time.match(line)
        if m is not None and event is not None:
            event.end_time = parse_date(m)
        m = event_attendee.match(line)
        if m is not None and event is not None:
            if hasattr(event, "attendent"):
                event.attendent.append(m.group(1)[:2].upper())
            else:
                event.attendent = [m.group(1)[:2].upper()]
        m = event_summary.match(line)
        if m is not None and event is not None:
            event.title = m.group(1)
        m = event_color.match(line)
        if m is not None and event is not None:
            if int(m.group(1)[:2], 16) > 128 and int(m.group(1)[2:4], 16) < 64 and int(m.group(1)[4:6], 16) < 64:
                event.is_important = True
        m = event_exdate.match(line)
        if m is not None and event is not None:
            print("found exclude dates: " + m.group(1))
            ex_dates = m.group(1).split(",")
            ex_dt_times = []
            for ex_dt in ex_dates:
                dm = event_date.match(ex_dt)
                if dm is not None:
                    dt = parse_date(dm, 1, 2)
                    ex_dt_times.append(dt)
            event.exclude = ex_dt_times
    print(str(len(events)) + " Events")
    events.sort(key=start_time)
    return events

def parse_date(m: re.Match[str], date_group_num: int = 3, time_group_num: int = 4) -> datetime:
    print("date: " + m.group(date_group_num) + " (" + str(len(m.groups())) + ")")
    time = None
    if m.group(time_group_num) is not None:
        print("time: " + m.group(time_group_num))
        time = datetime(int(m.group(date_group_num)[:4]), int(m.group(date_group_num)[4:6]), int(m.group(date_group_num)[6:]), int(m.group(time_group_num)[:2]), int(m.group(time_group_num)[2:4]), int(m.group(time_group_num)[4:6]), tzinfo=timezone)
    else:
        time = datetime(int(m.group(date_group_num)[:4]), int(m.group(date_group_num)[4:6]), int(m.group(date_group_num)[6:]), tzinfo=timezone)
    return time

label_person_font = bitmap_font.load_font("/TitilliumWeb-Black-24.bdf")
default_font = bitmap_font.load_font("/TitilliumWeb-Regular-16.bdf")
day_header_font = bitmap_font.load_font("/TitilliumWeb-Bold-Header-16.bdf")


pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, pixel_order=neopixel.RGBW)
pixels.brightness = 0.5

pixels[0] = (10, 10, 0)

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
ntp = adafruit_ntp.NTP(pool)
(ntpdt, isDst) = cedargrove_dst_adjuster.adjust_dst(ntp.datetime)
timezone = adafruit_datetime.timezone(offset=timedelta(hours=1 + (1 if isDst else 0)), name="Europe/Berlin")
current_date = datetime(ntp.datetime.tm_year, ntp.datetime.tm_mon, ntp.datetime.tm_mday, ntp.datetime.tm_hour + 1 + (1 if isDst else 0), ntp.datetime.tm_min, tzinfo=timezone)

print("fetching " + os.getenv('CALENDAR_MAIN', "-"))
calTxt = requests.get(os.getenv('CALENDAR_MAIN', "-"), stream=True).text
termine = parse_ical(calTxt, current_date.combine(current_date.date(), adafruit_datetime.time(tzinfo=timezone)))
calTxt = None
gc.collect()

stundenplanTxt = requests.get(os.getenv('CALENDAR_STUNDENPLAN', '-'), stream=True).text
stundenplan = parse_ical(stundenplanTxt, current_date.combine(current_date.date(), adafruit_datetime.time(tzinfo=timezone)))
stundenplanTxt = None
gc.collect()

ferienTxt = requests.get(os.getenv('CALENDAR_FERIEN', '-'), stream=True).text
ferien = parse_ical(ferienTxt, current_date.combine(current_date.date(), adafruit_datetime.time(tzinfo=timezone)))
feiertage = parse_ical(requests.get(os.getenv('CALENDAR_FEIERTAGE', '-'), stream=True).text, current_date.combine(current_date.date(), adafruit_datetime.time(tzinfo=timezone)))
ferienTxt = None
gc.collect()

for fer in ferien:
    fer.attendent = []
    termine.append(fer)

for feiertag in feiertage:
    feiertag.attendent = []
    ferien.append(feiertag)
    termine.append(feiertag)

ferien.sort(key=start_time)
termine.sort(key=start_time)

weather_url = "https://api.openweathermap.org/data/3.0/onecall?lat=" + os.getenv("OPENWEATHER_LAT", "-") + "&lon=" + os.getenv("OPENWEATHER_LON", "-") + "&exclude=minutely,hourly,current&units=metric&appid=" + os.getenv("OPENWEATHER_API_KEY", "-")
weather = requests.get(weather_url).json()

pixels[0] = (10, 0, 0)

batPin = analogio.AnalogIn(board.A2)

displayio.release_displays()

# This pinout works on a Feather M4 and may need to be altered for other boards.
spi = board.SPI()  # Uses SCK and MOSI
epd_cs = board.D39
epd_dc = board.D40
epd_reset = board.D41
epd_busy = board.D42

display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)
time.sleep(1)

display = ws7in5b.WS7IN5B(
    display_bus,
    width=800,
    height=480,
    seconds_per_frame=20,
    busy_pin=epd_busy,
    highlight_color=0xff0000,
    rotation=180
)

g = displayio.Group()

#display.refresh()
# (optional) wait until display is fully updated
while display.busy:
    pass
# display is now updated
print("update ok")
print(ntp.datetime)

rect = Rect(0, 0, 800, 480, fill=0xFFFFFF)
g.append(rect)

header_group = show_header(ntp, 10)

# Show it
g.append(header_group)

delta = timedelta(days=1)
tomorrow_date = current_date + delta
tag = zeige_tag(current_date, 'Heute')
tag.x = 10
tag.y = 60
g.append(tag)

tag2 = zeige_tag(tomorrow_date, 'Morgen')
tag2.x = 250
tag2.y = 60
g.append(tag2)

x = 10

for cdate in [current_date, tomorrow_date]:
    y = 90
    termine_count = 0
    for termin in termine:
        if termin.start_time.date() == cdate and (termin.start_time.time() is None or (termin.start_time.hour == 0 and termin.start_time.minute == 0)):
            termin2 = zeige_termin(termin.start_time.time(), termin.attendent, termin.title, termin.is_important)
            termin2.y = y
            termin2.x = x
            y += 45
            g.append(termin2)
            termine_count += 1
    # Stundenplan
    last_start = None
    isFerien = False
    for fer in ferien:
        if fer.start_time.date() == cdate.date():
            isFerien = True
    if not isFerien:
        for stunde in stundenplan:
            if stunde.start_time.date() == cdate:
                if last_start is not None and stunde.start_time.timestamp() - last_start.timestamp() > 60:
                    p_rect = dithered_rectangle(45, 0, 218 - 45, 8, fill=0x000000, opacity=0.25)
                    p_rect.x = x + 45
                    p_rect.y = y
                    g.append(p_rect)
                    y += 8
                stunde_eintrag = zeige_stunde(stunde.title, stunde.is_important)
                stunde_eintrag.y = y
                stunde_eintrag.x = x
                g.append(stunde_eintrag)
                if last_start is None:
                    pers_label = zeige_person_label("LU")
                    pers_label.y = y
                    pers_label.x = x
                    g.append(pers_label)
                last_start = stunde.end_time
                y += 36
                termine_count += 1
        y += 8
    else:
        print("Ferien am " + str(cdate))
    # normale Termine
    for termin in termine:
        if termin.start_time.date() == cdate and termin.start_time.time() is not None and (termin.start_time.hour != 0 or termin.start_time.minute != 0):
            termin2 = zeige_termin(termin.start_time.time(), termin.attendent, termin.title, termin.is_important)
            termin2.y = y
            termin2.x = x
            y += 45
            g.append(termin2)
            termine_count += 1
    if termine_count == 0:
        no_data = displayio.OnDiskBitmap("smile.bmp")
        no_data_sprite = displayio.TileGrid(no_data, pixel_shader=no_data.pixel_shader)
        no_data_sprite.pixel_shader.make_transparent(0)
        no_data_sprite.x = x + 100
        no_data_sprite.y = y + 70
        no_data_label = label.Label(day_header_font, text="Keine Termine!\nViel Spaß!", color=0x000000)
        no_data_label.width
        no_data_label.anchor_point = (0.5, 0.0)
        no_data_label.anchored_position = (x + 125, y + 140)
        g.append(no_data_sprite)
        g.append(no_data_label)
    x += 250

cal = zeige_kalender(current_date.month, current_date.year, current_date.day, ["AS", "LU", "AN"], termine, ferien)
cal.x = 500
cal.y = 200
g.append(cal)

# Set text, font, and color
text = 'letzte Aktualisierung: ' + prefix_date(current_date.day) + '.' + prefix_date(current_date.month) + '.' + str(current_date.year) + ' ' + prefix_date(current_date.hour) + ":" + prefix_date(current_date.minute)
font = terminalio.FONT
color = 0x000000

# Create the text label
text_area = label.Label(font, text=text, color=color)
text_area.anchor_point = (1.0, 1.0)
text_area.anchored_position = (780, 478)

g.append(text_area)
    
voltage = (batPin.value / 65535) * batPin.reference_voltage
bat_perc = min((voltage - 1.50) / (2.10 - 1.50), 1.0)

print("Battery pin: " + str(batPin.value))
print(str(voltage) + 'V => ' + str(bat_perc) + '%')

battery_sprite_sheet = displayio.OnDiskBitmap("battery.bmp")
battery_symbol = displayio.TileGrid(battery_sprite_sheet, pixel_shader=battery_sprite_sheet.pixel_shader, width=1, height=1, tile_width=20, tile_height=10)
battery_symbol.pixel_shader.make_transparent(0)
battery_symbol[0] = min(max(int(bat_perc * 5), 0), 4)

battery_symbol.x = 5
battery_symbol.y = 15
g.append(battery_symbol)

bat_label = label.Label(font, text=str(int(round(bat_perc*100, 0))) + '%', color=0x000000)
bat_label.anchor_point = (0.0, 0.0)
bat_label.anchored_position = (30, 15)

g.append(bat_label)

weather_sprite_sheet = displayio.OnDiskBitmap("wetter.bmp")
weather_symbol = displayio.TileGrid(weather_sprite_sheet, pixel_shader=weather_sprite_sheet.pixel_shader, width=3, height=1, tile_width=70, tile_height=70)
weather_sprite_sheet.pixel_shader.make_transparent(0)
symbolmap = ["01d", "02d", "03d", "04d", "09d", "10d", "11d", "13d", "50d"]

for day in range(0, 3):
    icon = weather["daily"][day]["weather"][0]["icon"]
    print("day " + str(day) + ": " + str(weather["daily"][day]))
    weather_symbol[day] = symbolmap.index(icon)
    temp_label = label.Label(day_header_font, text=str(int(weather["daily"][day]["temp"]["min"])) + " / " + str(int(weather["daily"][day]["temp"]["max"])), color=0x000000)
    temp_label.anchor_point = (0.5, 0.0)
    temp_label.anchored_position = (583 + day * 70, 130)
    g.append(temp_label)

weather_symbol.x = 545
weather_symbol.y = 70
g.append(weather_symbol)


print("is DST: " + str(isDst))
print("in DST: " + str(ntpdt))
print("current date: " + str(current_date.ctime()))
print("tzone: " + str(timezone))

secondsWaited = 0
turns = 0

while secondsWaited < 5 and turns < 5:
    display.show(g)
    display.refresh()
    time.sleep(2)
    turns += 1
    secondsWaited = 0
    while display.busy:
        time.sleep(1)
        secondsWaited += 1
    time.sleep(20)

pixels[0] = (0, 10, 0)

# display is now updated
print("img ok")
pixels.brightness = 0.0

time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 6 * 60 * 60) # type: ignore
# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.