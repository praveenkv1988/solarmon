#!/usr/bin/env python
import json
from datetime import datetime
import requests, time


ENERGY_FEED_URL = "http://localhost/emoncms/feed/fetch.json?ids=22,23,24,30"

PV_OUTPUT_URL_TEMPLATE = "https://pvoutput.org/service/r2/addoutput.jsp?key=dbbabc3e4d7c80e5eca4962d3a62ddc224b685ba&sid=50492&d={}&g={}&e={}&io={}&c={}"

def update_pvoutput():
    attempt = 0
    while(attempt < 5):
        request = requests.get(ENERGY_FEED_URL)
        energy_data = json.loads(request.text)

        energy_generated = int(energy_data[0] * 1000)
        energy_exported = int(energy_data[1] * 1000)
        energy_imported = int(energy_data[2] * 1000)
        energy_consumed = int(energy_data[3] * 1000)

        date = datetime.today().strftime('%Y%m%d')

        PV_OUTPUT_URL = PV_OUTPUT_URL_TEMPLATE.format(date, energy_generated, energy_exported, energy_imported, energy_consumed)
        r = requests.get(PV_OUTPUT_URL)
        attempt += 1
        if(r.status_code != requests.codes.ok):
            time.sleep(3)
        else:
            break

if __name__ == '__main__':
    update_pvoutput()
