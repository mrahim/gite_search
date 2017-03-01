from os.path import join
from lxml import html
import requests
import googlemaps
from datetime import datetime
import pandas as pd
import sys


def request_distances(dest_coords):
    # dest_coords is a list of coords
    # connect to gmaps
    file_key = open('key.txt', 'r')
    key = file_key.read().splitlines()[0]

    gmaps = googlemaps.Client(key=key)

    # When: 5/2/2017 at 9am
    orig_time = datetime.fromtimestamp(1493708400)
    # Where: Massy-Palaiseau
    orig_coords = '48.724819, 2.260779'

    # keys are 'destination_addresses', 'rows', 'origin_addresses', 'status'
    result = gmaps.distance_matrix(origins=orig_coords,
                                   destinations=dest_coords,
                                   mode='driving',
                                   units='metric',
                                   departure_time=orig_time,
                                   )

    # extract relevant informations
    # start with full directions
    keys = ['full_direction']
    results = [result['destination_addresses']]
    for k in ['distance', 'duration', 'duration_in_traffic']:
        for t in ['text', 'value']:
            results.append([r[k][t] for r in result['rows'][0]['elements']])
            keys.append('%s_%s' % (k, t))
    return results, keys


def get_n_beds(beds):
    for s in beds.split():
        if s.isdigit():
            return int(s)
    return -1


def scrape_details(url_detail):
    # scrape gite
    page = requests.get(url_detail)
    tree = html.fromstring(page.content)

    # gps coordinates
    data = tree.xpath('//div[@id="ma_carte"]/iframe')
    gps_coords = data[0].attrib['src'].split('&')[1][2:]

    # description
    data = tree.xpath('//div[@id="bloc_description"]')
    description = data[0].text

    # contact info (phone, mobile, web)
    data = tree.xpath('//div[@id="bloc_resa"]/table/tr/*')
    texts = [d.text for d in data]
    phone, mobile, external_url = texts[1], texts[3], texts[-1]

    # price
    data = tree.xpath('//div[@id="tarifs_cont"]/table/tr/*')
    prices = [str(d.text).strip('\xa0') for d in data]
    price = ' '.join(prices)
    return {
        'gps': gps_coords,
        'description': description,
        'price': price,
        'phone': phone, 'mobile': mobile, 'external_url': external_url
    }


def scrape_entry(entry):
    # Gite name
    name = entry.xpath('./a')[0].text
    # Gite url
    url = entry.xpath('./a')[0].attrib['href']
    full_url = join(url_prefix, url)
    # Gite beds
    beds = entry.xpath('./span[@class="or"]')[0].text
    n_beds = get_n_beds(beds)
    details = scrape_details(full_url)
    return {**{
        'internal_url': full_url,
        'name': name,
        'n_beds': n_beds,
    }, **details}


# start script
url_prefix = 'http://www.grandsgites.com'

regions = ['bourgogne', 'champagne-ardenne', 'pays-de-loire', 'centre',
           'picardie', 'haute-normandie', 'basse-normandie']
region = 'bourgogne' if sys.argv[-1] not in regions else sys.argv[-1]
print('-> %s' % region)
input_url = 'grand-gite-%s.htm' % region

# scrape list and details
page = requests.get(join(url_prefix, input_url))
tree = html.fromstring(page.content)
listing = tree.xpath('//div[@class="t_donnees2"]')
print('-> scraping entries')
results_all = [scrape_entry(ls) for ls in listing]
n_results = len(results_all)

# request distances such that only one request of 25 destinations is sent
print('-> requesting distances')
final_results = []
step = 25
for j in range(0, n_results, step):
    print('%u/%u' % (j, n_results))
    results = results_all[j:j+step]
    dest_coords = [r['gps'] for r in results]
    distances, keys = request_distances(dest_coords)
    # append distances
    for d, k in zip(distances, keys):
        for i, r in enumerate(results):
            r[k] = d[i]
    final_results.extend(results)

print('-> saving results')
# save in csv format
df = pd.DataFrame(final_results)
cols = ['name', 'n_beds', 'distance_text', 'distance_value',
        'duration_in_traffic_text', 'duration_in_traffic_value',
        'duration_text', 'duration_value', 'full_direction', 'gps',
        'internal_url', 'external_url', 'mobile', 'phone', 'price',
        'description']
df[cols].to_csv('/tmp/gites_%s.csv' % region, index=False)
